import pyspark
import time
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, approx_percentile, count, mean

spark = SparkSession.builder \
    .master("local") \
    .getOrCreate()

# Read data from Kafka
df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:29092") \
    .option("subscribe", "water-treatment") \
    .option("startingOffsets", "earliest") \
    .load()

# Deserialize key and value assuming they are in JSON format
df = df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)")

# extract features from JSON
def extract_attack_features(value):
    # I used features from swat_attack file to make it effifient for our change detection algos 
    features = [
        value.get('FIT 401', 0.0),
        value.get('LIT 301', 0.0),
        value.get('P 601', 0),
        value.get('MV 201', 0),
        value.get('P 101', 0),
        value.get('MV 501', 0),
        value.get('P 301', 0),
    ]
    return features

# feature extraction
df = df.select(extract_attack_features(col("value")).alias("features"))

# Perform initial preprocessing steps
for feature in df.columns:
    # Casting numeric columns to DoubleType
    if feature.startswith("FIT") or feature.startswith("LIT") or feature.startswith("P") or feature.startswith("MV"):
        df = df.withColumn(feature, col(feature).cast("double"))
    # replace missing values with the mean(we can replace with 0 as well but I thought mean is better)
    mean_value = df.select(mean(col(feature))).first()[0]
    df = df.withColumn(feature, when(col(feature).isNull(), mean_value).otherwise(col(feature)))

# Experiment with different sample sizes because we all are going to use diff algos so can be chaged later to improve performace of algo
sample_sizes = [0.05, 0.1, 0.2]  # Adjust the sample sizes as needed

for sample_fraction in sample_sizes:
    # Perform real-time descriptive stats with sampling
    sampled_df = df.sample(fraction=sample_fraction, seed=42)
    descriptive_stats = sampled_df.select(
        *[count(feature).alias(f'{feature}_count') for feature in df.columns],
        *[mean(feature).alias(f'{feature}_mean') for feature in df.columns],
        *[approx_percentile(feature, [0.25, 0.5, 0.75], 0.0).alias(f'{feature}_percentiles') for feature in df.columns]
    )

    # Print the descriptive statistics and sample size
    print(f"Sample Size: {sample_fraction * 100}%")
    query = descriptive_stats.writeStream.format("console").outputMode("update").start()
    query.awaitTermination()
