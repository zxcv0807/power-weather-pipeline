# kafka 배포판 비교

Kafka는 실시간으로 발생하는 대량의 데이터를 안정적이고, 빠르게 처리하기 위한 오픈소스 분산 스트리밍 플랫폼이다.
docker-compose.yml 파일에서 kafka 이미지를 선택할 때, 여러가지 선택지가 있었다.
wurstmeister/kafka, confluentinc/cp-kafka, bitnami/kafka

## wurstmeister/kafka

이 이미지는 과거에 많이 사용되었던 이미지이다. 그리고 과거에는 kafka가 Zookeeper라는 서비스와 함께 사용되었다.
하지만 Kafka가 버전이 올라가면서 Zookeeper를 제거하고 KRaft를 사용하는 방향으로 가고 있다.
게다가 wurstmeister/kafka도 docker-hub에서 3년전 업데이트가 마지막인 구식인 것을 확인했기에, 이 이미지는 사용하지 않았다.

## bitnami/kafka

Bitnami는 다양한 오픈소스 소프트웨어를 패키징하는 전문 회사이다. 설정이 직관적이고, 불필요한 기능 없이 가벼워서 컨테이너 환경(Docker/K8s) 환경에서 쉽고 빠르게 실행될 수 있도록 최적화되었다.
다른 소프트웨어(Redis, MySQL 등)도 Bitnami 이미지를 사용한다면, 설정 방식이 편해 함께 사용하기 좋다.
Confluent 이미지보다 순수 Apache Kafka에 더 가깝다.
하지만 선택하지 않았다. Confluent Kafka가 좀 더 매력적인 측면이 있었기 때문이다.

## confluentinc/cp-kafka

Confluent는 Apache Kafka를 최초로 만든 핵심 개발자들이 창립한 회사이다. 규모가 있는 기업에서는 단순 Kafka 브로커뿐만 아니라, Confluent가 제공하는 부가 기능(Schema Registry, Kafka Connect 등)을 함께 사용하는 경우가 많다. 
또한, Kafka 관련 고급 설정이나, 문제 해결을 위해 검색할 때 나오는 공식문서들이 이 이미지 설정과 잘 맞는다고 한다.
이러한 점은 실제 회사에서는 bitnami보다는 confluent 생태계에 익숙해지는 것이 취업에 조금이라도 유리하다고 생각했기 때문에, 이 이미지를 선택했다.

## Zookeeper와 KRaft 

Zookeeper는 분산 시스템을 위한 코디네이션 서비스이다. 
- Kafka의 서버(브로커)를 관리하고, 
- Kafka의 파티션을 관리할 리더 브로커를 정하고, 
- 토픽이 어디에 저장되어 있는 지와 같은 메타데이터를 저장한다.

KRaft는 Kafka 클러스터의 메타데이터를 관리하기 위해, 별도의 Zookeeper 클러스터를 운영하는 대신, Kafka 브로커 자체 내부에서 Raft 합의 알고리즘을 이용해 메타데이터(브로커, 토픽, 파티션 등)를 관리하는 방식이다.
- Zookeeper 없이도 메타데이터 관리가 가능해져, Zookeeper에 대한 의존성이 제거되었다.
- Kafka 브로커와 클러스터 관리를 담당하는 컨트롤러가 메타데이터를 직접 관리하므로, 시스템의 복잡성과 운영부담이 줄었다.
- Zookeeper와 Kafka 간의 통신 지연이 사라지고, 메타데이터 관리가 효율적으로 이루어져 성능이 향상되었다.
- KRaft 모드를 통해 메타데이터 관리의 병목 현상이 줄어들고, 클러스터의 확장성이 개선되었다.