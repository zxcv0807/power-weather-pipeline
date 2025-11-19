# AWS 클라우드로 마이그레이션

지금까지 로컬에서 docker-compose로 돌리던 모든 시스템을 실제 클라우드(AWS)환경으로 옮겨서, 24시간 꺼지지 않고 돌아가는 '운영(Production)' 환경을 만든다.
기업에서는 AWS MSK (Kafka), AWS MWAA (Airflow), AWS EMR (Spark) 같은 '관리형 서비스'를 주로 사용하지만,
비용 문제로 인해 아래와 같이 마이그레이션 한다.
- Storage (저장소): MiniO => AWS S3
- Compute (서버): 로컬(내 컴퓨터) => AWS EC2
- middleware: Kafka/Airflow는 EC2 안에서 Docker로 유지 (비용 절감)


## Trouble Shooting

에러: Java gateway process exited before sending its port number
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