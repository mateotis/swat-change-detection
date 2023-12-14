from river import anomaly
from confluent_kafka import Consumer, TopicPartition
from confluent_kafka.admin import AdminClient
import json
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

model = anomaly.QuantileFilter(
    anomaly.OneClassSVM(nu=0.3),
    q=0.999
)

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

		timestamp = msg.key().decode('utf-8')
		features = msg.value().decode('utf-8')
		features = json.loads(features)
		#print(features)
		#features = pd.DataFrame.from_dict([features]) 

		 # Pass the record to the drift detector without the attack label (since that would give it away, obviously)
		record = {k: features[k] for k in features.keys() - {'attack_label', 'timestamp'}}

		score = model.score_one(record)
		is_anomaly = model.classify(score)
		model.learn_one(record)

		if(is_anomaly):
			print(f"Change detected at time {timestamp}, value: {features}")

			if(features["attack_label"] == "attack"):
				attackNum = which_attack(features["timestamp"])
				if(attacksDetected[attackNum - 1] == 0):
					attacksDetected[attackNum - 1] = 1
				detections += 1
			else:
				falseAlarms += 1
				
		print("\r", end = '')
		print(msgCount, "records analysed.", end = '', flush = True)

except KeyboardInterrupt:
	pass

finally:
	print("Closing consumer.")
	print(f"Detection statistics:\nActual detections: {detections}\nList: {attacksDetected}\nFalse alarms: {falseAlarms}")
	# Fill out results dictionary
	results["algorithm"] = "one-class-svm"
	results["detections"] = detections
	results["false-alarms"] = falseAlarms
	for i in range(6):
		results["attack" + str(i + 1) + "-detected"] = attacksDetected[i]

	with open('./change-detection/results.csv', 'a') as f: # Write results to file
		writer = csv.DictWriter(f, fieldnames=results.keys())
		#writer.writeheader()
		writer.writerows([results])
	c.close()