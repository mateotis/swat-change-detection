# Utilities functions used by our change detection scripts
from confluent_kafka import TopicPartition
from confluent_kafka.admin import AdminClient
from datetime import datetime
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

def which_attack(timestamp): # Find which attack the algorithm detected and calculate detection delay 
	dateFormat = '%Y-%m-%d %H:%M:%S'
	detectionTime = datetime.strptime(timestamp, dateFormat)
	attackNum = 0
	delay = 0

	if(timestamp >= '2019-07-20 07:08:46') & (timestamp <= '2019-07-20 07:10:31'):
		attackNum = 1
		attackStart = datetime.strptime('2019-07-20 07:08:46', dateFormat)
		delay = detectionTime - attackStart
		delay = delay.total_seconds()
	elif(timestamp >= '2019-07-20 07:15:00') & (timestamp <= '2019-07-20 07:19:32'):
		attackNum = 2
		attackStart = datetime.strptime('2019-07-20 07:15:00', dateFormat)
		delay = detectionTime - attackStart
		delay = delay.total_seconds()
	elif(timestamp >= '2019-07-20 07:26:57') & (timestamp <= '2019-07-20 07:30:48'):
		attackNum = 3
		attackStart = datetime.strptime('2019-07-20 07:26:57', dateFormat)
		delay = detectionTime - attackStart
		delay = delay.total_seconds()
	elif(timestamp >= '2019-07-20 07:38:50') & (timestamp <= '2019-07-20 07:46:20'):
		attackNum = 4
		attackStart = datetime.strptime('2019-07-20 07:38:50', dateFormat)
		delay = detectionTime - attackStart
		delay = delay.total_seconds()
	elif(timestamp >= '2019-07-20 07:54:00') & (timestamp <= '2019-07-20 07:56:00'):
		attackNum = 5
		attackStart = datetime.strptime('2019-07-20 07:54:00', dateFormat)
		delay = detectionTime - attackStart
		delay = delay.total_seconds()
	elif(timestamp >= '2019-07-20 08:02:56') & (timestamp <= '2019-07-20 08:16:18'):
		attackNum = 6
		attackStart = datetime.strptime('2019-07-20 08:02:56', dateFormat)
		delay = detectionTime - attackStart
		delay = delay.total_seconds()

	return attackNum, delay

def save_results(algorithm, detections, falseAlarms, attacksDetected, delays):
	results = {}
	results["algorithm"] = algorithm
	results["detections"] = detections
	results["false-alarms"] = falseAlarms
	for i in range(6):
		results["attack" + str(i + 1) + "-detected"] = attacksDetected[i]
		results["attack" + str(i + 1) + "-delay"] = delays[i]

	with open('./change-detection/results.csv', 'a') as f: # Write results to file
		writer = csv.DictWriter(f, fieldnames=results.keys())
		#writer.writeheader()
		writer.writerows([results])