from influxdb_client import InfluxDBClient
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv() # Load environmental variables from .env file for security

# InfluxDB configuration
INFLUXDB_HOST = 'localhost'
INFLUXDB_PORT = 8086
INFLUXDB_TOKEN = os.getenv('INFLUX_TOKEN')
INFLUXDB_ORG = os.getenv('INFLUX_ORG')
INFLUXDB_BUCKET = os.getenv('INFLUX_BUCKET')

# Construct the URL
url = f"http://{INFLUXDB_HOST}:{INFLUXDB_PORT}"

# Initialize the InfluxDBClient
client = InfluxDBClient(url=url, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)

try:
    # Query data from InfluxDB
    start_time = '2019-07-20T00:00:00Z'
    end_time = '2019-07-20T23:59:59Z'
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
    |> range(start: {start_time}, stop: {end_time})
    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    |> keep(columns: ["FIT 401", "LIT 301", "P601 Status", "MV201", "P101 Status", "MV 501", "P301 Status", "attack_label"])
    '''

    df = client.query_api().query_data_frame(org=INFLUXDB_ORG, query=query) # Turn the query results into a dataframe (that's what the pivot row was for)
    df = df.drop(columns=["result", "table"])
    print(df)
    
    # Check if data is not empty
    if len(df) > 0:
        # last column is the attack_label
        X = df.drop(columns = ["attack_label"])
        y = df["attack_label"]

        # Reshape y to ensure it's a 1D array
        y = y.ravel()

        # Split the data into training and testing sets
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Initialize the Decision Tree classifier
        classifier = DecisionTreeClassifier()

        # Batch training
        classifier.fit(X_train, y_train)

        # Make predictions on the test set
        y_pred = classifier.predict(X_test)

        # Evaluate accuracy
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Accuracy: {accuracy}")
    else:
        print("No data retrieved from InfluxDB.")

finally:
    # Close the InfluxDBClient to release resources
    client.close()
