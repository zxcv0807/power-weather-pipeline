import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, FloatType

# --- 설정 ---
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_TOPIC = 'power_demand_realtime'

# Kafka에서 받은 JSON 데이터의 스키마 정의
# (Producer가 보낸 데이터 구조와 일치해야 합니다)
SCHEMA = StructType([
    StructField("base_datetime", StringType(), True),
    StructField("current_demand_mw", FloatType(), True),
    StructField("reserve_power_mw", FloatType(), True)
])

def main():
    print("Starting Spark Streaming Consumer...")

    # Spark Session 생성 (Kafka 연동 설정 포함)
    spark = SparkSession.builder \
        .appName("PowerStreamingMonitor") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.7") \
        .getOrCreate()
    
    # 스트리밍 로그 레벨 설정 (필요 없는 로그 줄이기)
    spark.sparkContext.setLogLevel("WARN")

    # 1. Kafka 토픽에서 데이터 스트림 읽기
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", KAFKA_TOPIC) \
        .load()

    # 2. Kafka 메시지(Value)를 JSON에서 스키마에 맞게 파싱
    # Kafka의 value는 바이너리(binary)이므로 먼저 문자열(string)로 변환
    parsed_df = df.selectExpr("CAST(value AS STRING) as json_string") \
        .select(from_json(col("json_string"), SCHEMA).alias("data")) \
        .select("data.*")   # data 구조체 컬럼 안에 묶여있던 모든 하위 필드를 밖으로 꺼내, 개별 컬럼으로 펼친다.

    # 3. 실시간 알림(Alert) 로직 추가 
    # 예: 예비력이 5500MW 미만인지 확인
    alert_df = parsed_df.filter(col("reserve_power_mw") < 5500)

    # 4. 결과를 콘솔에 출력 (테스트용)
    # (실제로는 이 데이터를 다른 Kafka 토픽이나 DB로 보냅니다)
    query = alert_df.writeStream \
        .outputMode("append") \
        .format("console") \
        .start()

    print(f"Streaming data from Kafka topic: {KAFKA_TOPIC}")
    print("Waiting for alerts (reserve_power_mw < 5500)...")

    try:
        query.awaitTermination()
    except KeyboardInterrupt:
        print("Stopping Spark Streaming...")
        query.stop()

if __name__ == "__main__":
    main()