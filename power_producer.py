import requests
import json
import time
import datetime
import os
from dotenv import load_dotenv
from kafka import KafkaProducer
import xml.etree.ElementTree as ET

load_dotenv()

SERVICE_KEY = os.getenv("POWER_API_KEY")
API_URL = "https://openapi.kpx.or.kr/openapi/sukub5mMaxDatetime/getSukub5mMaxDatetime"
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092']
TOPIC_NAME = 'power_demand_realtime'

# Kafka Producer 생성 (JSON 직렬화 설정)
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

def fetch_power_data():
    """전력거래소 API를 호출하여 실시간 전력 데이터를 가져옵니다."""

    params = {
        'serviceKey': SERVICE_KEY,
    }

    try:
        response = requests.get(API_URL, params=params, timeout=10)
        response.raise_for_status()
        
        # 1. XML 파싱 시작
        root = ET.fromstring(response.content)
        
        # 2. 에러 코드 확인 (XML 경로 기반)
        result_code = root.findtext('.//resultCode') # './/'는 하위 모든 태그에서 찾기
        if result_code != '00': # '00'이 정상이 아닐 경우
            result_msg = root.findtext('.//resultMsg')
            print(f"API Error: {result_msg} (Code: {result_code})")
            return None

        # 3. 정상 데이터(item) 찾기 (XML 경로 기반)
        item = root.find('.//item') # 'body/items/item' 경로에 있을 item 태그
        
        if item is not None:
            # 4. XML 태그에서 텍스트(데이터) 추출
            base_datetime = item.findtext('baseDatetime')
            curr_pwr_tot = item.findtext('currPwrTot')
            supp_reserve_pwr = item.findtext('suppReservePwr')

            power_data = {
                "base_datetime": base_datetime,
                "current_demand_mw": float(curr_pwr_tot if curr_pwr_tot else 0),
                "reserve_power_mw": float(supp_reserve_pwr if supp_reserve_pwr else 0)
            }
            return power_data
        else:
            print("API 응답 성공. (item 태그를 찾을 수 없음)")
            return None

    except requests.exceptions.RequestException as e:
        print(f"API 호출 중 오류 발생: {e}")
        return None
    except ET.ParseError: # XML 파싱 오류
        print(f"XML 파싱 오류. 응답 내용: {response.text[:200]}...")
        return None
    except Exception as e:
        print(f"기타 오류 발생: {e}")
        return None

def main():
    print(f"Starting producer for topic: {TOPIC_NAME}")
    print(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")

    # 100회 트래픽 제한을 고려, 5분(300초)보다 길게 설정 (예: 15분)
    WAIT_TIME_SECONDS = 900

    try:
        while True:
            current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{current_time_str}] Trying to fetch power data...")
            
            power_data = fetch_power_data()
            
            if power_data:
                # Kafka로 데이터 전송
                producer.send(TOPIC_NAME, value=power_data)
                producer.flush() # 즉시 전송 강제
                print(f"✅ Data sent to Kafka: {power_data}")
            else:
                print("❌ Failed to fetch data, will retry in next cycle.")

            print(f"Waiting for {WAIT_TIME_SECONDS} seconds...")
            time.sleep(WAIT_TIME_SECONDS)
    
    except KeyboardInterrupt:
        print("Stopping producer...")
    finally:
        producer.close()
        print("Kafka producer closed.")

if __name__ == "__main__":
    main()