import requests
import json

url = "http://localhost:8000/generate"

test_texts = [
    "It connects buyers and sellers through a user-friendly interface.",
    "Track the location of your pets in real-time using GPS.",
    "Analyze and predict weather patterns using satellite data.",
    "Create and mint your own NFTs on the blockchain.",
    "Is an online auction platform for art, antiques, and collectibles."
]

for text in test_texts:
    try:
        response = requests.post(url, json={"prompt": text})
        print("\nInput:", text)
        if response.status_code == 200:
            result = response.json()
            print("Category:", result["category"])
            print("Confidence:", result["confidence"])
            print("Explanation:", result["explanation"])
        else:
            print("Error:", response.text)
    except Exception as e:
        print("Error:", str(e))