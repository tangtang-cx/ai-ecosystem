import json
import urllib.error
import urllib.request

HOSTS = ["https://cloud.dify.ai", "https://udify.app"]
TOKEN = "CTbEyrNETzo7iVA7"
APP_ID = "6d6a7cea-15e5-43a0-a9c6-54a13816ef30"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
    "X-App-Token": TOKEN,
    "X-App-Id": APP_ID,
}


def call(host, path, method="GET", payload=None, extra=None):
    url = host + path
    headers = dict(HEADERS)
    headers.update(extra or {})
    data = json.dumps(payload).encode() if payload is not None else None
    try:
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=90) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")[:300]
    except Exception as error:
        return 0, f"{type(error).__name__}: {error}"


for host in HOSTS:
    print(f"\n===== {host} =====")
    status, body = call(host, f"/api/parameters?app_id={APP_ID}")
    print(f"GET /api/parameters -> {status}")
    if status == 200:
        try:
            data = json.loads(body)
            print(json.dumps(data, ensure_ascii=False, indent=2)[:2200])
        except Exception:
            print(body[:800])
    else:
        print("  ", body[:200])

    status, body = call(host, "/api/chat-messages", "POST", {
        "app_id": APP_ID, "query": "HNSW 向量索引的建表语句是什么？",
        "inputs": {}, "response_mode": "blocking", "conversation_id": "",
    })
    print(f"POST /api/chat-messages -> {status}")
    if status == 200:
        try:
            data = json.loads(body)
            answer = data.get("answer", "")
            print("  answer:", answer[:1200].replace("\n", " "))
            print("  six sections:", {k: (k in answer) for k in ("医书摘录", "望闻问切", "药方", "忌口", "养生建议", "医嘱小笺")})
        except Exception:
            print(body[:600])
    else:
        print("  ", body[:300])
