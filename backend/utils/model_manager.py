# File: backend/utils/model_manager.py

import requests
from pathlib import Path
from tqdm import tqdm
import hashlib
import json
import logging
from typing import Optional, Dict, Any
from functools import lru_cache
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from datetime import datetime, timedelta
import sys
import argparse

class ModelCache:
    def __init__(self, cache_dir: Path, max_size_gb: float = 4.0, ttl_hours: int = 24):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        self.ttl = timedelta(hours=ttl_hours)
        self.cache_index_file = self.cache_dir / "cache_index.json"
        self.load_cache_index()

    def load_cache_index(self):
        if self.cache_index_file.exists():
            with open(self.cache_index_file) as f:
                self.cache_index = json.load(f)
        else:
            self.cache_index = {
                "entries": {},
                "total_size": 0,
                "last_cleanup": datetime.now().isoformat()
            }
            self.save_cache_index()

    def save_cache_index(self):
        with open(self.cache_index_file, 'w') as f:
            json.dump(self.cache_index, f, indent=2)

    def get_cache_key(self, model_name: str, config: Dict[str, Any]) -> str:
        """Generate a unique cache key based on model and config"""
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(f"{model_name}:{config_str}".encode()).hexdigest()

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get item from cache if it exists and is valid"""
        if cache_key not in self.cache_index["entries"]:
            return None

        entry = self.cache_index["entries"][cache_key]
        cache_file = self.cache_dir / f"{cache_key}.pt"

        # Check if cache entry is expired
        cached_time = datetime.fromisoformat(entry["timestamp"])
        if datetime.now() - cached_time > self.ttl:
            self.invalidate(cache_key)
            return None

        if not cache_file.exists():
            self.invalidate(cache_key)
            return None

        try:
            return torch.load(cache_file)
        except Exception as e:
            logging.error(f"Error loading cache entry: {e}")
            self.invalidate(cache_key)
            return None

    def put(self, cache_key: str, data: Dict[str, Any], size_bytes: int):
        """Add item to cache, managing size limits"""
        # Cleanup if needed
        self._ensure_cache_size(size_bytes)

        # Save cache entry
        cache_file = self.cache_dir / f"{cache_key}.pt"
        torch.save(data, cache_file)

        self.cache_index["entries"][cache_key] = {
            "timestamp": datetime.now().isoformat(),
            "size": size_bytes
        }
        self.cache_index["total_size"] += size_bytes
        self.save_cache_index()

    def invalidate(self, cache_key: str):
        """Remove item from cache"""
        if cache_key in self.cache_index["entries"]:
            entry = self.cache_index["entries"][cache_key]
            cache_file = self.cache_dir / f"{cache_key}.pt"
            
            if cache_file.exists():
                cache_file.unlink()
                
            self.cache_index["total_size"] -= entry["size"]
            del self.cache_index["entries"][cache_key]
            self.save_cache_index()

    def _ensure_cache_size(self, needed_bytes: int):
        """Ensure cache has enough space by removing old entries"""
        while (self.cache_index["total_size"] + needed_bytes > self.max_size_bytes and 
               self.cache_index["entries"]):
            # Remove oldest entry
            oldest_key = min(
                self.cache_index["entries"].keys(),
                key=lambda k: datetime.fromisoformat(
                    self.cache_index["entries"][k]["timestamp"]
                )
            )
            self.invalidate(oldest_key)

class ModelManager:
    def __init__(self, models_dir: str = "backend/models", 
                 cache_dir: str = "backend/cache",
                 max_cache_size_gb: float = 4.0):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.models_dir / "models.json"
        self.cache = ModelCache(
            Path(cache_dir), 
            max_size_gb=max_cache_size_gb
        )
        self.load_config()
        
    def load_config(self):
        if self.config_file.exists():
            with open(self.config_file) as f:
                self.config = json.load(f)
                # Update any "expected_hash_here" to None
                for _, model_info in self.config["models"].items():
                    if model_info["sha256"] == "expected_hash_here":
                        model_info["sha256"] = None
                self.save_config()
        else:
            self.config = {
                "models": {
                    "tinyllama": {
                        "version": "1.0.0",
                        "url": "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
                        "sha256": None,
                        "size": 638_930_832,
                        "required": True,
                        "model_type": "gguf",
                        "description": "TinyLlama 1.1B Chat Quantized"
                    }
                },
                "cache_version": "1.0",
                "last_updated": datetime.now().isoformat()
            }
            self.save_config()

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def download_model(self, model_name: str, force: bool = False) -> bool:
        """Download a model with progress bar and validation"""
        if model_name not in self.config["models"]:
            raise ValueError(f"Unknown model: {model_name}")
            
        model_info = self.config["models"][model_name]
        model_path = self.models_dir / model_name
        
        # Convert "expected_hash_here" to None if it exists
        if model_info["sha256"] == "expected_hash_here":
            model_info["sha256"] = None
            self.save_config()
        
        # Check if model exists and is valid
        if not force and model_path.exists():
            if self.verify_model(model_name):
                logging.info(f"Model {model_name} already exists and is valid")
                return True
            logging.warning(f"Model {model_name} exists but failed verification")
                
        # Download model
        try:
            logging.info(f"Downloading {model_name}...")
            response = requests.get(model_info["url"], stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', model_info["size"]))
            
            # Use temporary file for download
            temp_path = model_path.with_suffix('.tmp')
            with open(temp_path, 'wb') as f, tqdm(
                desc=model_name,
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for data in response.iter_content(chunk_size=1024*1024):
                    size = f.write(data)
                    pbar.update(size)
            
            # Calculate hash of downloaded file
            calculated_hash = self.calculate_hash(temp_path)
            logging.info(f"Calculated hash for {model_name}: {calculated_hash}")
            
            # Update hash in config
            self.config["models"][model_name]["sha256"] = calculated_hash
            self.save_config()
            logging.info(f"Updated hash in config for {model_name}")
            
            # Move to final location
            temp_path.rename(model_path)
            logging.info(f"Successfully downloaded {model_name}")
            return True
            
        except Exception as e:
            logging.error(f"Error downloading {model_name}: {str(e)}")
            if temp_path.exists():
                temp_path.unlink()
            return False

    @lru_cache(maxsize=1)  # Cache the last used tokenizer
    def load_tokenizer(self, model_name: str):
        """Load tokenizer with caching"""
        model_path = self.models_dir / model_name
        return AutoTokenizer.from_pretrained(str(model_path))

    def load_model(self, model_name: str, model_config: Optional[Dict[str, Any]] = None) -> Any:
        """Load model with caching support"""
        if model_config is None:
            model_config = {}

        # Generate cache key based on model name and config
        cache_key = self.cache.get_cache_key(model_name, model_config)
        
        # Try to get from cache
        cached_model = self.cache.get(cache_key)
        if cached_model is not None:
            logging.info(f"Loaded model {model_name} from cache")
            return cached_model

        # Load model normally
        model_path = self.models_dir / model_name
        model = AutoModelForCausalLM.from_pretrained(
            str(model_path),
            **model_config
        )

        # Cache the loaded model
        model_size = sum(p.numel() * p.element_size() for p in model.parameters())
        self.cache.put(cache_key, model, model_size)
        
        return model

    def verify_model(self, model_name: str) -> bool:
        """Verify model file against expected hash"""
        model_path = self.models_dir / model_name
        if not model_path.exists():
            return False
            
        # If no hash is set, calculate and save it
        if self.config["models"][model_name]["sha256"] is None:
            calculated_hash = self.calculate_hash(model_path)
            self.config["models"][model_name]["sha256"] = calculated_hash
            self.save_config()
            logging.info(f"Saved new hash for existing {model_name}: {calculated_hash}")
            return True
            
        calculated_hash = self.calculate_hash(model_path)
        expected_hash = self.config["models"][model_name]["sha256"]
        return calculated_hash == expected_hash
    
    def ensure_models(self) -> bool:
        """Ensure all required models are downloaded"""
        success = True
        for model_name, info in self.config["models"].items():
            if info.get("required", False):
                if not self.verify_model(model_name):
                    success = success and self.download_model(model_name)
        return success
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information about a model"""
        if model_name not in self.config["models"]:
            raise ValueError(f"Unknown model: {model_name}")
        
        model_info = self.config["models"][model_name].copy()
        model_info["downloaded"] = self.verify_model(model_name)
        model_path = self.models_dir / model_name
        if model_path.exists():
            model_info["actual_size"] = model_path.stat().st_size
        return model_info

    def get_model_path(self, model_name: str) -> Path:
        """Get path to a model, downloading if necessary"""
        if model_name not in self.config["models"]:
            raise ValueError(f"Unknown model: {model_name}")
            
        if not self.verify_model(model_name):
            self.download_model(model_name)
            
        return self.models_dir / model_name
    
