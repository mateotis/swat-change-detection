import json
import pandas as pd
from confluent_kafka import Consumer, TopicPartition
import time
from datetime import datetime

def assignment_callback(consumer, partitions):
    for p in partitions:
        print(f'Assigned to {p.topic}, partition {p.partition}')

def reset_offset(consumer, topic):
    resetTP = [TopicPartition(topic, 0, 0)]
    consumer.assign(resetTP)
    consumer.seek(resetTP[0])

def close_consumer(consumer):
    print("\nClosing consumer.")
    consumer.close()

def cusum_detector(data, threshold):
    mean = sum(data) / len(data)
    cusum = 0
    for value in data:
        cusum = max(0, cusum + value - mean - threshold)
    return cusum

# consumer_cleanup()
topic = 'water-treatment-preproc'

consumer_conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'water-treatment-group',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': 'false'
}
c = Consumer(consumer_conf)
c.subscribe([topic], on_assign=assignment_callback)
reset_offset(c, topic)

# Initialize variables for drift detection and performance metrics
msgCount = 0
history_size = 10
history = []
threshold_multiplier = 1.0  # Adjust this multiplier for sensitivity
cusum_threshold = 1.0  # Adjust this threshold for CUSUM sensitivity
detections = 0
false_alarms = 0
detection_delays = []

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

        current_value = float(features["LIT 301"].item())

        history.append(current_value)
        history = history[-history_size:]

        if len(history) >= history_size:
            # Apply the CUSUM algorithm
            cusum_value = cusum_detector(history, cusum_threshold)

            print(f"\rCurrent CUSUM value: {cusum_value}", end='', flush=True)

            # Check if a change point is detected
            if cusum_value > threshold_multiplier:
                print(f"\nChange point detected at time {timestamp}, value: {current_value}, label {features['attack_label'].item()}, CUSUM value: {cusum_value}")

                # Check if it's actually a change based on the attack label
                if features["attack_label"].item() == "attack":
                    detections += 1
                    detection_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    detection_delay = (time.time() - detection_time.timestamp()) * 1000  # Convert to milliseconds
                    print(f"Detection delay: {detection_delay:.2f} milliseconds")
                else:
                    false_alarms += 1
                    print(f"False alarm detected at time {timestamp}, value: {current_value}, label {features['attack_label'].item()}, CUSUM value: {cusum_value}")

            print(f"\r{msgCount} records analysed. Total Detections: {detections}, False Alarms: {false_alarms}", end='', flush=True)

except KeyboardInterrupt:
    pass

finally:
    close_consumer(c)

# Print performance metrics
print(f"\nPerformance Metrics:")
print(f"Total Detections: {detections}")
print(f"False Alarms: {false_alarms}")
if detections > 0:
    avg_delay = sum(detection_delays) / detections
    print(f"Average Detection Delay: {avg_delay:.2f} milliseconds")
else:
    print("No detections to calculate average delay.")
