# CI/CD 구축
프로젝트를 진행하면서, 로컬에서 개발한 코드를 매번 EC2에 수동으로 'git pull'하는 것은 비효율적이다. 코드를 푸시하면 자동으로 서버에 배포되고, 파이프라인이 재가동되는 CI/CD를 구축하였다.

## CI/CD 전략
지금 프로젝트는 멀티 클라우드 환경이기에, Github Actions를 사용하여 두 개의 서로 다른 배포 파이프라인을 구축해야 한다.
1. Naver Cloud 배포 (deploy-naver.yml)
  - collectors/power/, requirements.txt, deploy-naver.yml이 변경되었을 때, 스크립트를 실행한다.
2. AWS EC2 배포 (deploy-aws.yml)
  - collectors/weather/spark/, dags/, docker-compose.yml, Dockerfile.airflow, requirements.txt, deploy-aws.yml 이 변경되었을 때, 스크립트를 실행한다.

## 1단계: Github Secrets 설정
GitHub 리포지토리 상단 메뉴 Settings -> 왼쪽 메뉴 Secrets and variables -> Actions 클릭한 뒤, 아래의 6가지 변수를 추가한다.
NAVER_HOST	            (네이버 클라우드 공인 IP)
NAVER_USERNAME	root	(네이버 클라우드 접속 계정)
NAVER_KEY		        (naver-key.pem 파일 내용 전체 복사/붙여넣기)
AWS_HOST		        (AWS EC2 탄력적 IP)
AWS_USERNAME	ubuntu	(AWS 접속 계정)
AWS_KEY                 (AWS 키 페어 파일(key.pem) 내용 전체)

## 2단계: Self-hosted Runner 사용
SSH 접속(appleboy/ssh-action)방식은 Github 서버가 내 서버에 SSH로 접속을 해서 명령을 내리는 방식이다.
Self-hosted Runner 방식은 내 서버에 Runner를 설치해둔 뒤, Github에 Listening을 하다가 변경사항이 생기면 내부에서 실행할 수 있는 방식이다. 22번 포트를 열 필요없는 보안적인 요소를 챙길 수 있다. 

### 네이버 클라우드에 Runner 설치
1. GitHub 리포지토리 -> Settings -> Actions -> Runners 로 이동.
2. [New self-hosted runner] 초록색 버튼 클릭.
3. Runner image: Linux 선택.
4. Download 및 Configure 명령어들을 네이버 클라우드 터미널에서 그대로 복사/붙여넣기 실행.
  (주의: Configure 단계에서 질문이 나오면 아래와 같이 입력)
  - Enter the name of the runner group: (그냥 엔터)
  - Enter the name of runner: naver-runner (원하는 이름)
  - Enter any additional labels: naver-cloud (중요: 이 라벨로 구분)
  - Enter the name of work folder: (그냥 엔터)
5. 설치가 끝나면 실행
```bash
# 서비스 설치 및 시작
sudo ./svc.sh install
sudo ./svc.sh start
```
### AWS EC2에 Runner 설치
똑같은 과정을 반복
1. New self-hosted runner 버튼 클릭 -> Linux.
2. 명령어 복사해서 AWS EC2 터미널에서 실행.
3. Configure 질문:
  Name: aws-runner
  Labels: aws-ec2 (중요: 네이버랑 구분해야 함)
4.서비스 실행:
```bash
sudo ./svc.sh install
sudo ./svc.sh start
```

## 3단계: Naver Cloud, AWS EC2 배포 워크플로우 작성
1. Naver Cloud
- 수정파일: .github/workflows/deploy-naver.yml
- 코드: 해당 파일 참고

2. AWS EC2
- 수정파일: .github/workflows/deploy-aws.yml
- 코드: 해당 파일 참고

### Runner는 actions-runner에서, 실제 코드는 원래 있던 폴더에서
기본적으로 GitHub Actions Runner는 자기 자신의 폴더(actions-runner/_work/...)안에서 코드를 받고 빌드하는 것이 정석이다.
하지만 내가 사용한 방식은 Runner를 단순히 배포 명령을 내리는 용도로만 사용하고, 실제 코드는 원래 있던 고정 폴더에서 관리하는 방식이다.
- 파일: .github/workflows/deploy-naver.yml
- 코드: 
```yml
run: |
  # 1. Runner가 사용하는 작업 폴더에서 프로젝트 폴더로 이동
  cd /root/power-weather-pipeline
  
  # 2. 최신 코드 받기 (git pull)
  # (주의: 이 폴더가 git init이 되어 있어야 함.)
  git pull origin main
```
정석 방식의 장점
  - 격리성: 매 배포마다 깨끗한 환경에서 시작할 수 있다. (설정에 따라 배포 후 폴더를 싹 비울 수 있다.)
  - 권한 문제 없음: Runner 자신이 만든 폴더에서 작업하므로 sudo나 파일 권한 문제가 거의 발생하지 않는다.
  - 일반적인 CI 용도: 단순히 빌드해서 결과물만 만들고 끝나는 경우 가장 적합하다.
