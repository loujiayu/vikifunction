import azure.functions as func
import datetime
import requests
import json
import logging
import os
import traceback

from openai import AzureOpenAI
from azure.functions import HttpRequest, HttpResponse
from azure.storage.blob import BlobServiceClient
from azure_storage import save_to_table
from openai_message import assistant_message

def load_settings_from_json(json_file):
    with open(json_file, 'r') as f:
        settings = json.load(f)
    
    # Extract the "Values" section
    values = settings.get('Values', {})
    
    # Set each key in the "Values" section as an environment variable
    for key, value in values.items():
        os.environ[key] = value

# Path to your local.settings.json file
json_file = 'local.settings.json'

# Load settings from the JSON file into environment variables
load_settings_from_json(json_file)


# Configuration
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
headers = {
    "Content-Type": "application/json",
    "api-key": API_KEY,
}

# Payload for the request
payload = {
  "messages": [
    # {
    #   "role": "system",
    #   "content": "Generate the top three differential diagnoses along with their associated probabilities for a patient presenting with specific symptoms.\n\nConsider the following symptoms:\n- Fever for 3 days\n- Cough for 5 days\n- Fatigue\n\nYou are tasked with determining the most likely differential diagnoses based on these symptoms and typical clinical reasoning.\n\n# Steps\n\n1. **Analyze Symptoms:** Review each symptom separately and how they might correlate when considered together. \n2. **Identify Potential Conditions:** Consider common medical conditions that could present with these symptoms.\n3. **Probability Assessment:** Assign probabilities to each differential diagnosis based on how likely they are given the symptoms.\n\n# Output Format\n\nProvide a JSON output with the differential diagnoses and their probabilities. The structure should be as follows:\n\n```json\n[\n  {\n    \"diagnosis\": \"Diagnosis 1\",\n    \"probability\": \"Probability%\"\n  },\n  {\n    \"diagnosis\": \"Diagnosis 2\",\n    \"probability\": \"Probability%\"\n  },\n  {\n    \"diagnosis\": \"Diagnosis 3\",\n    \"probability\": \"Probability%\"\n  }\n]\n```\n\n# Notes\n\n- Consider common and significant conditions that match the symptom pattern.\n- Use reasonable, evidence-based estimates for the probabilities based on symptoms.\n- Ensure the probabilities total 100% for the three diagnoses provided.\n"
    # },
    {
        "role": "user",
        "content": "What are the top three differential diagnoses for a patient presenting with fever, cough, and fatigue?"
    }
  ],
  "temperature": 0.7,
  "top_p": 0.95,
  "max_tokens": 800
}

ENDPOINT = "https://vikiopenai1.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-05-01-preview"

# Send request
try:
    response = requests.post(ENDPOINT, headers=headers, json=payload)
    response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
except requests.RequestException as e:
    raise SystemExit(f"Failed to make the request. Error: {e}")

response_data = response.json()
response_text = response_data['choices'][0]['message']['content']
# Handle the response as needed (e.g., print or process)
print(response.json())