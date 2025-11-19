import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, date_trunc, avg, max
from pyspark.sql.types import TimestampType

# S3 설정
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
REGION = "ap-northeast-2"

# S3 연동 드라이버
HADOOP_AWS_JAR = "org.apache.hadoop:hadoop-aws:3.3.4"
AWS_SDK_JAR = "com.amazonaws:aws-java-sdk-bundle:1.12.262"

def create_spark_session():
    """S3 접속 설정이 포함된 Spark Session을 생성합니다."""
    
    return SparkSession.builder \
        .appName("DailyBatchAnalysis") \
        .master("local[*]") \
        .config("spark.jars.packages", f"{HADOOP_AWS_JAR},{AWS_SDK_JAR}") \
        .config("spark.hadoop.fs.s3a.access.key", AWS_ACCESS_KEY) \
        .config("spark.hadoop.fs.s3a.secret.key", AWS_SECRET_KEY) \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.endpoint", f"s3.{REGION}.amazonaws.com") \
        .getOrCreate()

def main():
    print("Starting Spark batch analysis job...")
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    # 1. 원본 데이터(Raw Data) 읽기
    power_df = spark.read.format("parquet").load(f"s3a://{BUCKET_NAME}/raw/power")
    weather_df = spark.read.format("parquet").load(f"s3a://{BUCKET_NAME}/raw/weather")

    # 2. 데이터 전처리 (시간 기준으로 조인하기)
    # base_datetime (예: '202511142200')을 시간 단위로 통일
    power_hourly = power_df.withColumn(
        "hour_timestamp",
        date_trunc("hour", col("base_datetime").cast(TimestampType()))
    )
    
    weather_hourly = weather_df.withColumn(
        "hour_timestamp",
        date_trunc("hour", col("base_datetime").cast(TimestampType()))
    )

    # 3. 조인(Join)
    joined_df = power_hourly.join(weather_hourly, "hour_timestamp", "inner")

    # 4. 분석 (시간대별 집계)
    # 시간대별 평균 기온, 최대 전력 수요, 평균 예비 전력 등
    analysis_df = joined_df.groupBy("hour_timestamp").agg(
        avg("temperature_c").alias("avg_temp_c"),
        max("current_demand_mw").alias("max_demand_mw"),
        avg("reserve_power_mw").alias("avg_reserve_mw"),
        max("rainfall_mm").alias("max_rainfall_mm")
    )

    # 5. 분석 결과(Warehouse)를 S3에 저장
    # Parquet으로 저장하며, 덮어쓰기(overwrite) 모드 사용
    output_path = f"s3a://{BUCKET_NAME}/warehouse/hourly_summary"
    analysis_df.write.mode("overwrite").format("parquet").save(output_path)

    print(f"Batch analysis complete. Data saved to {output_path}")
    spark.stop()

if __name__ == "__main__":
    main()