from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import *

def attackLabeling(df): # Add a new column labeling whether the system is under attack at any timestamp (attack times given in the dataset specification)
	df = df.withColumn(
		"attack_label",
		when((df['timestamp'] >= '2019-07-20 07:08:46') & (df['timestamp'] <= '2019-07-20 07:10:31'), "attack")
		.when((df['timestamp'] >= '2019-07-20 07:15:00') & (df['timestamp'] <= '2019-07-20 07:19:32'), "attack")
		.when((df['timestamp'] >= '2019-07-20 07:26:57') & (df['timestamp'] <= '2019-07-20 07:30:48'), "attack")
		.when((df['timestamp'] >= '2019-07-20 07:38:50') & (df['timestamp'] <= '2019-07-20 07:46:20'), "attack")
		.when((df['timestamp'] >= '2019-07-20 07:54:00') & (df['timestamp'] <= '2019-07-20 07:56:00'), "attack")
		.when((df['timestamp'] >= '2019-07-20 08:02:56') & (df['timestamp'] <= '2019-07-20 08:16:18'), "attack")
		.otherwise("normal"))

	return df

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

spark.sparkContext.setLogLevel("WARN") # Reduce Spark's logging verbosity so we can actually see our own output

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

df = df.withColumn("timestamp", to_timestamp(date_format(col("timestamp"), "yyyy-MM-dd HH:mm:ss"))) # Convert timestamp into actual readable timestamp format and cut off the milliseconds

df = attackLabeling(df) # Add attack/normal labeling

df.printSchema()

# Define a list of numerical column names
numerical_columns = ["FIT 401", "LIT 301", "P601 Status", "MV201", "P101 Status", "MV 501", "P301 Status"]

# Add streaming aggregations for count, mean, min, max, stddev, and rate of each numerical column
agg_expr = []
for column in numerical_columns:
    agg_expr.extend([
        count(col(column)).alias("{}_count".format(column)),
        mean(col(column)).alias("{}_mean".format(column)),
        min(col(column)).alias("{}_min".format(column)),
        max(col(column)).alias("{}_max".format(column)),
        stddev(col(column)).alias("{}_stddev".format(column)),
        (count(col(column)) / 10 * 60).alias("{}_rate".format(column)),
        avg(col(column)).alias("{}_avg_10min".format(column)),
    ])

window_size = "10 minutes"
slide_interval = "5 minutes"

agg_query = df \
    .withWatermark("timestamp", window_size) \
    .groupBy(window("timestamp", window_size, slide_interval), "attack_label") \
    .agg(*agg_expr)

agg_query.writeStream \
    .outputMode("complete") \
    .format("console") \
    .start()


# Once all the preproc is done, feed the new data back into Kafka in the same key-value format but under a different topic
topic = "water-treatment-preproc"
procColumns = [col("timestamp").cast("String").alias("timestamp")] # Convert the timestamp back to string format as the JSON conversion will automatically change its readable format (which we don't want)
for column in df.columns[1:]: # The rest of the (numerical) columns are untouched
    procColumns.append(col(column))

# We're basically reversing the steps we did when we consumed the data: renaming timestamp back to be the key and turning the features back into a json string to serve as the value
procDf = df.select(col("timestamp").alias("key"), to_json(struct(procColumns)).alias("value"))
'''Note that the timestamp is included in the value json too.
We do this so we can specify in the Telegraf config that it should use that column as the timestamp when putting the data into InfluxDB. 
'''
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

'''ds1 = df.writeStream.format("console").option("truncate", False).start()
ds2 = procDf.writeStream.format("console").option("truncate", False).start() # Print stream to console as it arrives
ds2.awaitTermination()'''

