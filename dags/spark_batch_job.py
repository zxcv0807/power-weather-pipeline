import os
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, date_trunc, avg, max, lit, to_timestamp
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
        .master("local[1]") \
        .config("spark.jars.packages", f"{HADOOP_AWS_JAR},{AWS_SDK_JAR}") \
        .config("spark.driver.memory", "512m") \
        .config("spark.executor.memory", "512m") \
        .config("spark.sql.shuffle.partitions", "1") \
        .config("spark.hadoop.fs.s3a.access.key", AWS_ACCESS_KEY) \
        .config("spark.hadoop.fs.s3a.secret.key", AWS_SECRET_KEY) \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.endpoint", f"s3.{REGION}.amazonaws.com") \
        .getOrCreate()

def main():
    print("Starting Spark batch analysis job...")
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    # 처리할 날짜 계산
    target_date = datetime.now() - timedelta(days=1)
    target_year = target_date.year
    target_month = f"{target_date.month:02d}"
    target_day = f"{target_date.day:02d}"

    print(f"Processing data for: {target_year}-{target_month}-{target_day}")

    # 파티션 경로를 지정하여 '어제 데이터'만 읽기 (Partition Pruning)
    power_path = f"s3a://{BUCKET_NAME}/raw/power/year={target_year}/month={target_month}/day={target_day}"
    weather_path = f"s3a://{BUCKET_NAME}/raw/weather/year={target_year}/month={target_month}/day={target_day}"
    # 1. 원본 데이터(Raw Data) 읽기
    try:
        power_df = spark.read.format("parquet").load(power_path)
        weather_df = spark.read.format("parquet").load(weather_path)

        # 데이터 중복 제거
        power_df = power_df.dropDuplicates(["base_datetime"])
        weather_df = weather_df.dropDuplicates(["base_datetime"])
    except Exception as e:
        print(f"No data found for {target_date}. Skipping job.")
        spark.stop()
        return

    # 2. 데이터 전처리 (시간 기준으로 조인하기)
    power_hourly = power_df.withColumn(
        "hour_timestamp",
        date_trunc("hour", to_timestamp(col("base_datetime"), "yyyyMMddHHmmss"))
    )
    weather_hourly = weather_df.withColumn(
        "hour_timestamp",
        date_trunc("hour", to_timestamp(col("base_datetime"), "yyyyMMddHHmm"))
    )

    # 3. 조인(Join)
    joined_df = power_hourly.join(weather_hourly, "hour_timestamp", "left_outer")

    # 4. 분석 (시간대별 집계)
    analysis_df = joined_df.groupBy("hour_timestamp").agg(
        avg("temperature_c").alias("avg_temp_c"),
        max("current_demand_mw").alias("max_demand_mw"),
        avg("reserve_power_mw").alias("avg_reserve_mw"),
        max("rainfall_mm").alias("max_rainfall_mm")
    )

    # 5. 분석 결과(Warehouse)를 S3에 저장
    # 파티션을 나눠서 append 모드로 저장
    output_path = f"s3a://{BUCKET_NAME}/warehouse/hourly_summary"

    analysis_df = analysis_df \
        .withColumn("year", lit(target_year)) \
        .withColumn("month", lit(target_month)) \
        .withColumn("day", lit(target_day))

    analysis_df.write.mode("append").partitionBy("year", "month", "day").format("parquet").save(output_path)

    print(f"Batch analysis complete. Data saved to {output_path}")
    spark.stop()

if __name__ == "__main__":
    main()