# AWS 클라우드로 마이그레이션

지금까지 로컬에서 docker-compose로 돌리던 모든 시스템을 실제 클라우드(AWS)환경으로 옮겨서, 24시간 꺼지지 않고 돌아가는 '운영(Production)' 환경을 만든다.
기업에서는 AWS MSK (Kafka), AWS MWAA (Airflow), AWS EMR (Spark) 같은 '관리형 서비스'를 주로 사용하지만,
비용 문제로 인해 아래와 같이 마이그레이션 한다.
- Storage (저장소): MiniO => AWS S3
- Compute (서버): 로컬(내 컴퓨터) => AWS EC2
- middleware: Kafka/Airflow는 EC2 안에서 Docker로 유지 (비용 절감)


## load_dotenv() 선언

dags/spark_batch_job.py 에서는 load_dotenv()를 선언할 필요가 없다.

- streaming_to_lake.py (Local 실행)
  - 이 스크립트는 로컬 윈도우 터미널에서 실행된다.
  - 로컬 터미널은 .env 파일의 내용을 자동으로 알지 못한다.
  - 그래서 load_dotenv()를 통해 .env 파일의 내용을 환경 변수로 불러와야 했다.

- spark_batch_job.py (Docker/Airflow 실행)
  - 이 스크립트는 Airflow 컨테이너 내부에서 실행된다.
  - 우리는 docker-compose.yml 파일에서 다음과 같이 설정했다.
  ```yml
  airflow-scheduler:
  environment:
    - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
    # ...
  ```
  - 이 설정 덕분에, Docker가 컨테이너를 실행할 때, .env 파일의 값을 읽어서 이미 컨테이너의 환경 변수로 주입해두었다.
  - 따라서, .env 파일을 다시 읽을 필요가 없다.


## Trouble Shooting

### 에러: Java gateway process exited before sending its port number
- JAVA_HOME is not set 이 보이지 않는 것을 보면 자바는 정상적으로 설치되었다.
- JAVA_HOME 환경변수가 설정되지 않았다.

=> Dockerfile.airflow에 JAVA_HOME 환경변수를 명시적으로 설정한다.

```yml
USER root
RUN apt-get update \
    && apt-get install -y openjdk-17-jre-headless \
    && apt-get clean

# 추가
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
```
- ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64: Debian 12에서 openjdk-17-jre-headless 를 설치하면 보통 이 경로에 설치된다.

### psycopg2.OperationalError: could not translate host name "postgres" ...

Airflow 스케줄러가 자신의 데이터베이스인 postgres 컨테이너를 찾지 못했다.
ERROR - Heartbeat time limit exceeded!

Spark 작업이 너무 무거워서 Airflow 컨테이너가 뻗어버렸다.(Resource Exhaustion)
현재 Spark가 local[*] 모드로 사용 가능한 모든 CPU 코어와 메모리를 쓰게 되면서, 같은 컨테이너에 있던 Airflow 스케줄러가 자원이 없어, 데이터베이스와의 네트워크 처리조차 못한 것이다.

=> Spark가 사용할 메모리 양을 강제로 제한해야 한다.

dags/spark_batch_job.py 에서 create_spark_session 함수를 수정
```python
def create_spark_session():
    """MinIO(S3) 접속 설정이 포함된 Spark Session을 생성합니다."""
    return SparkSession.builder \
        .appName("DailyBatchAnalysis") \
        .master("local[*]") \
        .config("spark.jars.packages", f"{HADOOP_AWS_JAR},{AWS_SDK_JAR}") \
        # [추가] 드라이버 메모리를 512MB로 제한
        .config("spark.driver.memory", "512m") \
        # [추가] 실행기 메모리도 제한
        .config("spark.executor.memory", "512m") \
        .config("spark.hadoop.fs.s3a.access.key", AWS_ACCESS_KEY) \
        .config("spark.hadoop.fs.s3a.secret.key", AWS_SECRET_KEY) \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.endpoint", f"s3.{REGION}.amazonaws.com") \
        .getOrCreate()
```

### 공공데이터 포털에서 제공하는 시간의 데이터 형태가 다르다.
- 전력 데이터: "base_datetime": "20251122222500"
- 날씨 데이터: "base_datetime": "202511221200"
전력 데이터는 **yyyyMMddHHmmss**의 형태로 제공하지만, 날씨는 **yyyyMMddHHmm**의 형태로 제공한다.

=> 특정 topic에 제한되지 않게 substring을 사용하였다.
- 수정 파일: streaming_to_lake.py
- 코드:
```python
partitioned_df = parsed_df \
        .withColumn("year", substring(col("base_datetime"), 1, 4)) \
        .withColumn("month", substring(col("base_datetime"), 5, 2)) \
        .withColumn("day", substring(col("base_datetime"), 7, 2))
```