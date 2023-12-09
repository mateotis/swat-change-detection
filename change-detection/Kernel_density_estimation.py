from sklearn.neighbors import KernelDensity
from sklearn.preprocessing import StandardScaler
from scipy.stats import wasserstein_distance
import numpy as np
import json
import pandas as pd
from confluent_kafka import Consumer, KafkaException, TopicPartition
from confluent_kafka.admin import AdminClient


def assignment_callback(consumer, partitions):
    for p in partitions:
        print(f'Assigned to {p.topic}, partition {p.partition}')

def reset_offset(consumer, topic):
    resetTP = [TopicPartition(topic, 0, 0)]
    consumer.assign(resetTP)  # Assign the partitions to the consumer
    consumer.seek(resetTP[0])  # Seek to the beginning of the assigned partition

def consumer_cleanup():
    admin = AdminClient({'bootstrap.servers': 'localhost:9092'})
    admin.delete_consumer_groups(group_ids=["water-treatment-group"])

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

# Initialize variables for drift detection
reference_distribution = None
msgCount = 0
history_size = 10  
history = []

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

        current_distribution = np.asarray(features.drop(columns=["attack_label"]).iloc[0])

        if reference_distribution is not None:
            # Fit Kernel Density Estimation to both distributions
            kde_reference = KernelDensity(bandwidth=0.2, kernel='gaussian').fit(reference_distribution.reshape(-1, 1))
            kde_current = KernelDensity(bandwidth=0.2, kernel='gaussian').fit(current_distribution.reshape(-1, 1))

            # Calculate the log-density of each point in the current distribution
            log_density_current = kde_current.score_samples(current_distribution.reshape(-1, 1))

            # Calculate the log-density of each point in the reference distribution
            log_density_reference = kde_reference.score_samples(current_distribution.reshape(-1, 1))

            # Calculate the Relative Density Ratio
            rdr = np.mean(np.exp(log_density_current - log_density_reference))

            # Add the current RDR to the history
            history.append(rdr)

            history = history[-history_size:]

            # set a threshold for drift detection based on the history of RDR values
            drift_threshold = 1.5  # needs ti be adjusted, selected this for now

            if np.max(history) > drift_threshold:
                print(f"Drift detected at", msgCount, timestamp, "entry is\n", features)

        reference_distribution = current_distribution

        print("\r", end='')
        print(msgCount, "records analysed.", end='', flush=True)

except KeyboardInterrupt:
    pass

finally:
    print("Closing consumer.")
    c.close()
