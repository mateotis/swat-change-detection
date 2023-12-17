import json
import pandas as pd
from confluent_kafka import Consumer
from change_detection_utils import *

def cusum_detector(data, threshold):
    mean = sum(data) / len(data)
    cusum = 0
    for value in data:
        cusum = max(0, cusum + value - mean - threshold)
    return cusum

consumer_cleanup()
topic = 'water-treatment-preproc'

consumer_conf = {'bootstrap.servers': 'localhost:9092', 'group.id': 'water-treatment-group', 'auto.offset.reset': 'earliest', 'enable.auto.commit': 'false'}
c = Consumer(consumer_conf)
c.subscribe([topic], on_assign=assignment_callback) # Subscribe to topic
reset_offset(c, topic) # Reset offset back to start in case it moved so the consumer can read the entire topic

# Initialize variables for drift detection and performance metrics
msgCount = 0
history_size = 10
history = []
threshold_multiplier = 5  # Adjust this multiplier for sensitivity
cusum_threshold = 1.0  # Adjust this threshold for CUSUM sensitivity

algorithm = "cusum"
detections = 0 # Actual detections (one per attack)
false_alarms = 0 # False alarms (with attack_label == "normal")
attacksDetected = [0, 0, 0, 0, 0, 0] # There are six attacks; if the algorithm detects one, set the corresponding element to 1
detection_delays = [0, 0, 0, 0, 0, 0]
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

        current_value = float(features["LIT 301"].item())

        history.append(current_value)
        history = history[-history_size:]

        if len(history) >= history_size:
            # Apply the CUSUM algorithm
            cusum_value = cusum_detector(history, cusum_threshold)

            # Check if a change point is detected
            if cusum_value > threshold_multiplier:
                print(f"Change point detected at time {timestamp}, value: {current_value}, label {features['attack_label'].item()}, CUSUM value: {cusum_value}")

                # Check if it's actually a change based on the attack label
                if(features["attack_label"].item() == "attack"): # If so, figure out which attack it detected and with what delay
                    attackNum, delay = which_attack(features["timestamp"].item())
                    if(attacksDetected[attackNum - 1] == 0): # And store the results
                        attacksDetected[attackNum - 1] = 1
                    if(detection_delays[attackNum - 1] == 0):
                        detection_delays[attackNum - 1] = delay
                    detections += 1
                else:
                    false_alarms += 1

            print(f"\r{msgCount} records analysed. Total Detections: {detections}, False Alarms: {false_alarms}", end='', flush=True)

except KeyboardInterrupt:
    pass

finally:
	print("Closing consumer.")
	print(f"Detection statistics:\nActual detections: {detections}\nDetected attacks: {attacksDetected}\nDetection delays: {detection_delays}\nFalse alarms: {false_alarms}")
	# Fill out results dictionary
	save_results(algorithm, detections, false_alarms, attacksDetected, detection_delays) # Save results in a csv
	c.close()
