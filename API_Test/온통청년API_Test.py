"""
온통청년 API에서 정책 30개 받아서 저장 + 사업기간 날짜필드 채워진 비율 바로 확인.

    python fetch_policy_sample.py
"""

import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["YOUTHCENTER_API_KEY"] #수정하면 안됨! env 수정하기(테스트 가이드 참고)

url = "https://www.youthcenter.go.kr/go/ythip/getPlcy"
params = {
    "apiKeyNm": API_KEY,
    "pageNum": 1,
    "pageSize": 30,   
    "rtnType": "json",
}

response = requests.get(url, params=params, timeout=10)
data = response.json()

print("상태코드:", response.status_code)
print("전체 정책 개수(totCount):", data["result"]["pagging"]["totCount"])
print("실제 받아온 개수:", len(data["result"]["youthPolicyList"]))

# 파일로 저장 (덮어쓰기)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
save_path = os.path.join(BASE_DIR, "raw_policy_sample.json")

with open(save_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("\nraw_policy_sample.json 저장 완료 (30개 기준으로 덮어씀)")

# 사업기간 날짜필드 채워진 비율 바로 확인
policies = data["result"]["youthPolicyList"]
filled = sum(1 for p in policies if p.get("bizPrdBgngYmd", "").strip())
print(f"\n날짜 필드(bizPrdBgngYmd) 채워진 정책: {filled} / {len(policies)}")

print("\n--- 상세 ---")
for p in policies:
    print(
        p.get("plcyNm"), "|",
        repr(p.get("bizPrdBgngYmd")), "~", repr(p.get("bizPrdEndYmd")), "|",
        (p.get("bizPrdEtcCn") or "")[:30]
    )