# Spark, Kafka, 파이썬 스크립트 실행을 위한 메모리 부족
메모리 부족 문제로 인해, 
- Airflow가 작업 실행 도중 데이터베이스(postgres)와의 연결을 잃거나, 
- ec2 서버가 다운되는 문제가 발생했다.

## Spark의 batch 작업에서 메모리 해결

- 수정 파일: spark_batch_job
- 코드:
```python
return SparkSession.builder \
        .appName("DailyBatchAnalysis") \
        .master("local[1]") \
        .config("spark.jars.packages", f"{HADOOP_AWS_JAR},{AWS_SDK_JAR}") \
        .config("spark.driver.memory", "512m") \
        .config("spark.executor.memory", "512m") \
        .config("spark.sql.shuffle.partitions", "1") \
        ...
```
### A local[*] => local[1]
c7i-flex.large 인스턴스는 cpu가 2개이다. 
만약 local[*]은 cpu2개를 Spark가 모두 사용하게 된다. 하지만 EC2 서버에서는 Kafka, Airflow Scheduler, Airflow WebServer, Postgres & Redis, OS 커널 들을 실행해야하는 입장에서 Spark가 cpu를 모두 사용하게 되면 에러가 발생하게 된다.
그래서 cpu 개수를 1개로 제한하였다.

### B .config("spark.sql.shuffle.partitions", "1")
Spark는 **파티션**이라는 데이터를 처리하는 가장 작은 단위를 사용한다. 
왜냐하면 거대한 데이터를 한 번에 처리할 수 없으니, 여러 파티션으로 잘라서 여러 CPU에게 나눠주고 동시에 처리하게 하기 때문이다. 
실제로 Spark의 파티션의 기본 값은 200이다. 데이터를 200조각으로 자른다는 의미이다.

하지만 우리는 데이터의 규모와 양이 매우 작기 때문에, 이 작은 데이터를 200개로 나누고, 200개의 태스크를 생성하고, 이를 관리하기 위한 Metadata에 기록하는 과정이 오히려 메모리를 더 낭비하는 방식이다. 
=> .config("spark.sql.shuffle.partitions", "1") 의 설정을 통해서 파티션의 단위를 1로 제한하였다. 만약 추후에 데이터가 커지게 된다면 해당 설정을 수정해야 할 것이다.


## Swap Memory 설정
c7i-flex.large의 메모리는 4GB이다. 여기에 SSD의 일부를 마치 RAM처럼 사용할 수 있게 해주는 **스왑 메모리**를 사용하여 메모리 부족 문제를 해결할 수 있다.

### 스왑 메모리 2GB 추가하기
1. 스왑 파일 생성
```bash
# 128MB * 16 = 2GB짜리 공간 확보
sudo dd if=/dev/zero of=/swapfile bs=128M count=16
```
2. 권한 설정
```bash
sudo chmod 600 /swapfile
```
3. 스왑 영역 설정
```bash
sudo mkswap /swapfile
```
4. 스왑 활성화
```bash
sudo swapon /swapfile
```
5. 확인
```bash
free -h
# 만약 결과에서 Swap: 행에 2.0Gi가 보이면 성공이다.
```
6. 재부팅 후에도 유지되도록 설정
```bash
sudo nano /etc/fstab
```
파일의 마지막 줄에 아래의 내용을 추가하고 저장
```Plaintext
/swapfile swap swap defaults 0 0
```

### 2GB만 설정한 이유
리눅스 운영체제는 메모리가 부족하면 프로세스를 죽이게 되는데, 만약 스왑 메모리를 크게 설정했다면 디스크에 공간이 남았다고 판단하고, 램에 있는 것을 디스크로 옮기고 계속하면서 버티게 된다.
- 문제점
  - 하드디스크는 RAM보다 속도가 수천~수만 배 느리다.
  - 4GB를 설정하고, 꽉 채워서 쓰게되면, CPU는 데이터를 처리하는 시간보다 데이터를 디스크에서 RAM으로 옮기는 시간에 대부분 쓰인다.
  - 결과: 서버가 죽지 않았지만 아무런 응답을 하지 않는 상태가 된다.

- 권장 비율
일반적으로 클라우드 인프라 엔지니어링에서 통용되는 스왑 설정 공식이 있다고 한다.
  - RAM 2GB 이하: RAM의 2배
  - RAM 2GB ~ 8GB: RAM의 0.5배배 또는 최대 4GB
  - RAM 8GB 이상: 최소한(2GB~4GB)만 설정하거나 사용하지 않음.

=> 서버가 멈추지 않는 선에서 최소한의 크기인 2GB로 스왑 메모리를 설정하였다.