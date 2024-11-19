import os
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

def download_model():
    # Create a models directory if it doesn't exist
    os.makedirs("models/tinyllama", exist_ok=True)
    
    print("Starting download process...")
    
    # Model ID on Hugging Face
    model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    
    try:
        print(f"Downloading tokenizer from {model_id}...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_id, 
            trust_remote_code=True
        )
        
        print(f"Downloading model from {model_id}...")
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True,
            trust_remote_code=True
        )
        
        print("Saving files locally...")
        # Save the model and tokenizer locally
        model_path = "models/tinyllama"
        model.save_pretrained(model_path)
        tokenizer.save_pretrained(model_path)
        
        print(f"Download complete! Files saved to {model_path}")
        
    except Exception as e:
        print(f"Error during download: {str(e)}")
        raise

if __name__ == "__main__":
    download_model()