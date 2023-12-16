import json
import pandas as pd
import numpy as np
from confluent_kafka import Consumer, TopicPartition
import time
from datetime import datetime
from scipy.stats import cramervonmises

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

def cvm_detector(data):
    # Assuming `data` is a list or NumPy array
    result = cramervonmises(data, cdf='norm')
    p_value = result.pvalue

    return p_value

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
p_value_threshold = 0.05  # Adjust as needed
magnitude_threshold = 10  # Adjust as needed (reduced for higher sensitivity)
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
            # Apply the CvM test
            cvm_p_value = cvm_detector(np.array(history))

            # Calculate the absolute difference between the current value and the mean of historical values
            mean_value = np.mean(history)
            magnitude_change = np.abs(current_value - mean_value)

            print(f"\rCurrent CvM p-value: {cvm_p_value:.4f}, Magnitude of change: {magnitude_change:.2f}", end='', flush=True)

            # Check if a change point is detected
            if cvm_p_value < p_value_threshold and magnitude_change > magnitude_threshold:
                print(f"\nChange point detected at time {timestamp}, value: {current_value}, label {features['attack_label'].item()}, CvM p-value: {cvm_p_value:.4f}, Magnitude of change: {magnitude_change:.2f}")

                # Check if it's actually a change based on the attack label
                if features["attack_label"].item() == "attack":
                    detections += 1
                    detection_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    detection_delay = (time.time() - detection_time.timestamp()) * 1000  # Convert to milliseconds
                    detection_delays.append(detection_delay)
                    print(f"Detection delay: {detection_delay:.2f} milliseconds")
                else:
                    false_alarms += 1
                    print(f"False alarm detected at time {timestamp}, value: {current_value}, label {features['attack_label'].item()}, CvM p-value: {cvm_p_value:.4f}, Magnitude of change: {magnitude_change:.2f}")

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
