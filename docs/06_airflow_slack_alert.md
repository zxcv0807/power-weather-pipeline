# Airflow에서 에러 발생 시 Slack으로 알림 보내기

## 1단계: Slack Incoming Webhook URL 발급
Slack에서 "메시지를 받은 URL"을 만들어야 한다.

1. Slack 워크 스페이스 준비
  - 새로운 개인 워크 스페이스 생성
2. 채널 생성
  - 알림을 받을 채널(예: #airflow-alerts) 생성
3. App 생성
  - Slack API 페이지(https://api.slack.com/apps)접속 -> Create New App -> From scratch 선택
  - App Name: Airflow Alert
  - WorkSpace: 방금 만든 워크스페이스 선택
4. Webhook 활성화:
  - 왼쪽 메뉴 Features -> Incoming Webhooks 클릭
  - Activate Incoming Webhooks 스위치를 On으로 변환
5. Webhook URL 생성:
  - Add New Webhook to Workspace 선택
  - 아까 만든 채널 선택 -> Allow 선택
6.  https://hooks.slack.com/services/... 로 시작하는 URL 복사

## 2단계: 라이브러리 설치
Airflow에서 Slack과 통신하기 위한 라이브러리(apache-airflow-providers-slack)를 설치해야 한다.

1. requirements.txt 에 추가
```Plaintext
apache-airflow-providers-slack>=8.0.0
```
2. 이미지 재빌드 및 실행
라이브러리를 추가했기에 Airflow이미지를 다시 구워줘야 한다.
```bash
docker compose down
docker compose up --build -d
```

## 3단계: Airflow Connection 설정
Slack URL은 민감한 정보이므로 코드에 직접 적지 않고, **Airflow의 Connection**에 저장해서 불러오는 것이 정석이다.
1. Airflow 웹 UI 접속
2. 상단 메뉴 Admin -> Connections 클릭
3. [+](파란색 더하기) 클릭
4. 다음과 같이 입력
  - Connection Id: slack_conn
  - Connection Type: HTTP
  - Host: https://hooks.slack.com/services/... (아까 복사해둔 URL) => Trouble Shooting 확인
5. Save

## 4단계: 알림 함수 작성(dags/utils/slack_alert.py)
DAG 파일이 지저분해지지 않도록, 알림 로직은 별도로 관리한다. dags폴더 안에 utils폴더를 만들고, 그 안에 파일을 생성한다.
Airflow에서는 **on_failure_callback**이라는 기능을 통해, Task가 실패하면 Slack 전송 로직을 실행할 수 있게 하였다.
- 파일: dags/utils/slack_alert.py

## 5단계: DAG에 적용
- 수정 파일: dags/batch_analysis_dag.py
- 코드: 
```python
# ... (기존 import)
# (Airflow는 dags 폴더를 PYTHONPATH에 추가하므로 바로 import 가능)
from utils.slack_alert import on_failure_callback 

# DAG 기본 설정
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 11, 24),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    # [추가] Task 실패 시 이 함수를 실행
    'on_failure_callback': on_failure_callback, 
}
# ... (이하 DAG 정의 코드는 그대로) ...
```

### **From a manifest** vs **From scratch**
Slack API 페이지에서 Create New APP을 누르게 되면  **From a manifest**와 **From scratch** 중에서 선택할 수 있다.

From a manifest
설정 파일(JSON 또는 YAML) 코드를 붙여넣어 한 번에 설정하는 방식이다.
- 방식: 미리 정의된 텍스트 파일(manifest)을 복사+붙여넣기 하면 권한, 이벤트 구독, 앱 이름 등이 순식간에 적용된다.
- 장점: 
  - 복제와 배포가 쉽다.(코드를 복사하면 똑같은 앱이 순식간에 복제됨)
  - 버전 관리(git)가 가능하다. 앱 설정을 코드처럼 저장해둘 수 있다.
  - IaC(Infrastructure as Code) 개념과 비슷하다. 설정을 코드로 관리하는 방식이다.

From scratch
웹사이트의 UI를 통해 마우스로 하나씩 클릭하며 설정하는 방식이다.
- 방식: 앱 이름을 짓고 생성한 뒤, 왼쪽 메뉴들에서 설정 요소들을 하나씩 찾아다니며 설정한다.
- 장점: 직관적이다. 설정 메뉴를 눈으로 보면서 설정할 수 있다.


## Trouble Shooting

### 파라미터 이름
- 문제 상황: 
  airflow.exceptions.AirflowException: missing keyword argument 'slack_webhook_conn_id'
- 원인: 
  Airflow의 Slack Provider 라이브러리가 업데이트 되면서 파라미터 이름이 바뀌었다.
  - 구버전: http_conn_id
  - 신버전: slack_webhook_conn_id
- 해결:
  - 수정 파일: dags/utils/slack_alert.py
  - 코드:
  ```python
  operator = SlackWebhookOperator(
        task_id='slack_alert',
        # http_conn_id => slack_webhook_conn_id
        slack_webhook_conn_id='slack_conn',
        message=message,
    )
  ```

### Airflow의 보안 아키텍처 및 HttpHook의 작동 원리
- 문제 상황: 
  airflow.exceptions.AirflowNotFoundException: Connection ID 'slack_conn' does not contain password (Slack Webhook Token).
- 원인:
  - Slack Api페이지에서 Webhook URL 전체를 Airflow의 Connections의 Host에 붙여 넣게되면 발생하는 에러이다.
  - Airflow의 보안 아키텍처 및 HttpHook의 작동 원리 때문이다.

1. 보안 관점: 암호화 저장
- Host 필드: 메타데이터 DB에 평문으로 저장된다.
- Password 필드: Airflow가 DB에 저장할 때, Fernet Key를 사용하여 암호화해서 저장한다.
- Slack Webhook URL의 뒷 부분(https://hooks.slack.com/services/... 에서 ...)은 그 자체로 인증이 가능한 **비밀 토큰**이다. 그래서 Host필드에 넣으면 권한이 그대로 노출되기 때문에 보안상 'Password' 필드에 넣어야 한다.

2. 작동 원리: HttpHook의 결합 방식
SlackWebhookOperator는 내부적으로 HttpHook을 상속받거나 사용한다. Http Hook이 URL을 조립하는 방식은 다음과 같다.
Full URL = Host(Base URL) + Endpoint (Token)
- Host: https://hooks.slack.com/services/
- Password(또는 Endpoint): 뒷부분의 비밀 토큰
Airflow는 이 둘을 합쳐서 요청을 보낸다. 그래서 Host에는 앞부분을, Password에는 뒷부분(토큰)을 넣는 것이 권장된다.

- 해결:
  - Connection 구성을 분리한다.
  - Host: https://hooks.slack.com/services/
  - Password: Host의 뒷부분
  