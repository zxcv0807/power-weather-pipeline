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

## 요약

- Producer는 비동기다. send()는 빠르지만 버퍼가 찰떄까지 전송을 보장하지 않는다. flush()를 호출해야 실제 전송이 보장된다.
- Key-Value: 지금은 value=... 만 보냈지만, key=... 도 보낼 수 있다.
  - producer.send('weather_realtime', key='seoul', value=weather_data)
  - Kafka는 동일한 Key를 가진 데이터는 항상 동일한 파티션(토픽의 하위 저장소)에 순서대로 저장하는 것을 보장한다.
  - 예를 들어, seoul이라는 key를 사용하면, 서울 날씨 데이터는 Kafka 내부에 항상 순서대로 쌓이게 된다.
