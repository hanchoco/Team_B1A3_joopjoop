import requests
print(requests.get("https://www.google.com", timeout=5).status_code)
