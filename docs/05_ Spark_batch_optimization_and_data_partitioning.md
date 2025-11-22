# Spark 배치 처리 최적화 및 데이터 파티셔닝

초기 단계에서는 단순히 모든 데이터를 한 폴더에 저장하고, 배치 작업 시 전체 데이터를 읽고 처리하여 덮어쓰는 방식을 사용했다.
하지만 이 방식은 데이터가 쌓일수록 **비용 증가**와 **성능 저하**가 발생하므로, 이를 **파티셔닝(Partitioning)**과 **증분 처리(Incremental Processing)** 방식으로 고도화했다.

## 1. 문제점 분석 (Legacy)

### A. Raw 데이터의 비효율적인 저장
- 현황: `s3a://bucket/raw/power/`, `s3a://bucket/raw/weather/` 경로에 모든 시간대의 Parquet 파일이 섞여서 저장된다.
- 문제: 특정 날짜의 데이터만 분석하려 해도, Spark가 해당 폴더 내의 모든 파일을 스캔해야 한다.

### B. 비효율적인 배치 처리 (Full Scan)
- 현황: `spark.read.load(".../raw/power")` 로 전체 시간대의 파일을 읽은 뒤 Join을 수행한다.
- 문제: 만약 배치 처리를 하루에 한 번 한다면, 실질적으로 추가된 데이터는 어제 하루치 데이터이지만, 과거 전체 데이터를 매일 다시 읽고 있다.

### C. 결과 데이터의 덮어쓰기 (Overwrite)
- 현황: `mode("overwrite")` 사용한다.
- 문제: 매일 배치가 돌 때마다 과거의 기록이 사라지거나, 하나의 거대한 파일로 뭉뚱그려진다.

---

## 2. 해결 방안

### A. 데이터 수집 단계: 파티셔닝 (Partitioning)
데이터를 저장할 때부터 **연/월/일** 디렉토리 구조로 나누어 저장한다.

- 수정 파일: `streaming_to_lake.py`
- 코드:
```python
    # 1. 파생 컬럼 생성
    partitioned_df = parsed_df \
        .withColumn("year", year(...)) \
        .withColumn("month", month(...)) \
        .withColumn("day", dayofmonth(...))

    # 2. 파티션 저장
    query = partitioned_df.writeStream \
        .partitionBy("year", "month", "day") \
        .start()
```
- 결과 구조: raw/power/year=2025/month=11/day=20/part-xxx.parquet

### B. 배치 처리 단계: 증분 처리 (Partition Pruning)
전체 경로가 아닌 **분석 대상 날짜(어제)**의 폴더만 콕 찍어서 읽는다. 이를 Partition Pruning이라고 한다.

- 수정 파일: `spark_batch_job.py`
- 코드: 
```python
# 어제 날짜 계산
target_date = datetime.now() - timedelta(days=1)

# 특정 경로만 지정해서 Read (비용/속도 최적화)
power_path = f"s3a://{BUCKET}/raw/power/year={target_year}/month={...}/day={...}"
power_df = spark.read.format("parquet").load(power_path)
```

### C. 저장 단계: Append 모드 및 파티셔닝
분석된 날짜도 날짜별로 나누어 저장하며, 기존 데이터를 건드리지 않고 추가(Append)한다.

- 수정 파일: spark_batch_job.py
- 코드:
```python
analysis_df.write \
    .mode("append") \ # 덮어쓰기 방지
    .partitionBy("year", "month", "day") \ # 결과물도 검색하기 쉽게 파티셔닝
    .save(output_path)
```
