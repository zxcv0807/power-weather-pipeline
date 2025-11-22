# Kafka와 Spark에 관해

-  Kafka
  - Kafka의 핵심 역할은 데이터를 수집하고, 저장하는 것이다.
  - 엄청난 양의 데이터가 쏟아져도 잃어버리지 않고, 순서대로, 안전하게 저장한다.
  - 여러 Consumer가 동시에 데이터를 가져갈 수 있도록 분배해준다.

- Spark
  - Spark의 핵심 역할은 데이터를 처리하고 연산하는 것이다.
  - Kafka에서 데이터를 들고와서, 검증하고, 자르고, 붙이고, 다른 데이터와 합치는 등 복잡한 작업을 수행한다.

## Kafka Streams vs Spark Streaming

- Kafka Streams
  - Kafka에 추가로 장착할 수 있는 라이브러리이다. 조인/집계 등 복잡한 로직도 수행 가능하다.
  - 하지만 Kafka to Kafka 처리에 최적화되어 있어, 외부 저장소(S3, DB)로 데이터를 내보내거나, 대규모 배치 처리를 하기에는 Spark보다 불편하다.

- Spark Streaming
  - Kafka to Everywhere가 강점이다. 다양한 포맷(Parquet, Avro)과 다양한 저장소(S3, RDB)를 지원한다.
  - 우리 프로젝트처럼 Data Lake 구축이 목표일 때 적합하다.

### Spark를 사용한 이유
Spark를 사용한 이유는 Kafka의 데이터를 수집하고, 가공해서 외부 스토리지(S3)에 Parquet 포맷으로 적재하는 것이 목표이기 때문이다. Kafka Streams는 Kafka 내에서의 파이프라인에 최적화되어 있어 외부 싱크와 연결이 제한적이지만, Spark는 다양한 데이터 소스와 싱크(S3, DB 등)를 유연하게 연결할 수 있고, 대용량 배치처리까지 확장 가능하기 때문에 Spark를 선택했다.


## SCHEMA를 선언한 이유

Kafka는 데이터를 단순한 텍스트 덩어리(JSON 문자열)로 갖고 있다. Spark가 이 텍스트를 효율적으로 계산하고 처리하려면, 텍스트 덩어리 안에 "어떤 이름의 컬럼이 있고, 각 컬럼은 어떤 데이터 타입인지" 명확하게 알아야 한다.

1. SCHEMA는 이 원본 JSON 문자열을 Spark가 이해하는 DataFrame으로 변환해주는 역할을 한다.

2. SCHEMA를 알려주면, Spark가 추측(Inference)하느라 시간을 낭비하지 않아 속도가 빠르다.
SCHEMA를 선언하지 않고, JSON을 읽으라고 한다면 아래와 같이 Spark는 작동한다.
  1) 전체 데이터를 훑는다.
  2) 데이터 타입을 추측한다.
  3) 다시 데이터를 읽으면서 변환한다.
이는 데이터를 처리하기도 전에 **타입을 알아내려고 데이터를 읽는 과정(오버헤드)**이 발생한다. 이를 SCHEMA Inference(스키마 추론)비용이라고 한다.
만약 SCHEMA가 정의되어 있다면, 불필요한 스캔과정이 사라지고, 곧바로 데이터를 읽으면서 변환하여 속도가 훨씬 빨라진다.

### StructType, StructField

StructType([...]): **설계도 전체(테이블 구조)**를 의미한다.
- 여러 개의 StructField(컬럼)를 리스트로 감싸는 컨테이너다.
- 데이터베이스 테이블의 정의 그 자체이다.

StructField(...): **개별 컬럼의 속성**을 정의한다.
- StructField는 항상 3개의 요소를 가진다.
  1. 이름: 컬럼명
  2. 데이터 타입: 이 컬럼에 들어갈 데이터의 종류
  3. Nullable 여부: True 또는 False

## org.apache.spark:spark-sql-kafka-0-10_2.12:4.0.1

1. org.apache.spark (Group ID): 이 패키지를 만들고 관리하는 조직의 이름이다.
2. spark-sql-kafka: 이 라이브러리의 핵심 기능이다.Spark SQL(스트리밍 포함)이 Kafka와 데이터를 주고받을 수 있게 해준다.
3. -0-10: 이 커넥터가 호환되는 Kafka 클라이언트 API 버전을 의미한다.
4. _2.12: 이 패키지가 컴파일된 Scala 버전이다.