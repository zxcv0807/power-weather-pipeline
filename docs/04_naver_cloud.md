# 전력 거래소의 AWS 대역 차단으로 인한 Naver 클라우드 사용

기존의 AWS는 그대로 사용하되, 전력 거래소 api를 이용하는 것만 naver 클라우드를 사용해서, 멀티 클라우드 전략을 통해 이 프로젝트를 진행한다.

## 실행 가이드
1. 서버 생성
- 이미지는 ubuntu-24.04 를 선택
- VPC(Virtual Private Cloud) 생성
  - IP 주소 범위: 10.0.0.0/16 (기본값)
- Subnet 생성
  - IP 주소 범위: 10.0.1.0/24
  - Internet Gateway는 반드시 **public (공인)**을 선택
  - 용도: 일반
- 서버 스펙
  - Micro
- 요금제 : 
  - 월 요금제 (Micro는 무료 기간 내라면 차감되지 않는다.)
- 서버 개수: 1
- **공인 IP 설정**
  - 새로운 공인 IP 할당 선택 (월 4032원이라고 뜨지만 접속을 위해 필수적인 요소이다. )
- 물리 배치 그룹
  - 서버를 여러 대 만들 때, 물리적으로 서로 다른 기계에 배치해서 하나가 고장나도 나머지는 살리는 기능이다.
  - 우리는 서버 1개만 운영하기에 필요없다.
- 반납 보호
  - 실수로 서버를 삭제하는 것을 막아주는 기능이다.
- Script 
  - 서버가 켜질 때 자동으로 실행할 명령어를 넣는 곳이다.

## 터미널 접속 & 환경 설정

1. 터미널 접속
```bash
ssh -i "naver-key.pem" root@네이버_공인_IP
```
이 때, 비밀번호를 입력하라고 나오는데, 네이버 클라우드 콘솔에서
- 서버 선택
- 서버 관리 및 설정 변경
- 관리자 비밀번호 확인
에서 naver-key.pem을 통해 확인할 수 있다.

2. 환경 설정
```bash
# 1. 패키지 업데이트 및 Python 설치
apt-get update
apt-get install -y python3-pip python3-venv

# 2. 프로젝트 폴더 생성 및 가상환경 설정
mkdir power-collector
cd power-collector
python3 -m venv venv
source venv/bin/activate

# 3. 라이브러리 설치
pip install kafka-python requests python-dotenv
```

3. AWS 인바운드 규칙 추가
보안 그룹에서 아래의 규칙을 추가해서 네이버 클라우드에서 보낸 데이터를 AWS EC2가 받을 수 있게 해준다.
유형: 사용자 지정 TCP (Custom TCP)
포트 범위: 9092
소스 (Source): 0.0.0.0/0 (IPv4 Anywhere)


## power_producer.py 실행

nano power_producer.py 를 열고 로컬에 있던 코드를 붙여넣는다.
.env 파일도 만들어서 API 키를 넣어줘야 한다.

```python
# power_producer.py 내부 수정(Kafka의 주소는 AWS EC2 IP이어야 한다.)
KAFKA_BOOTSTRAP_SERVERS = ['AWS_EC2_퍼블릭_IP:9092'] # <-- AWS IP 입력
```

```bash
nohup python -u power_producer.py > power.log 2>&1 &
```