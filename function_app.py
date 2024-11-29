import azure.functions as func
import datetime
import json
import logging
import os
import traceback

from openai import AzureOpenAI
from azure.functions import HttpRequest, HttpResponse
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