# Comparative analysis of data distribution-based change detection methods in SWaT
### Steps for the entire pipeline:
1. Run ```docker-compose up influxdb``` in the root folder to start the InfluxDB container. Open its GUI at ```localhost:8086``` and sign in with the credentials supplied in the .env file (user: _admin_, password: _admin1234_).
2. Head to the API Tokens page and generate an all-access API token. Copy this token and insert it into the .env and config/telegraf.conf files on the lines where it says _"insert\_token_here"_. Keep the token saved somewhere, as it will also be needed for Grafana.
3. Run ```docker-compose down```, then ```docker-compose up``` again to launch the entire SWaT change detection stack.
4. (Optional) Go to the Kafka cluster manager running on ```localhost:9000``` and add a cluster with the following settings:
    - Cluster Name: whatever you want
    - Cluster Zookeeper Hosts: zookeeper:2181
    - ☑ Enable JMX Polling
    - ☑ Poll customer information
    - ☑ Enable Active OffsetCache
    - You can leave the rest as default and save - from this dashboard you can monitor the data ingestion into Kafka in the following step
5. Go into the preprocessing folder and run ```kafka-ingest.py``` to send the data into Kafka in streaming format.
6. While the data is being sent (or afterwards), enter the running Spark container with ```docker exec -it swat-spark bash``` and execute the following PySpark script to preprocess the data, get running statistics, and feed it back into Kafka: ```./bin/spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 /swat-change-detection/preprocessing/spark-preproc.py```
    - Note that you must have a Java SDK installed in your environment for PySpark to work 
7. Telegraf will automatically capture the preprocessed data as a metric and feed it into InfluxDB. You can login to InfluxDB with the previous credentials and explore the data.
    - The timestamps of the stored data correspond to the timestamps of the original dataset, which were all recorded on 20 July 2019. Make sure to set this day as your time range to see the data.
8. Login to Grafana on ```localhost:3000``` with the default credentials (user: _admin_, password: _admin_). Add a new InfluxDB datasource with the following settings:
    - Query language: Flux
    - URL: ```http://influxdb:8086```
    - Auth: None
    - Organization: swat-change-detection
    - Token: (your InfluxDB API token)
    - Default Bucket: water-treatment
9. You should be able to save the datasource. Now you can query the data and create dashboards in Grafana. Make sure you remember to set the time range to 20 July 2019!
10. GO to  ```localhost:8888``` to access Chronograph. Login with same credentials as above you have used for Grafana. After adding URL and mentioned above, select 'InfluxDB v2 Auth' and then enter your influxDB token and Organization(same as Grafana) and the click 'add connection'. You will be able to create Dashboards after selecting InfluxDB from dropdown.

### Contributions:
**Máté:** docker-compose file, Kafka data ingestion as stream, Kafka and Spark connection, Spark data transformation, TIG stack setup and configuration, readme instructions
