import os
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, FloatType, IntegerType

load_dotenv()

# --- 설정 ---
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
POWER_TOPIC = 'power_demand_realtime'
WEATHER_TOPIC = 'weather_realtime'

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
REGION = "ap-northeast-2"

# 1. Spark-S3 연동 드라이버 설정
HADOOP_AWS_JAR = "org.apache.hadoop:hadoop-aws:3.3.4"
AWS_SDK_JAR = "com.amazonaws:aws-java-sdk-bundle:1.12.262"

# 2. 데이터 스키마 정의
POWER_SCHEMA = StructType([
    StructField("base_datetime", StringType(), True),
    StructField("current_demand_mw", FloatType(), True),
    StructField("reserve_power_mw", FloatType(), True)
])

WEATHER_SCHEMA = StructType([
    StructField("base_datetime", StringType(), True),
    StructField("rainfall_type", IntegerType(), True),
    StructField("rainfall_mm", FloatType(), True),
    StructField("temperature_c", FloatType(), True)
])

def create_spark_session():
    """S3 접속 설정이 포함된 Spark Session을 생성"""

    return SparkSession.builder \
        .appName("KafkaToS3") \
        .config("spark.jars.packages", f"{HADOOP_AWS_JAR},{AWS_SDK_JAR},org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.7") \
        .config("spark.hadoop.fs.s3a.access.key", AWS_ACCESS_KEY) \
        .config("spark.hadoop.fs.s3a.secret.key", AWS_SECRET_KEY) \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.endpoint", f"s3.{REGION}.amazonaws.com") \
        .getOrCreate()

def start_stream(spark, topic_name, schema, output_path):
    """지정된 토픽에서 데이터를 읽어 S3로 저장하는 스트림을 시작합니다."""

    # 1. Kafka 토픽에서 데이터 스트림 읽기
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", topic_name) \
        .option("startingOffsets", "earliest") \
        .load()

    # 2. Kafka 메시지 파싱
    parsed_df = df.selectExpr("CAST(value AS STRING) as json_string") \
        .select(from_json(col("json_string"), schema).alias("data")) \
        .select("data.*")

    # 3. 데이터를 Parquet 형식으로 S3에 쓰기
    query = parsed_df.writeStream \
        .format("parquet") \
        .outputMode("append") \
        .option("path", f"s3a://{BUCKET_NAME}/{output_path}") \
        .option("checkpointLocation", f"s3a://{BUCKET_NAME}/checkpoints/{output_path}") \
        .start()

    print(f"Streaming data from '{topic_name}' to 's3a://{BUCKET_NAME}/{output_path}'")
    return query

def main():
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    # 전력 데이터 스트림 시작
    power_query = start_stream(spark, POWER_TOPIC, POWER_SCHEMA, "raw/power")

    # 날씨 데이터 스트림 시작
    weather_query = start_stream(spark, WEATHER_TOPIC, WEATHER_SCHEMA, "raw/weather")

    try:
        # 두 쿼리가 모두 종료될 때까지 대기
        spark.streams.awaitAnyTermination()
    except KeyboardInterrupt:
        print("Stopping streams...")
        power_query.stop()
        weather_query.stop()

if __name__ == "__main__":
    main()