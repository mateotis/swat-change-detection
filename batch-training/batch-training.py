from influxdb_client import InfluxDBClient
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.tree import DecisionTreeClassifier
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

    SPLIT_THRESHOLD = 11000
    
    # Check if data is not empty
    if len(df) > 0:
        # last column is the attack_label
        training_set = df[:SPLIT_THRESHOLD] # First 11 thousand records form the training set: this includes the lengthy period of "normal" operation and the first three attacks
        testing_set = df[SPLIT_THRESHOLD:] # The remaining ~4 thousand are the test set; this includes the other three attacks

        # Split the data into training and testing sets
        X_train = training_set.drop(columns = ["attack_label"])
        y_train = training_set["attack_label"].ravel()
        X_test = testing_set.drop(columns = ["attack_label"])
        y_test = testing_set["attack_label"].ravel()

        # Initialize the Decision Tree classifier
        classifier = DecisionTreeClassifier()

        # Batch training
        classifier.fit(X_train, y_train)

        # Make predictions on the test set
        y_pred = classifier.predict(X_test)

        # Evaluate accuracy
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Accuracy: {accuracy}") # The accuracy of the decision tree is around 72%, better than the other methods (RF and SVM) we tried
        # Still, it shows how difficult change detection is on this dataset

        cm = confusion_matrix(y_test, y_pred, labels=classifier.classes_)
        print("Confusion matrix:", cm)
    else:
        print("No data retrieved from InfluxDB.")

finally:
    # Close the InfluxDBClient to release resources
    client.close()
