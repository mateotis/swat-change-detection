import pandas as pd
from confluent_kafka import Producer
import time

def delivery_report(err, msg):
	if err is not None:
		print(f'Record delivery failed: {err}')

df = pd.read_excel("../data/swat-dataset.xlsx", skiprows = 1) # Load SWaT data
df = df.drop(0, axis = 0) # Remove unnecessary row
df = df.rename(columns={"GMT +0": "timestamp"}) # Give the timestamp column a proper name
df = df.reset_index()

df = df[["timestamp", "FIT 401", "LIT 301", "P601 Status", "MV201", "P101 Status", "MV 501", "P301 Status"]] # Reduce dataset to the columns that will be attacked (plus the timestamp)

prod = Producer({'bootstrap.servers': 'localhost:9092'}) # Set up producer
topic = "water-treatment"

for idx, row in df.iterrows():
	timestamp = row["timestamp"] # Pass the timestamp as the key
	jsonValue = row.drop("timestamp").to_json() # Convert data to json
	prod.produce(topic, key = timestamp, value = jsonValue, callback=delivery_report) # Ingest into Kafka
	prod.flush() # Ensure it's delivered
	
	print("\r", end = '')
	print(idx, "records delivered.", end = '', flush = True)

	if(idx % 100 == 0): # Sleep for a second after every 100 records to simulate the arrival of data in "real-time" 
		time.sleep(1)

print("\n")