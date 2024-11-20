# File: backend/utils/inference_handler.py

from ctransformers import AutoModelForCausalLM
import logging
from typing import Optional, Dict
from pathlib import Path

class InferenceHandler:
    def __init__(self, model_path: Path, 
                 context_length: int = 2048,
                 gpu_layers: int = 0,
                 temperature: float = 0.7,
                 top_p: float = 0.95):
        """
        Initialize the inference handler for GGUF models
        
        Args:
            model_path: Path to the .gguf model file
            context_length: Maximum context length for the model
            gpu_layers: Number of layers to offload to GPU (0 for CPU-only)
            temperature: Sampling temperature (0.0 to 1.0)
            top_p: Top-p sampling parameter (0.0 to 1.0)
        """
        self.model_path = model_path
        self.context_length = context_length
        self.gpu_layers = gpu_layers
        self.temperature = temperature
        self.top_p = top_p
        self.model = None
        
    def load_model(self):
        """Load the GGUF model"""
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                str(self.model_path),
                model_type="llama",
                context_length=self.context_length,
                gpu_layers=self.gpu_layers,
                temperature=self.temperature,
                top_p=self.top_p
            )
            logging.info(f"Successfully loaded model from {self.model_path}")
            return True
        except Exception as e:
            logging.error(f"Error loading model: {str(e)}")
            return False
            
    def generate_response(self, 
                         prompt: str,
                         max_tokens: int = 256,
                         temperature: Optional[float] = None,
                         top_p: Optional[float] = None) -> str:
        """
        Generate a response for the given prompt
        
        Args:
            prompt: Input text prompt
            max_tokens: Maximum number of tokens to generate
            temperature: Optional override for sampling temperature
            top_p: Optional override for top-p sampling
            
        Returns:
            Generated text response
        """
        if self.model is None:
            if not self.load_model():
                raise RuntimeError("Failed to load model")
                
        # Use instance defaults if not specified
        temp = temperature if temperature is not None else self.temperature
        p = top_p if top_p is not None else self.top_p
        
        try:
            # Use the TinyLlama chat template
            formatted_prompt = f"<|system|>You are a helpful AI assistant.</s><|user|>{prompt}</s><|assistant|>"
            
            response = self.model(
                formatted_prompt,
                max_new_tokens=max_tokens,
                temperature=temp,
                top_p=p,
                stream=False
            )
            
            # Clean up response if needed
            response = response.split("<|assistant|>")[-1].strip()
            return response
            
        except Exception as e:
            logging.error(f"Error generating response: {str(e)}")
            raise

    def __del__(self):
        """Cleanup when the handler is destroyed"""
        self.model = None