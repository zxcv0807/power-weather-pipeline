# Hybrid Multi-Cloud Real-time Power & Weather Data Pipeline

## 📖 Project Overview
이 프로젝트는 대한민국 **실시간 전력 수급 현황**과 **기상 정보**를 수집하여 상관관계를 분석하는 데이터 엔지니어링 파이프라인입니다.

**핵심 챌린지 및 해결책:**
전력거래소(KPX) API가 보안상의 이유로 AWS Cloud IP 대역을 차단하는 문제가 발생했습니다. 이를 해결하기 위해 **Naver Cloud(국산 클라우드)**를 데이터 수집 전진 기지로 활용하고, **AWS EC2**를 메인 처리 허브로 사용하는 **하이브리드 멀티 클라우드 아키텍처**를 설계 및 구축했습니다.

---

## 🏗 Architecture

```mermaid
graph LR
    %% 1. Naver Cloud 영역
    subgraph "Naver Cloud (Micro)"
        A[Power Producer]
    end

    %% 2. AWS EC2 영역 
    subgraph "AWS EC2 (Main Server)"
        B[Kafka Broker]
        C[Weather Producer]
        D[Spark Streaming]
        E[Airflow Scheduler]
        F[Spark Batch Job]
    end

    %% 3. AWS S3 영역
    subgraph "AWS S3 (Data Lake)"
        G[Raw Zone]
        H[Warehouse Zone]
    end

    %% 4. 데이터 흐름 연결
    A -->|Public Internet / 9092| B
    C -->|Localhost / 9092| B
    B --> D
    D -->|Save Raw Data| G
    E -->|Trigger| F
    G -->|Load Data| F
    F -->|Save Analysis| H
````

1.  **Collection**:
      * **Power Data**: Naver Cloud에서 수집하여 AWS Kafka로 전송 (IP 차단 우회).
      * **Weather Data**: AWS EC2에서 직접 수집.
2.  **Ingestion**: AWS EC2 상의 \*\*Kafka (KRaft Mode)\*\*가 데이터 버퍼링 및 중계.
3.  **Stream Processing**: **Spark Streaming**이 실시간 데이터를 읽어 AWS S3(`raw/`)에 Parquet 포맷으로 적재.
4.  **Batch Processing**: **Airflow**가 매일 **Spark Batch** 작업을 트리거하여 S3 데이터를 조인/집계 후 Data Warehouse(`warehouse/`)에 저장.

-----

## 🛠 Tech Stack

  * **Language**: Python 3.11, Java 17 (OpenJDK)
  * **Message Queue**: Apache Kafka 7.6.1 (Confluent, KRaft Mode)
  * **Data Processing**: Apache Spark 3.5.7 (PySpark)
  * **Orchestration**: Apache Airflow 2.8.1 (Docker)
  * **Storage**: AWS S3 (Production)
  * **Infra**: AWS EC2 (t3.medium), Naver Cloud (Micro Server), Docker Compose

-----

## 📂 Project Structure

```bash
power-weather-pipeline/
├── dags/                    # [AWS EC2/Airflow] 배치 분석 및 DAG
│   ├── batch_analysis_dag.py
│   └── spark_batch_job.py
│
├── docs/                    # 프로젝트 학습 노트 및 트러블 슈팅 로그
│
├── power_producer.py        # [Naver Cloud] 전력 데이터 수집기
├── weather_producer.py      # [AWS EC2] 날씨 데이터 수집기
├── streaming_to_lake.py     # [AWS EC2] Spark 스트리밍 작업
├── docker-compose.yml       # 전체 인프라 구성 (Kafka, Airflow)
└── Dockerfile.airflow       # Airflow 커스텀 이미지 (Java 17 포함)
```

-----

## 🚀 실행 방법법 (Production)

### 1\. 전제조건

  * **AWS EC2 Instance** (Ubuntu 22.04, t3.medium 추천)
  * **Naver Cloud Micro Server** (Ubuntu 20.04)
  * **AWS S3 Bucket** & IAM User

### 2\. AWS EC2 설정 및 실행 (Main Server)

1.  Clone Repository & Setup Environment:
    ```bash
    git clone [https://github.com/zxcv0807/power-weather-pipeline.git](https://github.com/zxcv0807/power-weather-pipeline.git)
    cd power-weather-pipeline
    # .env파일 생성 후 AWS Key들 설정
    ```
2.  컨테이너 실행 (Kafka, Airflow):
    ```bash
    docker compose up --build -d
    ```
3.  Weather Producer & Spark Streaming 실행:
    ```bash
    # Setup Python venv & Install requirements
    nohup python -u collectors/weather/weather_producer.py > weather.log 2>&1 &
    nohup python -u spark/streaming_to_lake.py > stream.log 2>&1 &
    ```

### 3\. Naver Cloud 설정 및 실행 (Power Collector)

*상세 가이드: [Naver Cloud 설정 및 실행](docs/04_naver_cloud.md)*

1.  Naver Cloud Server 연결.
2.  Power Producer 실행:
    ```bash
    # power_producer.py에서 Kafka Address to AWS EC2 Public IP 로 수정
    nohup python -u collectors/power/power_producer.py > power.log 2>&1 &
    ```

-----

## 🔥 Troubleshooting Log

프로젝트 진행 중 발생한 주요 이슈와 해결 과정입니다. 상세 내용은 `docs/` 폴더 내의 문서를 참고하세요.

### 1\. 공공기관 API의 클라우드 IP 차단

  * **Problem**: 로컬에서는 잘 작동하던 전력 데이터 수집기가 AWS EC2 배포 후 `Connection Timeout` 발생.
  * **Analysis**: `curl` 및 `traceroute` 테스트 결과, 전력거래소 방화벽이 AWS IP 대역을 차단하고 있음을 확인 (Hop 10에서 패킷 Drop).
  * **Solution**: **멀티 클라우드 전략 도입**. 차단되지 않는 \*\*Naver Cloud (국산 클라우드)\*\*의 Micro 서버를 수집 전용 노드로 구축하여 데이터를 수집하고, AWS Kafka로 전송하는 하이브리드 아키텍처로 해결.
  * **Link**: [네트워크 진단 과정](docs/04_network_diagnostics.md), [Naver Cloud 도입기](docs/04_naver_cloud.md)

### 2\. Spark & Airflow 자원 경합

  * **Problem**: Airflow에서 Spark 작업 실행 시 `Heartbeat time limit exceeded` 에러와 함께 컨테이너가 강제 종료됨.
  * **Analysis**: Spark가 `local[*]` 모드로 실행되면서 컨테이너의 모든 메모리를 점유, Airflow 스케줄러가 기아 상태(Starvation)에 빠짐.
  * **Solution**: Spark Session 설정에 `spark.driver.memory=512m` 제한을 추가하여 컨테이너 내 리소스 공존 환경 구성.
  * **Link**: [Spark 배치 파이프라인 및 OOM 해결](docs/04_AWS_S3_migration.md)
