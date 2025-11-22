# Kafka Producer에 관해

**Kafka Producer**는 Kafka 클러스터 내의 특정 **토픽** 으로 **레코드(데이터)**를 **전송**하는 역할을 하는 클라이언트 애플리케이션이다.

## Producer의 4가지 역할

### 1. 접속

Producer는 Kafka 클러스터의 주소를 알아야한다.
```python
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    ...
)
```
- bootstrap_servers: Producer가 처음 접속할 Kafka 서버(브로커)의 주소 목록이다.
- Producer는 이 주소로 일단 접속한 뒤, 클러스터 전체의 지도(어떤 토픽이 어디에 있는 지)를 받아온다. 그래서 모든 서버 주소를 다 적을 필요 없이, 한두 개만 알려줘도 알아서 잘 찾아간다.

### 2. 직렬화

Kafka는 파이썬의 딕셔너리나 JSON을 이해하지 못한다. 오직 **bytes**의 흐름으로만 데이터를 저장하기 때문에, 데이터를 'bytes'로 변환하는 과정이 필요하다.
```python
producer = KafkaProducer(
    ...
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)
```
- 이 과정을 통해 
{'temp': 10} (Python dict) 
=> '{"temp": 10}' (String) 
=> b'{"temp": 10}' (Bytes)로 변환되어 Kafka에 저장될 수 있다.

### 3. 전송

Producer는 데이터를 특정 토픽으로 보낸다.
```python
producer.send(TOPIC_NAME, value=weather_data)
```
- producer.send(): 이 명령은 비동기로 작동한다.
- 즉, "데이터를 전송하라"고 명령을 내리면, Producer는 일단 데이터를 내부 임시 저장소(버퍼)에 쌓아 둔다.
- '데이터 전송 완료'와 같은 확인을 기다리지 않고, 바로 다음 코드로 넘어간다. (그래서 매우 빠르다.)

### 4.전송 완료 보장(Flush)

Producer는 효율을 위해 데이터를 버퍼에 모았다가 한꺼번에 batch로 묶어서 전송한다. 하지만 필요에 따라 "지금 당장 보내"라고 강제할 수 있다.
```python
producer.flush()
```
- producer.flush(): 버퍼에 쌓여있는 데이터를 당장 Kafka로 전송하고, 서버가 데이터를 받았다고 응답할 때까지 기다리라는 명령이다.

### 5. 신뢰성 설정(acks)

acks(Acknowledgement)는 producer.send()를 했을 때, Producer가 "데이터가 안전하게 저장되었다."라고 간주하는 기준을 정하는 옵션이다.
**속도(Throughput)**와 **데이터 안정성(Durability)** 사이의 트레이드오프를 결정하는 요소이다.
```python
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    acks='all',  # 0, 1, 'all' 중 선택
    ...
)
```
- acks=0 (속도 최우선, 유실 위험 높음)
  - 동작: Producer는 데이터를 네트워크로 보내기만 하고, 브로커가 잘 받았는 지 확인하지 않는다. 전송 즉시 '성공'으로 간주한다.
  - 장점: 응답을 기다리는 시간이 없으므로 가장 빠르다.
  - 단점: 브로커가 다운되거나 네트워크 오류로 데이터가 도달하지 못해도, Producer는 이를 모르고 계속 다음 데이터를 보낸다. 데이터 유실 가능성이 가장 높다.
  - 용도: GPS 위치 데이터, 일부 로그 등 유실되어도 큰 문제가 없는 데이터

- acks=1 (균형, 기본값인 경우가 많음)
  - 동작: 데이터가 Leader 파티션에 저장되면 성공으로 간주한다. (Follower들의 복제 여부는 기다리지 않는다.)
  - 장점: 적당한 속도와 안전성을 보장한다.
  - 단점: Leader가 데이터를 받고 응답을 보낸 직후, Follower에게 복제되기 전에 Leader 브로커가 죽으면 데이터가 유실될 수 있다.

- acks=all 또는 acks=-1 (안전 최우선, 가장 느림)
  - 동작: Leader 파티션 뿐만 아니라, **모든 ISR(In-Sync Replicas, Leader와 싱크가 맞는 Follower들)**이 데이터를 복제할 때까지 기다린다.
  - 장점: Leader가 죽어도 다른 Follower가 데이터를 가지고 있으므로, 데이터 유실이 거의 없다.
  - 단점: 모든 브로커의 응답을 기다려야 하므로, 가장 느리다.
  = 용도: 결제 정보, 은행 거래 내역 등 절대 잃어버려서는 안되는 중요 데이터

## 요약

- Producer는 비동기다. send()는 빠르지만 버퍼가 찰떄까지 전송을 보장하지 않는다. flush()를 호출해야 실제 전송이 보장된다.
- Key-Value: 지금은 value=... 만 보냈지만, key=... 도 보낼 수 있다.
  - producer.send('weather_realtime', key='seoul', value=weather_data)
  - Kafka는 동일한 Key를 가진 데이터는 항상 동일한 파티션(토픽의 하위 저장소)에 순서대로 저장하는 것을 보장한다.
  - 예를 들어, seoul이라는 key를 사용하면, 서울 날씨 데이터는 Kafka 내부에 항상 순서대로 쌓이게 된다.
