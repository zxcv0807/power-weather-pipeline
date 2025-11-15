중요: MINIO_ENDPOINT가 http://minio:9000입니다. Airflow 컨테이너가 localhost가 아닌 Docker 내부 네트워크의 minio 컨테이너와 통신해야 하므로 **minio**라는 서비스 이름을 사용합니다.

# Batch 분석 파이프라인

## Docker 내부 통신
### localhost

- 내 PC(Host OS): localhost는 **내 컴퓨터 자신**을 가리킨다. (예: http://localhost:9000로 MinIO 접속)
- 컨테이너 내부: Airflow 컨테이너 내부에서 localhost는 **Airflow 컨테이너 자신**을 가리킨다.

따라서 Airflow 컨테이너에서 http://localhost:9000 으로 접속을 시도하게 되면, Airflow는 MiniO를 찾는 게 아니라 자기 자신의 9000번 포트를 찾는다. 당연히 MiniO가 없기 떄문에 연결에 실패한다.

### Docker의 해결책: 서비스 이름름

Docker는 '내부 가상 네트워크' 안에서 컨테이너들이 서로를 쉽게 찾을 수 있도록 **자동 이름표(내부 DNS)**를 제공한다.
이 이름표가 docker-compose.yml 파일에서 정의한 **서비스 이름(Service Name)**이다.
```yml
services:
  airflow-webserver:
    # ...
  minio:  # <--- 1. 이 '서비스 이름'이
    image: minio/minio
    ports:
      - "9000:9000" # (이건 외부 노출용)
    # ...
```
여기서 Airflow 컨테이너가 http://minio:9000 으로 요청을 보내면, Docker 네트워크는 "아, minio는 저기 MiniO 컨테이너를 말하는구나"라고 알아듣고 자동으로 트래픽을 올바른 컨테이너로 연결해준다.


## Trouble Shooting

### openjdk-17-jre-headless
에러 메시지: Package 'openjdk-11-jre-headless' has no installation candidate

- apache/airflow:2.8.1 이미지는 Debian 12 (Bookworm)라는 최신 리눅스 배포판을 기반으로 한다.
- 이 Debian 12의 apt-get 패키지 저장소에는 openjdk-11-jre-headless라는 이름의 패키지가 더 이상 존재하지 않는다.
- 대신 Debian 12는 Java 17을 기본으로 사용한다.

=> openjdk-11-jre-headless 에서 openjdk-17-jre-headless 로 수정하면 해결할 수 있다.