정석 방식의 단점:
  - 경로 복잡: 나중에 로그를 확인하거나 수동으로 고치려고 할 때, 경로가 깊고 복잡해서 귀찮다.
  - 데이터 유실 위험: _work 폴더가 정리되거나 Runner가 재설치되면 그 안에 쌓이던 로그파일과 데이터들이 날아갈 수 있다.

채택한 방식의 장점:
  - 데이터 보존: nohup으로 실행된 로그(power.log)나 수집된 데이터가 안전하게 계속 쌓인다.
  - 빠른 배포: 이미 venv가 설치되어 있고 라이브러리도 다 깔려 있으므로, git pull만 하면 되어 배포가 매우 빠르다.
채택한 방식의 단점:
  - 권한 문제 발생 가능: Runner는 보통 root가 아닌 일반 유저 권한으로 돈다. 그런데 /root/ 폴더나 다른 유저 소유의 폴더를 건드리면 권한 에러가 발생할 수 있다.
  - 지저분해질 수 있음: 이전 배포 때 생긴 쓰레기 파일이 계속 남아있을 수 있다.

결론:
로그와 데이터가 중요하고, 서비스의 연속성(Docker 컨테이너를 띄우거나, venv를 유지하는 것)을 위해 기존의 외부 폴더를 사용한다.



## Trouble Shooting
### GitHub Actions Runner 권한 문제
- 문제 상황: configure 명령어를 실행하다가,  
```bash
./config.sh --url https://github.com/zxcv0807/power-weather-pipeline --token <토큰> 
```
을 실행하면 **Must not run with sudo** 에러가 발생한다.

- 원인: GitHub Actions Runner는 보안상의 이유로 기본적으로 root 계정(관리자 권한)으로 실행하는 것을 막아두었다.

- 해결: 명령어를 통해 root로 실행해도 되게 환경 변수를 설정한다.
```bash
# root 실행 허용 환경변수 설정
export RUNNER_ALLOW_RUNASROOT=1
# 재실행
./config.sh --url https://github.com/zxcv0807/power-weather-pipeline --token <토큰>
```

### .git 필요
- 문제 상황: fatal: not a git repository

- 원인: ci/cd 구축 이전에 네이버클라우드에서는 git clone을 하지 않고, power_producer의 파일의 내용만 복사해서 사용했었음.
여기서 생긴 의문은 어차피 네이버 클라우드에서는 power_producer만 잘 돌아가면서 데이터 수집하고 EC2로 보내주면 될텐데, 굳이 전체 코드를 git clone해야할까? 라는 생각이 들었음.

- 해결: 전체 파일 git clone이 정석이다. 네이버 클라우드에서 git clone을 한 번 해준다.
엔지니어링 관점에서 전체 git clone이 정석이다.
1. 버전 관리의 일치:
  - Github에 코드와 서버에 있는 코드가 100% 동일하다는 것을 보장할 수 있다. 수동으로 파일을 복사하고 붙여넣는 것은 실수로 구버전이 남거나, 오타가 들어갈 수 있다.
2. 배포 자동화의 용이성:
  - git pull 명령어 한 줄이면 업데이트가 끝난다. 만약 Git을 쓰지 않는다면, Github Actions에서 scp로 파일을 뒤집어 쓰거나, 파일 내용을 echo로 밀어넣는 등 복잡하고 불안한 방식을 사용해야 한다.
3. 확장성:
  - 만약 requirements.txt이 수정되거나, 설정파일이 추가된다면 Git은 폴더 구조를 맞춰주지만, 파일 관리 단위는 그때마다 사람이 개입해야 한다.
4. 용량 문제:
  - 고작 텍스트 파일(코드) 몇 개 더 있다고 해서 서버 용량에 영향을 주지 않는다.

