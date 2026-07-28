"""
가장 먼저 이거부터 실행해서 토큰이 살아있는지 확인하세요.
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 핵심: Upstage는 OpenAI SDK와 100% 호환됩니다.
# api_key와 base_url만 바꿔주면 나머지 코드는 OpenAI 쓰던 것과 완전히 동일합니다.
client = OpenAI(
    api_key=os.environ["UPSTAGE_API_KEY"],
    base_url="https://api.upstage.ai/v1",
)

response = client.chat.completions.create(
    model="solar-pro2",  # 가벼운 테스트/QA용이면 solar-mini도 가능
    messages=[
        {"role": "user", "content": "안녕, 잘 연결됐어? 한 문장으로만 대답해줘."}
    ],
)

print("연결 성공! 응답:")
print(response.choices[0].message.content)
