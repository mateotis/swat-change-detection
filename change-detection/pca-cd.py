# Test consumer to receive SWaT data from the producer
from confluent_kafka import Consumer, TopicPartition
from confluent_kafka.admin import AdminClient
import json
import pandas as pd
import numpy as np
from menelaus.data_drift import PCACD
import csv

def assignment_callback(consumer, partitions):
    for p in partitions:
        print(f'Assigned to {p.topic}, partition {p.partition}')

def reset_offset(consumer, topic): # Reset the offset for a topic back to the start
	resetTP = [TopicPartition(topic, 0, 0)]
	consumer.commit(offsets = resetTP, asynchronous = False)

def consumer_cleanup():
	admin = AdminClient({'bootstrap.servers': 'localhost:9092'})
	admin.delete_consumer_groups(group_ids = ["water-treatment-group"]) # Remove consumer group if it already exists so we can join with the new consuemr (otherwise it gives an error)

def which_attack(timestamp):
	attackNum = 0
	if(timestamp >= '2019-07-20 07:08:46') & (timestamp <= '2019-07-20 07:10:31'): attackNum = 1
	elif(timestamp >= '2019-07-20 07:15:00') & (timestamp <= '2019-07-20 07:19:32'): attackNum = 2
	elif(timestamp >= '2019-07-20 07:26:57') & (timestamp <= '2019-07-20 07:30:48'): attackNum = 3
	elif(timestamp >= '2019-07-20 07:38:50') & (timestamp <= '2019-07-20 07:46:20'): attackNum = 4
	elif(timestamp >= '2019-07-20 07:54:00') & (timestamp <= '2019-07-20 07:56:00'): attackNum = 5
	elif(timestamp >= '2019-07-20 08:02:56') & (timestamp <= '2019-07-20 08:16:18'): attackNum = 6

	return attackNum


consumer_cleanup()
topic = 'water-treatment-preproc'

consumer_conf = {'bootstrap.servers': 'localhost:9092', 'group.id': 'water-treatment-group', 'auto.offset.reset': 'earliest', 'enable.auto.commit': 'false'}
c = Consumer(consumer_conf)
c.subscribe([topic], on_assign=assignment_callback) # Subscribe to topic
reset_offset(c, topic) # Reset offset back to start in case it moved so the consumer can read the entire topic

np.random.seed(1) # The kdq-tree implementation uses bootstrapping, so setting the seed ensures consistent reproduction of results
pca_cd = PCACD(window_size=50, divergence_metric="kl", delta = 0.1)

results = {} # Track results in a dict

detections = 0 # Actual detections (one per attack)
falseAlarms = 0 # False alarms (with attack_label == "normal")
attacksDetected = [0, 0, 0, 0, 0, 0] # There are six attacks; if the algorithm detects one, set the corresponding element to 1
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

			if(features["attack_label"].item() == "attack"):
				attackNum = which_attack(features["timestamp"].item())
				if(attacksDetected[attackNum - 1] == 0):
					attacksDetected[attackNum - 1] = 1
				detections += 1
			else:
				falseAlarms += 1

		print("\r", end = '')
		print(msgCount, "records analysed.", end = '', flush = True)

		#print("Timestamp:", timestamp, type(timestamp))
		#print("Features:", features, type(features))

		#c.close()
		#exit()


except KeyboardInterrupt:
	pass

finally:
	print("Closing consumer.")
	print(f"Detection statistics:\nActual detections: {detections}\nList: {attacksDetected}\nFalse alarms: {falseAlarms}")
	# Fill out results dictionary
	results["algorithm"] = "pca-cd"
	results["detections"] = detections
	results["false-alarms"] = falseAlarms
	for i in range(6):
		results["attack" + str(i + 1) + "-detected"] = attacksDetected[i]

	with open('./change-detection/results.csv', 'a') as f: # Write results to file
		writer = csv.DictWriter(f, fieldnames=results.keys())
		#writer.writeheader()
		writer.writerows([results])
	c.close()