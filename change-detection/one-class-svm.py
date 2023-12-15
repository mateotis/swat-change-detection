from river import anomaly
from confluent_kafka import Consumer
import json
from change_detection_utils import *

consumer_cleanup()
topic = 'water-treatment-preproc'

consumer_conf = {'bootstrap.servers': 'localhost:9092', 'group.id': 'water-treatment-group', 'auto.offset.reset': 'earliest', 'enable.auto.commit': 'false'}
c = Consumer(consumer_conf)
c.subscribe([topic], on_assign=assignment_callback) # Subscribe to topic
reset_offset(c, topic) # Reset offset back to start in case it moved so the consumer can read the entire topic

model = anomaly.QuantileFilter(
    anomaly.OneClassSVM(nu=0.1),
    q=0.995
)
algorithm = "one-class-svm"

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

		timestamp = msg.key().decode('utf-8')
		features = msg.value().decode('utf-8')
		features = json.loads(features)
		#print(features)
		#features = pd.DataFrame.from_dict([features]) 

		 # Pass the record to the drift detector without the attack label (since that would give it away, obviously) and the timestamp
		record = {k: features[k] for k in features.keys() - {'attack_label', 'timestamp'}}

		score = model.score_one(record)
		is_anomaly = model.classify(score)
		model.learn_one(record) # Update model

		if(is_anomaly):
			print(f"Drift detected at time {timestamp}, value: {features}")

			# Check if it's actually a change based on the attack label
			if(features["attack_label"] == "attack"): # If so, figure out which attack it detected and with what delay
				attackNum, delay = which_attack(features["timestamp"])
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