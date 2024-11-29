import os
import time
import re
import traceback
import logging

def parse_suggestsions(message):
    allowed_keys = [
        "Age", "Gender", "Medical Condition", "Blood Glucose (mg/dL)",
        "Na (mmol/L)", "K (mmol/L)", "Cl (mmol/L)", "iCa (mmol/L)",
        "TCO2 (mmol/L)", "BUN (mg/dL)", "Crea (mg/dL)", "BP Systolic",
        "BP Diastolic", "Height (cm)", "Weight (kg)", "Smoking Status",
        "Alcohol Consumption", "Oxygen Saturation (SpO2)", "Respiratory Rate",
        "Blood Type", "Medication Adherence", "Sleep Duration (hours)", "Occupation",
        "A1c(%)", "BPM", "BCM"
    ]

    # Extract key-value pairs using regex and filter by allowed keys
    pattern = r"^(.*?):\s*(.*)$"
    data = {}

    for line in message.splitlines():
        match = re.match(pattern, line.strip())
        if match:
            key, value = match.groups()
            key = key.strip()
            value = value.strip()
            if key in allowed_keys:
                data[key] = value

    return data

def get_latest_suggestsion(client, thread_id):
    messages = client.beta.threads.messages.list(
        thread_id=thread_id
    )

    # Filter the latest assistant response
    assistant_messages = [msg for msg in messages if msg.role == "assistant"]
    if assistant_messages:
        latest_response = next(
            (msg for msg in sorted(assistant_messages, key=lambda x: x.created_at, reverse=True) 
            if "age" in msg.content[0].text.value.lower() and "gender" in msg.content[0].text.value.lower()),
            None
        )
        if latest_response is not None:
          return parse_suggestsions(latest_response.content[0].text.value)

def get_latest_response(client, thread_id):
    messages = client.beta.threads.messages.list(
        thread_id=thread_id
    )

    # Filter the latest assistant response
    assistant_messages = [msg for msg in messages if msg.role == "assistant"]

    if assistant_messages:
        # Get the latest message from the assistant
        latest_response = assistant_messages[0]  # The last message in the list
        
        logging.info(f"Assistant Response: {latest_response.content}")
        return latest_response.content[0].text.value
    else:
        logging.info("No response from the assistant.")


def assistant_message(client, thread_id, content, action):
    try:
        # Step 1: Create a thread
        if (thread_id == None):
            thread = client.beta.threads.create()
            thread_id = thread.id

        # Step 2: Add a user question to the thread
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content
        )

        # Step 3: Run the thread with the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=os.getenv("ASSISTANT_ID")
        )

        # Step 4: Polling the run status
        while run.status in ["queued", "in_progress", "cancelling"]:
            time.sleep(1)  # Wait for a second before checking again
            run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
        logging.info(f'run.status: {run.status}')
        # Step 5: Handle the run's final status
        if run.status == "completed": 
            response = get_latest_response(client, thread_id)

            return response, thread_id
        elif run.status == "requires_action":
            client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run.id,
            tool_outputs=[{"tool_call_id": run.required_action.submit_tool_outputs.tool_calls[0].id, "output": "true"}]
            )

            while True:
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
                if run.status in ['completed', 'requires_action', 'failed']:
                    response = get_latest_suggestsion(client, thread_id)
                    if response.keys() == 0:
                        return "Please provide more details!", thread_id
                    action(response)
                    # response = get_latest_response(client, thread_id)
                    logging.info(response)
                    return "Save to DB successfully!", thread_id
                time.sleep(1)        
        else:
            logging.info(f"Run failed or was canceled. Status: {run.status}")

    except Exception as e:
        logging.info(f"An error occurred: {e}")
        stack = traceback.extract_stack
        for line in stack:
            logging.debug(line)
