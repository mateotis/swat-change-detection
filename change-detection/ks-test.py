import random
from river import drift
from confluent_kafka import Consumer, KafkaException, TopicPartition
from confluent_kafka.admin import AdminClient
import json
import pandas as pd
import numpy as np

def assignment_callback(consumer, partitions):
    for p in partitions:
        print(f'Assigned to {p.topic}, partition {p.partition}')

def reset_offset(consumer, topic): # Reset the offset for a topic back to the start
	resetTP = [TopicPartition(topic, 0, 0)]
	consumer.commit(offsets = resetTP, asynchronous = False)

def consumer_cleanup():
	admin = AdminClient({'bootstrap.servers': 'localhost:9092'})
	admin.delete_consumer_groups(group_ids = ["water-treatment-group"]) # Remove consumer group if it already exists so we can join with the new consuemr (otherwise it gives an error)

#consumer_cleanup()
topic = 'water-treatment-preproc'

consumer_conf = {'bootstrap.servers': 'localhost:9092', 'group.id': 'water-treatment-group', 'auto.offset.reset': 'earliest', 'enable.auto.commit': 'false'}
c = Consumer(consumer_conf)
c.subscribe([topic], on_assign=assignment_callback) # Subscribe to topic
reset_offset(c, topic) # Reset offset back to start in case it moved so the consumer can read the entire topic

kswin = drift.KSWIN(alpha=0.000001, window_size = 100)
trainingData = []

msgCount = 0
try:
	while True:
		msg = c.poll(1.0)
		if msg is None:
			continue
		if msg.error():
			print(msg.error())
			break                

		msgCount += 1

		timestamp = msg.key().decode('utf-8')
		features = msg.value().decode('utf-8')
		features = json.loads(features)
		features = pd.DataFrame.from_dict([features]) 

		record = features.drop(columns = ["attack_label"]) # Pass the record to the drift detector without the attack label (since that would give it away, obviously)
		testVar = float(record["LIT 301"].item())

		if(msgCount < 8000):
			trainingData.append(testVar)
		elif(msgCount == 8000):
			kswin = drift.KSWIN(alpha=0.000001, window_size = 200, stat_size = 100, window = trainingData)
		else:
			kswin.update(testVar)
			if kswin.drift_detected:
				print(f"Change detected at time {timestamp}, value: {testVar}, label {features['attack_label'].item()}")

except KeyboardInterrupt:
	pass

finally:
	print("Closing consumer.")
	c.close()