import json
import pandas as pd
import numpy as np
from confluent_kafka import Consumer
from scipy.stats import cramervonmises
from change_detection_utils import *

def cvm_detector(data):
    # Assuming `data` is a list or NumPy array
    result = cramervonmises(data, cdf='norm')
    p_value = result.pvalue

    return p_value

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
p_value_threshold = 0.05  # Adjust as needed
magnitude_threshold = 10  # Adjust as needed (reduced for higher sensitivity)

algorithm = "cvm"
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