def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='Model Manager CLI')
    parser.add_argument('command', choices=['ensure', 'download', 'verify', 'list', 'info'],
                       help='Command to execute')
    parser.add_argument('--model', help='Model name for specific operations')
    parser.add_argument('--force', action='store_true', 
                       help='Force download even if model exists')
    parser.add_argument('--models-dir', default='backend/models',
                       help='Directory for storing models')
    parser.add_argument('--cache-dir', default='backend/cache',
                       help='Directory for model cache')
    parser.add_argument('--max-cache-size', type=float, default=4.0,
                       help='Maximum cache size in GB')
    
    args = parser.parse_args()
    
    try:
        manager = ModelManager(
            models_dir=args.models_dir,
            cache_dir=args.cache_dir,
            max_cache_size_gb=args.max_cache_size
        )
        
        if args.command == 'ensure':
            if manager.ensure_models():
                print("✓ All required models are ready")
            else:
                print("✗ Failed to ensure all required models")
                sys.exit(1)
                
        elif args.command == 'info':
            if args.model:
                info = manager.get_model_info(args.model)
                print(f"\nModel: {args.model}")
                for key, value in info.items():
                    print(f"{key}: {value}")
            else:
                print("Error: --model argument required for info command")
                sys.exit(1)
                
        elif args.command == 'download':
            if not args.model:
                print("Error: --model argument required for download command")
                sys.exit(1)
            success = manager.download_model(args.model, force=args.force)
            if not success:
                print(f"Failed to download model: {args.model}")
                sys.exit(1)
            print(f"Successfully downloaded model: {args.model}")
            
        elif args.command == 'verify':
            if args.model:
                # Verify specific model
                valid = manager.verify_model(args.model)
                print(f"Model {args.model} is {'valid' if valid else 'invalid'}")
            else:
                # Verify all models
                all_valid = True
                for model_name in manager.config['models']:
                    valid = manager.verify_model(model_name)
                    print(f"Model {model_name} is {'valid' if valid else 'invalid'}")
                    all_valid = all_valid and valid
                if not all_valid:
                    sys.exit(1)
                    
        elif args.command == 'list':
            print("\nAvailable models:")
            for model_name, info in manager.config['models'].items():
                status = "Downloaded" if manager.verify_model(model_name) else "Not downloaded"
                required = "Required" if info.get('required', False) else "Optional"
                size_gb = info['size'] / (1024 ** 3)
                print(f"- {model_name}:")
                print(f"  Version: {info['version']}")
                print(f"  Status: {status}")
                print(f"  Type: {required}")
                print(f"  Size: {size_gb:.2f} GB")
                print()
                
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()