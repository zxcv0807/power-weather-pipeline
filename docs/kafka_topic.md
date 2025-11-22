# Kafka의 Topic에 관해

데이터가 저장되는 카테고리 공간이다.
Producer는 특정 topic에 데이터를 보내고, Consumer는 topic에서 데이터를 가져가 처리한다.
각 topic은 이름으로 구분되며, 하나 이상의 파티션으로 나뉘어 병렬 처리와 효율성을 높인다.

## 주요 특징

- 데이터 저장소: Producer가 보낸 메시지(데이터)를 저장하는 논리적인 저장 공간이다.
- 카테고리: 다양한 종류의 메시지를 topic별로 분류하여 관리한다. 예를 들어, 'purchases', 'logs'와 같은 topic으로 구분할 수 있습니다.
- 독립적인 구조: 각 topic은 독립적인 데이터 스트림이며, 서로 영향을 주지 않는다.
- 파티션: topic은 하나 이상의 파티션으로 구성된다. 파티션은 데이터 처리의 병렬성을 높이기 위한 단위로 사용되며, 각 파티션 내에서는 메시지의 순서가 보장된다.

### Topic의 Replication Factor(복제 개수)

Topic을 설명할 때, '파티션'이 병렬 처리를 위한 것이라면, **Replication(복제)**은 **고가용성(High Availability)과 내구성(Durability)**을 위한 것이다. 즉 서버가 터졌을 때를 대비한 보험이다.


- Replication Factor: 토픽의 파티션을 몇 개의 복제본으로 유지할 지 정하는 숫자이다. 보통 Replication Factor는 3으로 설정해서 운영 안정성을 높인다.
- 예를 들어 Replication Factor = 3 이라면, 원본 1개 + 복제본 2개 = 총 3개의 데이터 복사본을 서로 다른 브로커(서버)에 저장한다.

- Leader와 Follower
복제된 파티션들은 모두 평등하지 않고 계급이 있다.
  - Leader: 실질적인 대장이다. Producer가 데이터를 보내고, Consumer가 데이터를 읽어가는 작업은 오직 Leader하고만 수행한다. (최신 버전에서는 Follower Fetching도 가능하지만 기본은 Leader이다.)
  - Follower: Leader를 바라보며 데이터를 똑같이 복제해가는 역할만 한다. Leader가 죽었을 때, 새로운 Leader가 되기 위해 대기한다.

- ISR(In-Sync-Replicas)
  - Leader와 현재 데이터 싱크가 완벽하게 맞는 Follower들의 목록이다.
  - 만약, Replication Factor = 3 인데 Follower 하나가 고장나서 데이터를 못 따라오고 있다면, 그 녀석은 ISR 그룹에서 쫓겨난다.
  - 특히, 신뢰성 설정에서 acks=all 이라면 이 ISR 그룹이 모두 저장했는 지 확인하는 것이다.