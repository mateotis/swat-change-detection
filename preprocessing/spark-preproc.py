import pyspark
import time
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .master("local") \
	.getOrCreate()

df = spark \
  .readStream \
  .format("kafka") \
  .option("kafka.bootstrap.servers", "localhost:9092") \
  .option("subscribe", "water-treatment") \
  .option("startingOffsets", "earliest") \
  .load() # startingOffsets must be set to earliest so we can get all the data from the Kafka broker

df = df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)")

query = df.writeStream.format("console").start() # Print stream to console as it arrives
query.awaitTermination() # Don't continue until the data is printed


#print(df.first())
#print(df.describe())