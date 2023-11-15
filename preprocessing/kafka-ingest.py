import pandas as pd
from confluent_kafka import Producer

def delivery_report(err, msg):
	if err is not None:
		print(f'Record delivery failed: {err}')
	else:
		print(f'Record delivered to {msg.topic()} [{msg.partition()}]')

df = pd.read_excel("../data/swat-dataset.xlsx", skiprows = 1) # Load SWaT data
df = df.drop(0, axis = 0) # Remove unnecessary row

prod = Producer({'bootstrap.servers': 'localhost:9092'}) # Set up producer
topic = "water-treatment"

for idx, row in df.iterrows():
	jsonRow = row.to_json() # Convert data to json

	prod.produce(topic, jsonRow, callback=delivery_report) # Ingest into Kafka
	prod.flush()