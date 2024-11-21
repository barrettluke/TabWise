import torch
from ctransformers import AutoModelForCausalLM
from flask import Flask, request, jsonify
from pathlib import Path
from flask_cors import CORS
import logging
from utils.model_manager import ModelManager
from utils.config import load_category_keywords

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Load categories from config file
CATEGORY_KEYWORDS = load_category_keywords()


# Initialize the ModelManager
manager = ModelManager(
    models_dir="./models",  # Where models will be stored
    cache_dir="./cache",    # Where model cache will be stored
    max_cache_size_gb=4.0   # Maximum size of model cache
)

# Ensure all required models are downloaded
# This will download TinyLlama if it's not already present
success = manager.ensure_models()
if not success:
    raise RuntimeError("Failed to download required models")

# Determine the best device
if torch.backends.mps.is_available():
    device = torch.device("mps")
    logger.info("Using MPS (Apple Silicon) device")
elif torch.cuda.is_available():
    device = torch.device("cuda")
    logger.info("Using CUDA device")
else:
    device = torch.device("cpu")
    logger.info("Using CPU device")


def classify_text(text):
    text = text.lower()
    matches = {}
    
    # Count keyword matches for each category
    for category, keywords in CATEGORY_KEYWORDS.items():
        count = sum(1 for keyword in keywords if keyword.lower() in text)
        if count > 0:
            matches[category] = count
    
    if matches:
        best_category = max(matches.items(), key=lambda x: x[1])
        confidence = "High" if best_category[1] > 1 else "Medium"
        return best_category[0], confidence
    
    return "Other", "Low"

# Initialize model with ctransformers
try:
    logger.info("Starting to load model...")
    model_path = Path("./models/tinyllama")
    
    # Start with CPU by default for more stability
    gpu_layers = 0
    
    if torch.backends.mps.is_available():
        try:
            logger.info("Attempting to use MPS (Apple Silicon) device...")
            # Reduce GPU layers to prevent memory issues
            gpu_layers = 32  # Reduced from 50
            model = AutoModelForCausalLM.from_pretrained(
                str(model_path),
                model_type="llama",
                gpu_layers=gpu_layers,
                context_length=2048,
                temperature=0.7,
                top_p=0.95
            )
            logger.info("Successfully initialized model with MPS")
        except Exception as e:
            logger.warning(f"Failed to initialize with MPS, falling back to CPU: {e}")
            gpu_layers = 0
            model = AutoModelForCausalLM.from_pretrained(
                str(model_path),
                model_type="llama",
                gpu_layers=0,
                context_length=2048,
                temperature=0.7,
                top_p=0.95
            )
    elif torch.cuda.is_available():
        logger.info("Using CUDA device")
        model = AutoModelForCausalLM.from_pretrained(
            str(model_path),
            model_type="llama",
            gpu_layers=50,
            context_length=2048,
            temperature=0.7,
            top_p=0.95
        )
    else:
        logger.info("Using CPU device")
        model = AutoModelForCausalLM.from_pretrained(
            str(model_path),
            model_type="llama",
            gpu_layers=0,
            context_length=2048,
            temperature=0.7,
            top_p=0.95
        )
    logger.info(f"Model loaded successfully with {gpu_layers} GPU layers!")
except Exception as e:
    logger.error(f"Error loading model: {str(e)}")
    raise

@app.route("/generate", methods=["POST"])
def generate():
    try:
        text = request.json.get("prompt", "")
        logger.info(f"Processing text: {text}")
        
        # Use keyword-based classification
        category, confidence = classify_text(text)
        
        # Format prompt for TinyLlama
        formatted_prompt = f"<|system|>You are a helpful AI assistant.</s><|user|>{text}</s><|assistant|>"
        
        # Generate response using the model
        response = model(
            formatted_prompt,
            max_new_tokens=256,
            temperature=0.7,
            top_p=0.95,
            stream=False
        )
        
        # Clean up response
        response = response.split("<|assistant|>")[-1].strip()
        
        # Generate explanation based on category
        explanations = {
            "E-commerce/Marketplace": "This text describes a platform for buying and selling.",
            "Technology/IoT": "This text involves technological devices or IoT capabilities.",
            "Weather/Climate": "This text relates to weather analysis or climate data.",
            "Blockchain/Crypto": "This text involves blockchain technology or cryptocurrency.",
            "Social Media": "This text describes social networking features.",
            "Productivity": "This text involves tools for improving efficiency.",
            "Entertainment": "This text relates to entertainment content.",
            "Health/Medical": "This text involves health-related services.",
            "Communication": "This text describes communication features.",
            "News": "This text involves news articles or updates.",
            "Education": "This text relates to educational content or learning resources.",
            "Finance": "This text involves financial services or investment information.",
            "Travel": "This text describes travel or tourism services.",
            "Food": "This text relates to food, recipes, or dining experiences.",
            "Space/Aerospace": "This text involves space exploration or aerospace technology.",
            "Sports": "This text describes sports events or competitions.",
            "Fitness": "This text involves fitness activities or wellness programs.",
            "Other": "This text doesn't clearly match our predefined categories."
        }
        
        return jsonify({
            "category": category,
            "confidence": confidence,
            "explanation": explanations.get(category, "Category determined based on content analysis.")
        })
            
    except Exception as e:
        logger.error(f"Error during classification: {str(e)}")
        return jsonify({
            "category": "Error",
            "confidence": "Low",
            "explanation": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)