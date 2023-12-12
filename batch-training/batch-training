from influxdb_client import InfluxDBClient
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score
import numpy as np

# InfluxDB configuration
INFLUXDB_HOST = 'localhost'
INFLUXDB_PORT = 8086
INFLUXDB_TOKEN = 'tZPaYlcse6r3ixiuqysiEaDNJxnI-D9AIQb6192zEk0-l6avOtKHQP8AFI6aq8w2OKgVYtfDxifa90q94kp3yw=='
INFLUXDB_ORG = 'swat-change-detection'
INFLUXDB_BUCKET = 'water-treatment'

# Construct the URL
url = f"http://{INFLUXDB_HOST}:{INFLUXDB_PORT}"

# Initialize the InfluxDBClient
client = InfluxDBClient(url=url, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)

try:
    # Query data from InfluxDB
    start_time = '2019-07-20T00:00:00Z'
    end_time = '2019-07-20T23:59:59Z'
    query = f'from(bucket: "{INFLUXDB_BUCKET}") |> range(start: {start_time}, stop: {end_time})'

    result = client.query_api().query(org=INFLUXDB_ORG, query=query)


    # Extract values from the result
    values = [record.get_value() for table in result for record in table.records]

    # Convert values to numpy array for analysis
    data = np.array(values)

    # Check if data is not empty
    if data.size > 0:
        # last column is the attack_label
        X = data[:-1]  
        y = data[-1]   

        # Reshape y to ensure it's a 1D array
        y = y.ravel()

        # Split the data into training and testing sets
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, random_state=42)

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
