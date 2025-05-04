import os
import requests
import json

# Load token from environment variable
HF_TOKEN = os.getenv("HF_TOKEN")
API_URL = "https://jddif7wjpdwwjylo.us-east-1.aws.endpoints.huggingface.cloud"

if not HF_TOKEN:
    print("Warning: HF_TOKEN not set in environment variables")
    HF_TOKEN = input("Enter your Hugging Face API token: ")

# Headers
headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# Test prompt
prompt = "Apple just launched its new product. What will be the stock price in coming week?"

# Most HF endpoints expect this simplified format
payload = {
    "inputs": prompt
}

print(f"Sending request to: {API_URL}")
print(f"Payload: {json.dumps(payload)}")

try:
    response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
    print(f"Response status code: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Error response: {response.text}")
    else:
        result = response.json()
        print(f"Raw response: {json.dumps(result, indent=2)}")
        
        # Extract the text based on the response format
        if isinstance(result, list) and result:
            if isinstance(result[0], dict) and "generated_text" in result[0]:
                print(f"\nGenerated text: {result[0]['generated_text']}")
            else:
                print(f"\nGenerated text: {result[0]}")
        elif isinstance(result, dict) and "generated_text" in result:
            print(f"\nGenerated text: {result['generated_text']}")
        else:
            print(f"\nGenerated text: {result}")
            
except Exception as e:
    print(f"Error: {str(e)}") 