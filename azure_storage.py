import uuid
import os
import logging
import json

from azure.data.tables import TableServiceClient, TableEntity

def save_to_table(data):
    if data is None:
        return
    connection_string = os.getenv("VikiStorageAccountConnectionString")
    table_service_client = TableServiceClient.from_connection_string(conn_str=connection_string)
    table_name = "patients"
    table_client = table_service_client.get_table_client(table_name)

    patient_id = str(uuid.uuid4())
    partition_key = patient_id[0]  # First character of Patient ID
    entity = TableEntity()
    entity['PartitionKey'] = partition_key
    entity['RowKey'] = patient_id
    
    other_data = {key.replace(' ', '_'): value for key, value in data.items() if key != 'Patient ID'}
    entity['Data'] = json.dumps(other_data)  # Store all remaining data as a JSON object
    
    if os.getenv("VIKIENV") == "local":
      entity['Test'] = "true"

    # Insert entity into the table
    try:
        table_client.create_entity(entity)
        logging.info(f"Inserted entity: {entity['RowKey']}")
    except Exception as e:
        logging.info(f"Error inserting entity {entity['RowKey']}: {e}")
