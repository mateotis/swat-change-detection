from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import *

# We know the structure of the data coming in from Kafka
schema = StructType([
    StructField("FIT 401", DoubleType()),
    StructField("LIT 301", DoubleType()),
    StructField("P601 Status", IntegerType()),
    StructField("MV201", IntegerType()),
    StructField("P101 Status", IntegerType()),
    StructField("MV 501", IntegerType()),
    StructField("P301 Status", IntegerType()),
])

spark = SparkSession.builder \
    .appName("SWaT data preprocessing") \
    .master("local") \
	.getOrCreate()

# Consume the data from Kafka
df = spark \
  .readStream \
  .format("kafka") \
  .option("kafka.bootstrap.servers", "kafka:29092") \
  .option("subscribe", "water-treatment") \
  .option("startingOffsets", "earliest") \
  .load() # startingOffsets must be set to earliest so we can get all the data from the Kafka broker

df = df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)")
df = df.withColumn("data", from_json(df.value, schema)) # Deserialise the actual data from the json string and add it as a new column
df = df.select(col("key").alias("timestamp"), "data.*") # Get the timestamp (the key) and the features in their separate columns in one dataframe

df.printSchema()

# TODO more preprocessing steps

# Once all the preproc is done, feed the new data back into Kafka in the same key-value format but under a different topic
topic = "water-treatment-preproc"
# We're basically reversing the steps we did when we consumed the data: renaming timestamp back to be the key and turning the features back into a json string to serve as the value
procDf = df.select(col("timestamp").alias("key"), to_json(struct(df.columns[1:])).alias("value"))
procDf.printSchema()

ds = procDf \
  .selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)") \
  .writeStream \
  .format("kafka") \
  .option("kafka.bootstrap.servers", "kafka:29092") \
  .option("topic", topic) \
  .option("checkpointLocation", "proc-swat-checkpoints") \
  .start()
ds.awaitTermination()

#ds = df.writeStream.format("console").start() # Print stream to console as it arrives

