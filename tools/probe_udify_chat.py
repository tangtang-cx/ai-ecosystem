import json
import urllib.error
import urllib.request

BASE = "https://udify.app"
TOKEN = "CTbEyrNETzo7iVA7"
APP_ID = "6d6a7cea-15e5-43a0-a9c6-54a13816ef30"
PAYLOAD = {
    "app_id": APP_ID,
    "query": "HNSW 向量索引的建表语句是什么？",
    "inputs": {},
    "response_mode": "blocking",
    "conversation_id": "",
}


def attempt(label, path, headers=None, payload=None):
    try:
        req = urllib.request.Request(
            BASE + path,
            data=json.dumps(payload or PAYLOAD).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json",
                     "User-Agent": "Mozilla/5.0", **(headers or {})},
        )
        with urllib.request.urlopen(req, timeout=90) as response:
            body = response.read().decode("utf-8", "replace")
            print(f"[{label}] HTTP {response.status}")
            try:
                data = json.loads(body)
                answer = data.get("answer", "")
                print("    answer head:", answer[:900].replace("\n", " "))
                print("    has six sections:", {k: (k in answer) for k in ("医书摘录", "望闻问切", "药方", "忌口", "养生建议", "医嘱小笺")})
                return True
            except Exception:
                print("    raw:", body[:400])
                return False
    except urllib.error.HTTPError as error:
        print(f"[{label}] HTTP {error.code} {error.read()[:160].decode('utf-8','replace')}")
    except Exception as error:
        print(f"[{label}] {type(error).__name__}: {error}")
    return False


attempt("query token", f"/api/chat-messages?token={TOKEN}")
attempt("query app_token", f"/api/chat-messages?app_token={TOKEN}")
attempt("bearer header", "/api/chat-messages", {"Authorization": f"Bearer {TOKEN}"})
attempt("x-app-token header", "/api/chat-messages", {"X-App-Token": TOKEN})
attempt("both", f"/api/chat-messages?token={TOKEN}", {"Authorization": f"Bearer {TOKEN}"})
