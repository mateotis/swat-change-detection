# Test consumer to receive SWaT data from the producer
from confluent_kafka import Consumer, KafkaException, TopicPartition
from confluent_kafka.admin import AdminClient
import json
import pandas as pd
import numpy as np
from menelaus.data_drift import KdqTreeStreaming, PCACD

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

np.random.seed(1) # The kdq-tree implementation uses bootstrapping, so setting the seed ensures consistent reproduction of results
pca_cd = PCACD(window_size=50, divergence_metric="kl", delta = 0.1)

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

		#if(msgCount < 8000):
		#	continue

		timestamp = msg.key().decode('utf-8')
		features = msg.value().decode('utf-8')
		features = json.loads(features)
		features = pd.DataFrame.from_dict([features]) 

		record = features.drop(columns = ["attack_label", "timestamp"]) # Pass the record to the drift detector without the attack label (since that would give it away, obviously)
		pca_cd.update(record)
		if(pca_cd.drift_state == "warning"):
			print(f"Warning detected at", msgCount, timestamp, "entry is\n", features)
		elif(pca_cd.drift_state == "drift"):
			print(f"Drift detected at", msgCount, timestamp, "entry is\n", features)

		#print("\r", end = '')
		#print(msgCount, "records analysed.", end = '', flush = True)

		#print("Timestamp:", timestamp, type(timestamp))
		#print("Features:", features, type(features))

		#c.close()
		#exit()


except KeyboardInterrupt:
	pass

finally:
	print("Closing consumer.")
	c.close()