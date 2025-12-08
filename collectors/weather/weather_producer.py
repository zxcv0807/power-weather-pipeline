import requests
import json
import time
import datetime
import os
from dotenv import load_dotenv
from kafka import KafkaProducer

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WEATHER_API_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092']
TOPIC_NAME = 'weather_realtime'

# 서울시청 좌표 (nx=60, ny=127). 다른 지역을 원하면 수정 가능
SEOUL_NX = 60
SEOUL_NY = 127

# Kafka Producer 생성 (JSON 직렬화 설정)
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
)

def get_base_time():
    """기상청 API가 요구하는 base_date와 base_time을 생성합니다."""

    now = datetime.datetime.now()
    
    # 초단기실황은 정각에 생성되고, 10분 이후에 제공됩니다.
    # 10분 이전에는 이전 시간의 데이터를 요청해야 합니다.
    if now.minute < 10:
        target_time = now - datetime.timedelta(hours=1)
    else:
        target_time = now
    
    base_date = target_time.strftime('%Y%m%d')
    base_time = target_time.strftime('%H00')
    return base_date, base_time


def fetch_weather_data():
    """기상청 API를 호출하여 실시간 날씨 데이터를 (JSON으로) 가져옵니다."""
    
    base_date, base_time = get_base_time()
    
    params = {
        'serviceKey': WEATHER_API_KEY,
        'dataType': 'JSON',
        'base_date': base_date,
        'base_time': base_time,
        'nx': SEOUL_NX,
        'ny': SEOUL_NY,
        'numOfRows': '10', # T1H(기온), RN1(강수량), PTY(강수형태) 등을 받기 위함
        'pageNo': '1'
    }

    try:
        response = requests.get(WEATHER_API_URL, params=params, timeout=120)
        response.raise_for_status()
        data = response.json()

        # JSON 응답 구조 파싱
        if data.get('response') and data['response'].get('body') and data['response']['body'].get('items'):
            items = data['response']['body']['items'].get('item', [])
            
            weather_data = {
                "base_datetime": f"{base_date}{base_time}"
            }
            
            # T1H(기온), RN1(1시간 강수량), PTY(강수형태) 값을 찾습니다.
            for item in items:
                category = item.get('category')
                obsr_value = item.get('obsrValue')
                
                if category == 'T1H': # 기온
                    weather_data['temperature_c'] = float(obsr_value)
                elif category == 'RN1': # 1시간 강수량
                    # "강수없음" 문자열을 0으로 처리
                    weather_data['rainfall_mm'] = float(0 if "강수" in str(obsr_value) else obsr_value)
                elif category == 'PTY': # 강수형태
                    weather_data['rainfall_type'] = int(obsr_value)

            return weather_data
        
        elif data.get('response') and data['response'].get('header'):
            # API 키 오류 등 정상적이지 않은 응답 처리
            header = data['response']['header']
            print(f"API Error: {header.get('resultMsg')} (Code: {header.get('resultCode')})")
            return None
        else:
            print(f"알 수 없는 API 응답 구조입니다: {data}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"API 호출 중 오류 발생: {e}")
        return None
    except json.JSONDecodeError:
        print(f"JSON 파싱 오류. 응답 내용: {response.text[:200]}...")
        return None
    except Exception as e:
        print(f"기타 오류 발생: {e}")
        return None

def main():
    print(f"Starting producer for topic: {TOPIC_NAME}")
    print(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")

    WAIT_TIME_SECONDS = 3600

    try:
        while True:
            current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{current_time_str}] Trying to fetch weather data...")
            
            weather_data = fetch_weather_data()
            
            if weather_data:
                producer.send(TOPIC_NAME, value=weather_data)
                producer.flush() 
                print(f"✅ Data sent to Kafka: {weather_data}")
            else:
                print("❌ Failed to fetch data, will retry in next cycle.")

            print(f"Waiting for {WAIT_TIME_SECONDS} seconds...")
            time.sleep(WAIT_TIME_SECONDS)

    except KeyboardInterrupt:
        print("\nStopping producer...")
    finally:
        producer.close()
        print("Kafka producer closed.")

if __name__ == "__main__":
    main()