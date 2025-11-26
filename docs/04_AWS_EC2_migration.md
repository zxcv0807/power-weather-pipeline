# AWS 클라우드로 마이그레이션

AWS EC2 배포를 통해 24시간 운영 환경을 구축한다.

## EC2

### 인스턴스 유형 c7i-flex.large

t3.micro, t3.small 은 RAM의 크기가 너무 작아, c7i-flex.large(4GB) 를 선택했다.
만약 비용이 너무 많이 든다면, t3.small에서 스왑메모리를 시도할 계획이다.
스토리지도 기본 8GB로 부족할 수 있기에, 20GB 정도로 늘렸다.

## 환경 설정
```bash
# 1. 패키지 업데이트
sudo apt-get update

# 2. Docker 필수 패키지 설치
# ca-certificates: 보안 웹사이트(HTTPS)의 인증서를 신뢰하기 위한 도구.
# curl: 인터넷에서 파일을 다운로드하는 도구.
# gnupg: 암호화 키(GPG)를 다루는 보안 도구.
# lsb-release: 지금 사용 중인 리눅스의 버전 이름을 확인하는 도구.
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# 3. Docker 공식 GPG 키 추가
# 의미: Docker 공식 사이트에서 '정품 인증 Key'를 받아와서 /etc/apt/keyrings 에 저장
# 이유: 앞으로 다운로드할 Docker 프로그램이 해커가 변조한 것이 아니라, Docker 공식 팀이 만든 정품임을 검증하기 위해 이 키가 필요
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 4. Docker 저장소 추가
# arch=$(dpkg --print-architecture): 내 컴퓨터 CPU가 인텔인지, AMD인지 자동으로 확인
# signed-by=...: 아까 받은 정품 인증 key로만 검증된 파일을 받는다.
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. Docker Engine 설치
# docker-ce: Docker 엔진 본체 (Community Edition)
# docker-ce-cli: docker 명령어 도구
# containerd.io: 컨테이너를 실제로 실행하는 런타임
# docker-compose-plugin: docker-compose 대신, 최신 docker compose 명령어를 쓰게 해주는 플러그인
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 6. sudo 없이 docker 명령어 쓰기 (설정 후 재접속 필요)
# 현재 접속한 사용자($USER, 보통 ubuntu)를 'docker'라는 관리자 그룹에 추가
sudo usermod -aG docker $USER
```

## 프로젝트 실행
```bash
# 1. 프로젝트 복제
git clone https://github.com/본인계정/power-weather-pipeline.git
# 2. 폴더 이동
cd power-weather-pipeline
# 3. .env 파일 생성(로컬에 있는 .env 파일 내용을 그대로 복사)
nano .env
# 4. Docker Compose 실행
docker compose up --build -d
```

## python 스크립트 백그라운드로 실행

- 파이썬 스크립트를 실행하기 위해 필요한 프로그램을 설치해야 한다.
```bash
# 1. Java (JDK 17) 설치 (Spark 실행용)
sudo apt-get install -y openjdk-17-jre-headless

# 2. Python 가상환경 모듈 설치
sudo apt-get install -y python3-venv

# 3. 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 4. 필수 라이브러리 설치
pip install pyspark==3.5.7 kafka-python requests python-dotenv boto3
```

- 터미널을 꺼도 프로그램이 죽지 않도록 nohup (No Hang Up) 명령어를 사용해 실행한다.
```bash
# 1. 전력 데이터 수집기 실행 (로그는 power.log에 저장)
nohup python -u power_producer.py > power.log 2>&1 &

# 2. 날씨 데이터 수집기 실행 (로그는 weather.log에 저장)
nohup python -u weather_producer.py > weather.log 2>&1 &

# Spark 스트리밍 실행 (로그는 stream.log에 저장)
nohup python -u streaming_to_lake.py > stream.log 2>&1 &
```


## Trouble Shooting

### PermissionError: [Errno 13] Permission denied: '/opt/airflow/logs/scheduler'

- Docker는 docker-compose가 실행될 때, 로컬에 dags, logs, plugins 폴더가 없다면 자동으로 생성한다. 이 때, **root 권한**으로 생성해버린다.
- Airflow의 규칙: 반면, 컨테이너 내부의 Airflow는 보안상 root가 아닌 **airflow(UID 50000)**라는 일반 유저로 실행된다.
- 충돌: airflow 유저가 root 소유의 logs 폴더에 로그 파일을 쓰려고 하니, 리눅스가 권한 문제로 막아버린다.

=> EC2 서버의 터미널에서 폴더들의 권한을 airflow 유저로 바꿔준다.
```bash
# chown -R: 폴더와 그 안의 모든 파일의 주인을 바꾼다.
sudo chown -R 50000:0 dags logs plugins
```

### Python의 출력 버퍼링

```bash
nohup python -u weather_producer.py > weather.log 2>&1 &
tail -f weather.log
```
Python은 기본적으로 출력을 바로 파일에 쓰지 않고, 어느 정도 모았다가 한 번에 쓴다.(버퍼링) 그래서 프로그램은 잘 돌아가고 있어도, 로그 파일에는 아직 아무것도 안 찍힌 것처럼 보일 수 있다.

=> python -u 옵션을 사용해 버퍼링을 끄면 해결할 수 있다.


### 전력 거래소의 AWS IP 대역 차단
***04_network_diagnostics.md*** 참고


## 그 외 명령어들
```bash
# 백그라운드에서 실행 중인 파이썬 프로세스 확인
ps -ef | grep python 

# 실시간 로그 확인
tail -f power.log

# 기존 프로세스 종료
pkill -f power_producer.py
```
