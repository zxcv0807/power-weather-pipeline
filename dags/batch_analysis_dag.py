from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
from utils.slack_alert import on_failure_callback

# DAG 기본 설정
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 11, 15),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'on_failure_callback': on_failure_callback,
}

# DAG 정의
with DAG(
    dag_id='daily_power_weather_analysis',
    default_args=default_args,
    description='A daily batch job to analyze power and weather data.',
    schedule_interval='@daily',
    catchup=False, # 과거의 미실행 작업을 한꺼번에 실행하지 않음
) as dag:
    run_spark_batch_job = BashOperator(
        task_id='run_spark_batch_job',
        bash_command='python /opt/airflow/dags/spark_batch_job.py',
    )

    # 작업 순서 정의 
    run_spark_batch_job
