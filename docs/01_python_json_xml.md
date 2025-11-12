# Python, json, xml

## JSON 직렬화

JSON 직렬화는 python 데이터를 json 규격의 문자열로 바꾸는 것이다. python이 메모리에서 사용하는 객체(딕셔너리, 리스트 등)를 디스크에 저장하거나 네트워크로 전송할 수 있도록 단순한 문자열(string)로 변환하는 과정을 말한다.
json.dumps()는 파이썬 객체를 json형식의 문자열로 변환(직렬화)한다.

## XML 파싱
xml은 트리 구조이기 때문에 json처럼 단순한 딕셔너리로 바로 변환되지 않는다.
xml.etree.ElementTree(ET)는 이러한 트리 구조를 파이썬에서 다루기 쉽게 해준다.
- ET.fromstring(xml_string): XML 문자열을 파싱해서 Element 객체 트리를 만든다.
- root.find('태그') / root.findall('태그'): 만들어진 트리에서 원하는 요소를 태그 이름으로 찾을 수 있다.
- element.text / element.attrib: 찾은 요소의 텍스트 내용이나 속성 값을 가져온다.
