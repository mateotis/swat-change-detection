# Comparative analysis of data distribution-based change detection methods in SWaT
### Steps:
1. Run ```docker-compose up``` in the root folder
2. Go into the preprocessing folder and run ```kafka-ingest.py``` to turn the data into streaming format
3. Enter the running Spark container with ```docker exec -it swat-spark bash``` and execute the following PySpark script to preprocess the data: ```./bin/spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 /swat-change-detection/preprocessing/spark-preproc.py```
    - Note that you must have a Java SDK installed in your environment for Spark to work 