import yaml
from pathlib import Path
import os

def load_category_keywords(config_path: str = "categories.yaml") -> dict:
    """
    Load category keywords from a YAML configuration file.
    
    Args:
        config_path (str): Path to the YAML configuration file
        
    Returns:
        dict: Dictionary of categories and their keywords
    """
    try:
        # Get the directory where the current script is located
        current_dir = Path(__file__).parent.absolute()
        
        # Try multiple possible locations for the config file
        possible_paths = [
            Path(config_path),  # Try direct path
            current_dir / config_path,  # Try relative to current script
            current_dir.parent / config_path,  # Try parent directory
            current_dir / 'config' / config_path,  # Try config subdirectory
        ]
        
        # Try each path until we find the file
        for path in possible_paths:
            if path.is_file():
                with open(path) as f:
                    config = yaml.safe_load(f)
                    return config.get('categories', {})
                    
        # If we get here, we couldn't find the file
        raise FileNotFoundError(
            f"Could not find '{config_path}' in any of these locations:\n" +
            "\n".join(str(p) for p in possible_paths)
        )
            
    except Exception as e:
        raise RuntimeError(f"Failed to load category keywords: {str(e)}")