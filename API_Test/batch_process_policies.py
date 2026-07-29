"""
raw_policy_sample.json(온통청년 API 실제 응답, 정책 여러 개)을 읽어서
각 정책마다 rule_extractor.process_policy()를 돌리고, 결과를 전부 모아서
processed_policies.json으로 저장합니다.

이 결과가 그대로 A03(Rule 검수) 화면에 올라갈 초안입니다.

    python batch_process_policies.py
"""

import json
import os
from rule_extractor import process_policy

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(BASE_DIR, "raw_policy_sample.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "processed_policies.json")


def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_policies = data["result"]["youthPolicyList"]
    print(f"총 {len(raw_policies)}개 정책 처리 시작...\n")

    results = []
    failed = []

    for i, raw in enumerate(raw_policies, start=1):
        name = raw.get("plcyNm", "(이름 없음)")
        try:
            processed = process_policy(raw)
            results.append(processed)
            print(f"[{i}/{len(raw_policies)}] 완료 - {name}")
        except Exception as e:
            failed.append({"plcyNm": name, "error": str(e)})
            print(f"[{i}/{len(raw_policies)}] 실패 - {name} ({e})")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n완료: {len(results)}개 성공, {len(failed)}개 실패")
    print(f"결과 저장: {OUTPUT_PATH}")

    if failed:
        print("\n실패한 정책들:")
        for f_item in failed:
            print(" -", f_item["plcyNm"], ":", f_item["error"])


if __name__ == "__main__":
    main()
