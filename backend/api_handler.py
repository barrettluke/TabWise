# api_handler.py
from fastapi import FastAPI, Request
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS configuration for your Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://dffdagjllfkbmnpnmofliabhhpobmfnn"],  # Add your extension's ID
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

model_name = "microsoft/Phi-3.5-mini-instruct"
model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto", torch_dtype="auto")
tokenizer = AutoTokenizer.from_pretrained(model_name)

@app.post("/predict")
async def predict(request: Request):
    data = await request.json()
    text = data["text"]
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=200).to("cuda" if torch.cuda.is_available() else "cpu")
    outputs = model.generate(**inputs, max_new_tokens=50)
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return {"response": response}