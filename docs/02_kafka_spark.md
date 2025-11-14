# Kafka와 Spark에 관해

-  Kafka
  - Kafka의 핵심 역할은 데이터를 수집하고, 저장하는 것이다.
  - 엄청난 양의 데이터가 쏟아져도 잃어버리지 않고, 순서대로, 안전하게 저장한다.
  - 여러 Consumer가 동시에 데이터를 가져갈 수 있도록 분배해준다.

- Spark
  - Spark의 핵심 역할은 데이터를 처리하고 연산하는 것이다.
  - Kafka에서 데이터를 들고와서, 검증하고, 자르고, 붙이고, 다른 데이터와 합치는 등 복잡한 작업을 수행한다.

## Kafka Streams 

- Kafka Streams
  - Kafka에 추가로 장착할 수 있는 라이브러리이다.
  - Spark처럼 별도의 거대한 공장을 차릴 필요 없이, Kafka 위에서 바로 간단한 필터링이나 변환을 할 수 있게 해준다.(경량화)
  - 하지만 간단한 작업만을 할 수 있다.

## SCHEMA를 선언한 이유

Kafka는 데이터를 단순한 텍스트 덩어리(JSON 문자열)로 갖고 있다. Spark가 이 텍스트를 효율적으로 계산하고 처리하려면, 텍스트 덩어리 안에 "어떤 이름의 컬럼이 있고, 각 컬럼은 어떤 데이터 타입인지" 명확하게 알아야 한다.
SCHEMA는 이 원본 JSON 문자열을 Spark가 이해하는 DataFrame으로 변환해주는 역할을 한다.

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