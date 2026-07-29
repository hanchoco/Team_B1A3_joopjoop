import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE_DIR, "processed_policies.json")

data = json.load(open(path, encoding="utf-8"))

for p in data:
    extra_conditions = [c for c in p["policy_conditions"] 
                         if c["condition_key"] not in ("profile.age", "profile.region_code", "profile.income_band_code")]
    if extra_conditions:
        print(p["policies"]["title"])
        for c in extra_conditions:
            print("  ", c["condition_key"], c["operator"], c["expected_value_json"], "|", c["description"])

