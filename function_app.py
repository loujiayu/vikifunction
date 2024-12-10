import azure.functions as func
import hashlib
import json
import requests  
import json
import logging
import os
import traceback
import redis

from openai import AzureOpenAI
from azure.functions import HttpRequest, HttpResponse
from azure.storage.blob import BlobServiceClient
from azure_storage import save_to_table
from openai_message import assistant_message

app = func.FunctionApp()

@app.route(route="medai", auth_level=func.AuthLevel.ANONYMOUS)
def medai(req: func.HttpRequest) -> func.HttpResponse:
    
    logging.info('Python HTTP trigger function processed a request.')
    try:
        client = AzureOpenAI(
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key= os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-05-01-preview"
        )
        
        prompt = req.params.get('prompt')
        thread_id = req.params.get('thread_id')

        if not prompt:
            response_data = {
                "message": f"Hello, This HTTP triggered function executed successfully.",
            }
            return func.HttpResponse(
                json.dumps(response_data),
                status_code=200,
                mimetype="application/json")

        logging.info(f'prompt: {prompt}, thread id: {thread_id}')
        message, thread_id = assistant_message(client, thread_id, prompt, save_to_table)

        response_data = {
            "thread_id": thread_id,
            "message": message,
        }

        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype="application/json")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        stack = traceback.extract_stack()
        for line in stack:
            logging.debug(line)

@app.route(route="chat", auth_level=func.AuthLevel.ANONYMOUS)
def chat(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Get the request payload (messages)
        request_data = req.get_json()
        messages = request_data.get('messages')

        if not messages:
            return func.HttpResponse(
                "'messages' field is required in the request body.",
                status_code=400
                )
    except ValueError:
        return func.HttpResponse(
            "Invalid request. Ensure the request body is JSON with 'messages' field.",
            status_code=400
        )
    
    cache_key = f"chat:{generate_cache_key(messages)}"
    redis_client = init_redis()

    cached_response = redis_client.get(cache_key)

    if cached_response:
        logging.info("Returning cached response.")
        # Return cached response
        return func.HttpResponse(
            cached_response,
            status_code=200,
            mimetype="application/json"
        )

    headers = {
        "Content-Type": "application/json",
        "api-key": os.getenv("AZURE_OPENAI_API_KEY"),
    }
    ENDPOINT = "https://vikiopenai1.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-05-01-preview"
    payload = {
        "messages": messages,
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 800
    }
    logging.info(payload)
    try:
        response = requests.post(ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.RequestException as e:
        raise SystemExit(f"Failed to make the request. Error: {e}")

    response_json = response.json()
    response_text = response_json['choices'][0]['message']['content']
    
    response_data = {
        "response": response_text
    }

    response_json_string = json.dumps(response_data)

    try:
        one_month_ttl = 30 * 24 * 60 * 60  # 30 days in seconds
        redis_client.set(cache_key, response_json_string, ex=one_month_ttl)
        logging.info("Response cached successfully.")
    except Exception as e:
        logging.error(f"Failed to cache the response in Redis. Error: {e}")

    return func.HttpResponse(
        response_json_string,
        status_code=200,
        mimetype="application/json")


@app.route(route="fetchprompt", auth_level=func.AuthLevel.ANONYMOUS)
def fetchprompt(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # name = req.params.get('index')
    connection_string = os.getenv("VikiStorageAccountConnectionString")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    container_name = "prompts"

    file_list = ["1", "2", "3", "4", "5", "6"]

    # Get the container client
    container_client = blob_service_client.get_container_client(container_name)

    response_data = {}
    for file in file_list:
        blob_name = f"{file}.txt"
        # Get the blob client
        blob_client = container_client.get_blob_client(blob_name)

        # Download the blob as bytes
        blob_data = blob_client.download_blob()

        data = blob_data.readall().decode('utf-8')

        logging.info(data)
        response_data[file] = data
    return func.HttpResponse(
        json.dumps(response_data),
        status_code=200,
        mimetype="application/json")



@app.route(route="editprompt", auth_level=func.AuthLevel.ANONYMOUS)
def editprompt(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request to edit prompt.')

    # Get connection string from environment variables
    connection_string = os.getenv("VikiStorageAccountConnectionString")
    if not connection_string:
        logging.error("Connection string not found in environment variables.")
        return func.HttpResponse(
            "Connection string is missing.",
            status_code=500
        )

    # Get the file name and new content from the request body
    try:
        request_data = req.get_json()
        file_name = request_data.get('file_name')
        new_content = request_data.get('new_content')

        if not file_name or not new_content:
            return func.HttpResponse(
                "Both 'file_name' and 'new_content' must be provided.",
                status_code=400
            )

    except ValueError:
        return func.HttpResponse(
            "Invalid request. Ensure the request body is JSON with 'file_name' and 'new_content'.",
            status_code=400
        )

    try:
        # Initialize the BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_name = "prompts"

        # Get the container client
        container_client = blob_service_client.get_container_client(container_name)

        # Define the blob name based on the file name
        blob_name = f"{file_name}.txt"
        blob_client = container_client.get_blob_client(blob_name)

        # Upload the new content to the blob
        blob_client.upload_blob(new_content, overwrite=True)

        logging.info(f"Successfully updated content for {blob_name}")

        return func.HttpResponse(
            json.dumps({"message": f"Prompt {file_name} updated successfully."}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"An error occurred while updating the blob: {e}")
        return func.HttpResponse(
            f"An error occurred: {str(e)}",
            status_code=500
        )


def generate_cache_key(messages):
    # Convert the messages to a JSON string
    messages_json = json.dumps(messages, sort_keys=True)
    # Generate a SHA256 hash of the JSON string
    return hashlib.sha256(messages_json.encode()).hexdigest()

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
        logging.info("Connected to Redis successfully.")
        return redis_client
    except redis.ConnectionError as e:
        raise SystemExit(f"Failed to connect to Redis. Error: {e}")
