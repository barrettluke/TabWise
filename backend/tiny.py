import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

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
    "E-commerce/Marketplace": ["marketplace", "buyers", "sellers", "shop", "store", "purchase", "sell", "buy", "auction", "bid", "listing", "e-commerce", "sale"],
    "Technology/IoT": ["GPS", "tracking", "device", "sensor", "IoT", "real-time", "hardware", "monitor"],
    "Weather/Climate": ["weather", "climate", "forecast", "meteorological", "atmospheric", "prediction", "satellite"],
    "Blockchain/Crypto": ["blockchain", "crypto", "NFT", "token", "mint", "cryptocurrency", "decentralized", "ledger", "smart contract", "digital asset", "wallet", "miners", "cryptocurrencies"],
    "Social Media": ["social", "posts", "sharing", "friends", "network", "community"],
    "Productivity": ["workflow", "efficiency", "tools", "organization", "tasks", "management"],
    "Entertainment": ["games", "music", "video", "streaming", "play", "watch"],
    "Healthcare": ["health", "medical", "wellness", "patient", "doctor", "treatment", "diagnosis", "hospital", "clinic", "pharmacy", "medicine", "prescription", "Healthcare"],
    "Communication": ["chat", "message", "communication", "contact", "connect"],
    "News": ["news", "articles", "updates", "information", "current events", "newsletter", "journalism", "reporting", "breaking news"],
    "Education": ["learning", "learn","teaching", "education", "students", "teachers", "courses", "classes", "tutorials", "lessons", "curriculum"],
    "Finance": ["finance", "investment", "banking", "money", "stocks", "trading", "economy", "financial"],
    "Travel": ["travel", "tourism", "destination", "vacation", "trip", "hotel", "flight", "booking", "reservations"],
    "Food": ["food", "restaurant", "cuisine", "recipe", "cooking", "dining", "menu", "ingredients", "meal"],
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
        # Get category with most keyword matches
        best_category = max(matches.items(), key=lambda x: x[1])
        confidence = "High" if best_category[1] > 1 else "Medium"
        return best_category[0], confidence
    
    return "Other", "Low"

try:
    logger.info("Starting to load model...")
    model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float32,
        low_cpu_mem_usage=True
    ).to(device)
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