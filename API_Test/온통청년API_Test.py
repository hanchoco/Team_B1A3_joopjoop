"""
온통청년 API 실제 호출 - 최신 스펙 반영
"""

import requests

API_KEY = "382d0fed-6b39-450f-abad-453e343ee6e1"

url = "https://www.youthcenter.go.kr/go/ythip/getPlcy"
params = {
    "apiKeyNm": API_KEY,
    "pageNum": 1,
    "pageSize": 10,
    "rtnType": "json",
}

response = requests.get(url, params=params, timeout=10)

print("상태코드:", response.status_code)
print("Content-Type:", response.headers.get("Content-Type"))
print(response.text[:1000])

with open("raw_policy_sample.json", "w", encoding="utf-8") as f:
    f.write(response.text)

print("\nraw_policy_sample.json 저장 완료. 실제 필드명 확인하세요.")