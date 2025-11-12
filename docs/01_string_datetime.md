# strptime과 strftime

## strptime

string parse time의 약자로 문자열 형식으로 되어 있는 날짜와 시간 데이터를 datetime객체로 변환한다.

### 사용 예시
```python
from datetime import datetime

date_string = "2024-12-08 14:30:00"
date_object = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")

print(date_object)  # 출력: 2024-12-08 14:30:00
```

### 주요 포맷
```python
%Y: 4자리 연도 (e.g., 2024)
%m: 2자리 월 (01 ~ 12)
%d: 2자리 일 (01 ~ 31)
%H: 24시간 형식의 시 (00 ~ 23)
%M: 분 (00 ~ 59)
%S: 초 (00 ~ 59)
```

## strftime

string format time의 약자로, datetime 객체를 특정 형식의 문자열로 변환한다.

### 사용 예시
```python
from datetime import datetime

date_object = datetime(2024, 12, 8, 14, 30, 0)
date_string = date_object.strftime("%Y-%m-%d %H:%M:%S")

print(date_string)  # 출력: 2024-12-08 14:30:00
```

### 주요 포맷
```python
%Y: 4자리 연도
%m: 2자리 월
%d: 2자리 일
%H: 24시간 형식의 시
%M: 분
%S: 초
```