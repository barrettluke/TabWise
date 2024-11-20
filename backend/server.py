import torch
from ctransformers import AutoModelForCausalLM
from flask import Flask, request, jsonify
from pathlib import Path
from flask_cors import CORS
import logging
from utils.model_manager import ModelManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)


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

# Define categories with keywords
CATEGORY_KEYWORDS = {
    "E-commerce/Marketplace": ["marketplace", "buyers", "sellers", "shop", "store", "purchase", "sell", "buy", "auction", "bid", "listing", "e-commerce", "sale", "spend", "marketing"],
    "Technology/IoT": ["GPS", "tracking", "device", "sensor", "IoT", "real-time", "hardware", "monitor"],
    "Weather/Climate": ["weather", "climate", "forecast", "meteorological", "atmospheric", "prediction", "satellite", "temperature", "humidity", "precipitation", "weather patterns"],
    "Blockchain/Crypto": ["blockchain", "crypto", "NFT", "token", "mint", "cryptocurrency", "decentralized", "ledger", "smart contract", "digital asset", "wallet", "miners", "cryptocurrencies"],
    "Social Media": ["social", "posts", "sharing", "friends", "network", "community"],
    "Productivity": ["workflow", "efficiency", "tools", "organization", "tasks", "management"],
    "Entertainment": ["games", "music", "video", "streaming", "play", "watch"],
    "Healthcare": ["health", "medical", "wellness", "patient", "doctor", "treatment", "diagnosis", "hospital", "clinic", "pharmacy", "medicine", "prescription", "Healthcare"],
    "Communication": ["chat", "message", "communication", "contact", "connect"],
    "News": ["news", "articles", "updates", "information", "current events", "newsletter", "journalism", "reporting", "breaking news", "News"],
    "Education": ["learning", "learn","teaching", "education", "students", "teachers", "courses", "classes", "tutorials", "lessons", "curriculum"],
    "Finance": ["finance", "investment", "banking", "money", "stocks", "trading", "economy", "financial"],
    "Travel": ["travel", "tourism", "destination", "vacation", "trip", "hotel", "flight", "booking", "reservations"],
    "Food": ["food", "restaurant", "cuisine", "recipe", "cooking", "dining", "menu", "ingredients", "meal"],
    "Space/Aerospace": ["satellite", "space", "orbit", "launch", "rocket", "spacecraft", "astronomical", "aerospace", "constellation", "celestial", "planetary", "mission", "astronomy"],
    "Sports": ["sports", "game", "match", "team", "player", "score", "tournament", "championship", "league", "athletes", "competition", "Sports", "athletics", "playoffs", "players"],

}

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
    model_path = Path("./models/tinyllama")  # Path to your downloaded GGUF file
    
    # For Mac with Metal support
    if torch.backends.mps.is_available():
        logger.info("Using MPS (Apple Silicon) device")
        model = AutoModelForCausalLM.from_pretrained(
            str(model_path),
            model_type="llama",
            gpu_layers=50,  # Adjust based on your needs
            context_length=2048,
            temperature=0.7,
            top_p=0.95
        )
    # For CUDA
    elif torch.cuda.is_available():
        logger.info("Using CUDA device")
        model = AutoModelForCausalLM.from_pretrained(
            str(model_path),
            model_type="llama",
            gpu_layers=50,  # Adjust based on your needs
            context_length=2048,
            temperature=0.7,
            top_p=0.95
        )
    # For CPU
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
    logger.info("Model loaded successfully!")
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
            "Healthcare": "This text involves health-related services.",
            "Communication": "This text describes communication features.",
            "News": "This text involves news articles or updates.",
            "Education": "This text relates to educational content or learning resources.",
            "Finance": "This text involves financial services or investment information.",
            "Travel": "This text describes travel or tourism services.",
            "Food": "This text relates to food, recipes, or dining experiences.",
            "Space/Aerospace": "This text involves space exploration or aerospace technology.",
            "Sports": "This text describes sports events or competitions.",
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