# Kafka의 offset과 Spark Streaming의 Checkpoint에 관해

## Kafka Offset
Kafka 토픽의 각 파티션 내에서 메시지(레코드)가 저장되는 순서를 나타내는 64비트(Integer)값이다.

### 특징
- 단조 증가(Monotonically Increasing): 오프셋은 0부터 시작하여 메시지가 추가될 때마다 1씩 증가한다. 절대 줄어들지 않는다.
- 불변성(Immutable): 한 번 할당된 오프셋은 해당 메시지를 삭제되기 전까지 변하지 않는다.
- 위치 지정: 컨슈머(Spark)가 데이터를 어디까지 읽었는 지 판단하는 유일한 기준이다.

### Log End Offset(LEO)
현재 파티션에서 저장된 마지막 메시지의 offset + 1 (다음 메시지가 들어갈 위치)를 의미한다.

## S3 Checkpoint (Spark의 상태 저장소)
Spark Structured Streaming이 **내결함성(Fault Tolerance)**과 정확히 한 번(Exactly-Once)처리를 보장하기 위해 사용하는 메타데이터 저장소이다.

### 저장 내용
- Offset Log: 각 마이크로 배치(Micro-batch)가 처리를 끝낸 마지막 offset 정보. (예: batch_0은 offset 0~100 처리 완료)
- Commit Log: 해당 배치의 처리가 성공적으로 완료되어 Sink(저장소)에 반영되었음을 나타내는 마커
- State Data: 집계(Aggregation)연산 시 필요한 중간 상태 데이터

### 작동 원리
Spark는 데이터를 처리하기 전에, "이번 배치는 offset 100부터 200까지 읽겠다."는 계획을 Checkpoint에 기록한다.


## 둘 간의 상호 작용 및 에러 발생 메커니즘
에러(OffsetOutOfRangeException 또는 DataLoss)는 Spark가 관리하는 '기대 offset'과 Kafka가 보유한 '실제 offset'간의 불일치로 인해 발생한다.

### 정상적인 흐름
1. Terminate: Spark가 오프셋 150까지 처리를 완료하고, S3 Checkpoint에 {"topic": "A", "partition": 0, "offset": 150} 을 기록하고 종료된다.
2. Restart: Spark가 재시작되면 S3 Checkpoint를 읽는다. "마지막 커밋이 150이므로, 151부터 읽어야 한다." 라고 판단한다.
3. Fetch: Spark Driver가 Kafka 브로커에게 "파티션 0의 offset 151부터 데이터를 달라"고 요청한다.
4. Response: Kafka는 offset 151이 유효하므로 데이터를 전송한다.

### 에러 발생 흐름
1. Previous State: Spark Checkpoint에는 마지막 처리 offset이 150으로 기록되어 있다. (재시작시 151 요청 예정)
2. Infrastructure Reset: Kafka 컨테이너가 재생성되면서 기존 데이터 볼륨이 삭제되었다.
3. Topic Recreation: Kafka 토픽이 새로 생성되었다. 이 토픽의 offset은 0부터 시작한다.
4. Spark Restart & Request: Spark는 재시작하면 S3 Checkpoint를 읽고, Kafka에게 "offset 151부터 줘" 라고 요청한다.
5. Exception: Kafka 브로커는 자신의 현재 offset은 0인데 151을 요청받았기 때문에, 해당 요청을 처리할 수 없다.

### 결론
- Kafka Offset: 서버 측(Broker)의 물리적인 데이터 위치
- S3 Checkpoint: Spark의 논리적인 처리 기록
- 원인: Kafka의 물리적 위치가 0으로 초기화되었으나, S3의 Checkpoint는 초기화되지 않아 존재하지 않는 offset 주소를 참조하려는 시도를 하게 되면서 Index Out of Bounds 오류이다.


## 데이터 처리 방식의 3가지 유형

### 1) At-most-once(최대 한 번)
- 동작: 메시지를 전송하고, 수신 확인(Ack)를 기다리지 않는다.
- 특징:
  - 전송 실패 시 재시도하지 않으므로 데이터 유실 가능성이 있다.
  - Ack 대기 비용이 없어 처리 속도가 가장 빠르다.
  - 일부 유실이 허용되는 데이터 수집, 단순 로그 수집에 사용된다.

### 2) At-least-once(적어도 한 번)
- 동작: 메시지를 전송하고, 반드시 수신 확인을 받는다. 일정 시간 내에 Ack가 오지 않으면 성공할 때까지 재전송 한다.
- 특징:
  - 데이터 유실이 발생하지 않는다.
  - 네트워크 지연 등으로 Ack만 소실될 경우, 이미 전송된 데이터를 다시 보내므로 데이터 중복이 발생할 수 있다.
  - Kafka의 기본 동작 방식이다.

### 3) Exactly-once(정확히 한 번)
- 동작: 시스템 장애나 재시도가 발생하더라도, 최종적으로 데이터가 중복없이 단 한 번만 처리된 것과 동일한 상태를 보장한다.
- 특징:
  - 구현 복잡도와 시스템 부하가 높다.
  - Spark Structured Streaming은 Checkpoint와 Idempotent(멱등성) Sink를 통해 이 수준의 처리를 지향한다.
  - 멱등성이란 같은 작업을 여러 번 수행해도 결과가 달라지지 않는 성질을 의미한다.
  - Spark는 저장할 때 파일 이름에 배치 ID(Batch Id)를 포함시킨다. 재실행되어 똑같은 파일명으로 다시 업로드를 시도하면, 기존 파일을 덮어쓴다.