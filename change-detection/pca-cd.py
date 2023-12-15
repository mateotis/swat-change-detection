# Test consumer to receive SWaT data from the producer
from confluent_kafka import Consumer
import json
import pandas as pd
import numpy as np
from menelaus.data_drift import PCACD
from change_detection_utils import *

consumer_cleanup()
topic = 'water-treatment-preproc'

consumer_conf = {'bootstrap.servers': 'localhost:9092', 'group.id': 'water-treatment-group', 'auto.offset.reset': 'earliest', 'enable.auto.commit': 'false'}
c = Consumer(consumer_conf)
c.subscribe([topic], on_assign=assignment_callback) # Subscribe to topic
reset_offset(c, topic) # Reset offset back to start in case it moved so the consumer can read the entire topic

np.random.seed(1) # The kdq-tree implementation uses bootstrapping, so setting the seed ensures consistent reproduction of results
pca_cd = PCACD(window_size=50, divergence_metric="kl", delta = 0.1)
algorithm = "pca-cd"

detections = 0 # Actual detections (one per attack)
falseAlarms = 0 # False alarms (with attack_label == "normal")
attacksDetected = [0, 0, 0, 0, 0, 0] # There are six attacks; if the algorithm detects one, set the corresponding element to 1
delays = [0, 0, 0, 0, 0, 0]
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

			# Check if it's actually a change based on the attack label
			if(features["attack_label"].item() == "attack"): # If so, figure out which attack it detected and with what delay
				attackNum, delay = which_attack(features["timestamp"].item())
				if(attacksDetected[attackNum - 1] == 0): # And store the results
					attacksDetected[attackNum - 1] = 1
				if(delays[attackNum - 1] == 0):
					delays[attackNum - 1] = delay
				detections += 1
			else:
				falseAlarms += 1

		print("\r", end = '')
		print(msgCount, "records analysed.", end = '', flush = True)


except KeyboardInterrupt:
	pass

finally:
	print("Closing consumer.")
	print(f"Detection statistics:\nActual detections: {detections}\nDetected attacks: {attacksDetected}\nDetection delays: {delays}\nFalse alarms: {falseAlarms}")
	# Fill out results dictionary
	save_results(algorithm, detections, falseAlarms, attacksDetected, delays) # Save results in a csv
	c.close()