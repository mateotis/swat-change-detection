# Test consumer to receive SWaT data from the producer
from confluent_kafka import Consumer, KafkaException

def kafka_consumer_1():
	consumer_conf = {'bootstrap.servers': 'localhost:9092', 'group.id': 'water-treatment-group'}
	c = Consumer(consumer_conf)

	c.subscribe(['water-treatment'])

	try:
		while True:
			msg = c.poll(1.0)
			if msg is None:
				continue
			if msg.error():
				print(msg.error())
				break                

			value = msg.value().decode('utf-8')
			print(value)

	except KeyboardInterrupt:
		pass

	finally:
		c.close()

if __name__ == '__main__':
	kafka_consumer_1()