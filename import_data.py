import csv
import json
from azure.data.tables import TableServiceClient, TableEntity

# Function to load connection string from local.settings.json
def load_connection_string():
    try:
        with open("local.settings.json", "r") as file:
            settings = json.load(file)
            return settings["Values"]["AzureWebJobsStorage"]
    except FileNotFoundError:
        print("local.settings.json file not found.")
        return None
    except KeyError:
        print("AzureWebJobsStorage not found in local.settings.json.")
        return None

# Function to create a table if it doesn't already exist
def create_table_if_not_exists(service_client, table_name):
    try:
        service_client.create_table(table_name)
        print(f"Table '{table_name}' created.")
    except Exception as e:
        print(f"Table '{table_name}' already exists or an error occurred: {e}")

# Function to import CSV data into Azure Table Storage
def import_csv_to_table(file_path, table_client):
    with open(file_path, mode='r', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        
        for row in reader:
            patient_id = row['Patient ID']
            partition_key = patient_id[0]  # First character of Patient ID
            
            # Create the entity
            entity = TableEntity()
            entity['PartitionKey'] = partition_key
            entity['RowKey'] = patient_id
            
            # Prepare other data as JSON
            other_data = {key.replace(' ', '_'): value for key, value in row.items() if key != 'Patient ID'}
            entity['Data'] = json.dumps(other_data)  # Store all remaining data as a JSON object
            
            # Insert entity into the table
            try:
                table_client.create_entity(entity)
                print(f"Inserted entity: {entity['RowKey']}")
            except Exception as e:
                print(f"Error inserting entity {entity['RowKey']}: {e}")

def main():
    # Load connection string from local.settings.json
    connection_string = load_connection_string()
    if not connection_string:
        print("Connection string could not be loaded. Exiting.")
        return
    
    # File path to your CSV
    file_path = "synthetic_medical_data.csv"  # Replace with your CSV file path
    table_name = "patients"  # Replace with your table name

    # Initialize the Table Service Client
    table_service_client = TableServiceClient.from_connection_string(conn_str=connection_string)
    create_table_if_not_exists(table_service_client, table_name)
    
    # Get a reference to the table client
    table_client = table_service_client.get_table_client(table_name)
    
    # Import CSV data
    import_csv_to_table(file_path, table_client)

if __name__ == "__main__":
    main()
