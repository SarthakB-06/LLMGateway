import requests
import random
import time
from concurrent.futures import ThreadPoolExecutor

# Your FastAPI endpoint
URL = "http://localhost:8000/api/v1/chat"

# The models we want to test on the dashboard
# A mix of Google and Groq (LLaMA/Mixtral) models
MODELS = [
    "gemini-2.5-flash", 
    "llama3-8b-8192",         # Groq's ultra-fast model
    "mixtral-8x7b-32768"      # Groq's high-intelligence model
]
# A mix of prompts (notice the two Margarita ones to intentionally trigger your Semantic Cache)
PROMPTS = [
    "What is the speed of light?",
    "How do you make a Margarita cocktail?",
    "What are the ingredients of a Margarita?", 
    "Explain quantum computing in one sentence.",
    "What is the capital of Japan?",
    "Write a Python function to reverse a string.",
    "Who wrote Romeo and Juliet?"
]

def send_request(request_id):
    model = random.choice(MODELS)
    prompt = random.choice(PROMPTS)
    
    payload = {
        "prompt": prompt,
        "model": model
    }
    
    try:
        start_time = time.time()
        response = requests.post(URL, json=payload)
        latency = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            cache_hit = data.get("usage", {}).get("cache_hit", False)
            status = "🟢 CACHE HIT" if cache_hit else "🔵 LIVE API"
            print(f"[{request_id:02d}] {status} | Model: {model.ljust(18)} | Latency: {latency:.0f}ms")
        else:
            print(f"[{request_id:02d}] ❌ Failed with status: {response.status_code}")
            
    except Exception as e:
        print(f"[{request_id:02d}] ⚠️ Error: {e}")

def run_load_test(total_requests=2, concurrent_threads=5):
    print(f"\n🚀 Starting traffic generator: {total_requests} requests across {len(MODELS)} models...")
    print("-" * 65)
    
    # ThreadPoolExecutor allows us to send multiple requests at the exact same time
    with ThreadPoolExecutor(max_workers=concurrent_threads) as executor:
        executor.map(send_request, range(total_requests))
        
    print("-" * 65)
    print("🏁 Load test complete! Check your React Dashboard.")

if __name__ == "__main__":
    run_load_test()