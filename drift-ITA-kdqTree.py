import json
from confluent_kafka import Consumer, KafkaError
import pandas as pd
from sklearn.feature_selection import mutual_info_regression
import numpy as np
from scipy.stats import entropy
from pymongo import MongoClient
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from scipy.spatial import cKDTree



def detect_and_save_drift(current_data, previous_data, features, threshold=0.00001):

    
    current_features = np.array([current_data[field] for field in features])

    # Ensure 2D structure for KdqTree
    current_features = current_features.reshape(1, -1)

    previous_features = np.array([previous_data[field] for field in features])

    # Ensure 2D structure for KdqTree
    previous_features = previous_features.reshape(-1, len(features))

    print(current_features)
    
    kdtree = cKDTree(previous_features.T)

    # Query k-nearest neighbors for each sample in current data
    distances, _ = kdtree.query(current_features.T, k=2)

    # Calculate average distance for each sample in current data
    avg_distances_current = np.mean(distances[:, 1], axis=0)

    # Calculate KL divergence between previous and current data
    kl_divergence = entropy(avg_distances_current, np.mean(distances[:, 1]))

    # Check for drift based on KL divergence
    drift_detected = kl_divergence > threshold

    # Save data to InfluxDB
    json_body = [
        {
            "measurement": influxdb_measurement,
            "tags": {"event": "drift_detected"},
            "time": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "fields": {"kl_divergence": kl_divergence}
        }
    ]
    #influxdb_client.write_points(json_body)
    save_to_influxdb(json_body, client, influxdb_database, influxdb_measurement)

    # Save data to MongoDB
    drift_detected_python_bool = bool(drift_detected)
    drift_results=({
        "timestamp": datetime.utcnow(),
        "drift_detected": drift_detected_python_bool,
        "kl_divergence": kl_divergence
    })
    save_to_mongodb(drift_results, mongodb_uri, database, collection)
    return drift_detected


def clean_and_convert(data):
    cleaned_data = {}
    
    for key, value in data.items():
        try:
            cleaned_data[key] = float(value)
        except (ValueError, TypeError):
            cleaned_data[key] = value

    return cleaned_data
def save_to_influxdb(data, client, influxdb_database, influxdb_measurement):
    
    write_api.write(influxdb_database, org , data ,write_precision='s')

def save_to_mongodb(data, mongodb_uri, database, collection):
    client = MongoClient(mongodb_uri)
    db = client[database]
    col = db[collection]

    data["_id"] = datetime.now().isoformat()
    col.insert_one(data)

    client.close()

def consume_and_detect_drift(consumer_conf, topic, mongodb_uri, database, collection, fields):
    consumer = Consumer(consumer_conf)
    consumer.subscribe([topic])
    
    previous_data = None

    try:
        while True:
            msg = consumer.poll(timeout=1000)
            if msg is not None:
                try:
                    data = json.loads(msg.value())
                    cleaned_data = clean_and_convert(data)
                    print(cleaned_data)
                    
                    if previous_data is not None:
                        print('1')
                        drift_detected = detect_and_save_drift(cleaned_data, previous_data, fields)
                         
                        print("Drift Detected:", drift_detected)
                        
                    previous_data = cleaned_data
                    
                except ValueError as e:
                    print(f"Error processing message: {e}")

    except KeyboardInterrupt:
        pass

    finally:
        consumer.close()

if __name__ == "__main__":
    consumer_conf = {
        'bootstrap.servers': 'localhost:29092',
        'group.id': 'water-treatment-group5',
        'auto.offset.reset': 'latest'
    }
    topic = 'water-treatment'
    mongodb_uri = 'mongodb://admin:admin@localhost'
    database = 'swatData'
    collection = 'swatres'
    fields_to_check = ['FIT 401', 'LIT 301', 'P601 Status', 'MV201', 'P101 Status', 'MV 501', 'P301 Status']  # Specify the fields you want to check
    host = "localhost"
    port = 8086
    influxdb_database = "swatBUC"
    influxdb_username = "admin"
    influxdb_password = "admin123"
    influxdb_measurement='drift-meaturment-ITA-kdqTree-KL'
    token = "LdtBZ1bHhwj_mZLxYovlE3cUjGJmzOzLlaiU9eBzQkpSRMxrDNemP5HnYrAnYcj34M8uCUf53BcKP_M-PRUfmQ=="
    org = "swatorg"
    
    client = InfluxDBClient(url="http://localhost:8086", token=token, org=org)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    if client.ping():
        print(f"Connected to InfluxDB: {database}")
    else:
        print(f"Failed to connect to InfluxDB")
        
    consume_and_detect_drift(consumer_conf, topic, mongodb_uri, database, collection, fields_to_check)
