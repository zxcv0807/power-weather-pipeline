from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator

def on_failure_callback(context):
    """Task 실패 시 실행될 콜백 함수"""

    # 1. 실패한 Task 정보 가져오기
    dag_id = context.get('task_instance').dag_id
    task_id = context.get('task_instance').task_id
    execution_date = context.get('execution_date')
    exception = context.get('exception')

    # 2. 보낼 메시지 내용 구성
    message = f"""
    :red_circle: **Task Failed** :red_circle:
    *DAG*: {dag_id}
    *Task*: {task_id}
    *Date*: {execution_date}
    *Error*: {exception}
    """

    # 3. Slack으로 전송
    # http_conn_id는 Airflow의 Connection에서 저장한 Connection Id와 같아야 한다.
    operator = SlackWebhookOperator(
        task_id='slack_alert',
        slack_webhook_conn_id='slack_conn',
        message=message,
    )

    return operator.execute(context=context)