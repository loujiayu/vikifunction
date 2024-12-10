import azure.functions as func
import hashlib
import json
import requests  
import json
import logging
import os
import base64
import redis
from azure.identity import ClientSecretCredential


def init_redis():
    """
    Initializes and returns a Redis client instance.
    """

    redis_host = os.getenv('REDIS_HOST')  # Redis host from environment variables
    redis_password = os.getenv('REDIS_PASSWORD')  # Redis password from environment variables
    redis_port = int(os.getenv('REDIS_PORT', 6380))  # Redis port, default to 6379
    try:
        # Initialize the Redis client
        redis_client = redis.StrictRedis(
            host=redis_host,
            port=redis_port,
            ssl=True,
            password=redis_password,
            # username=user_name,
            decode_responses=True  # Enables Unicode responses
        )

        # Test the connection
        redis_client.ping()
        print("Connected to Redis successfully.")
        return redis_client
    except redis.ConnectionError as e:
        raise SystemExit(f"Failed to connect to Redis. Error: {e}")

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

init_redis()
