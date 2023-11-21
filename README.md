# Comparative analysis of data distribution-based change detection methods in SWaT
### Steps:
1. Run ```docker-compose up``` in the root folder
2. Go to the Kafka cluster manager running on ```localhost:9000``` and add a cluster with the following settings:
    - Cluster Name: whatever you want
    - Cluster Zookeeper Hosts: zookeeper:2181
    - ☑ Enable JMX Polling
    - ☑ Poll customer information
    - ☑ Enable Active OffsetCache
    - You can leave the rest as default and save - from this dashboard you can monitor the data ingestion into Kafka in the following step
3. Go into the preprocessing folder and run ```kafka-ingest.py``` to turn the data into streaming format
4. Enter the running Spark container with ```docker exec -it swat-spark bash``` and execute the following PySpark script to preprocess the data: ```./bin/spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 /swat-change-detection/preprocessing/spark-preproc.py```
    - Note that you must have a Java SDK installed in your environment for Spark to work 