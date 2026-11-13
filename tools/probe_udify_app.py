import json
import re
import urllib.error
import urllib.request

BASE = "https://udify.app"
TOKEN = "CTbEyrNETzo7iVA7"
UA = {"User-Agent": "Mozilla/5.0 (opencode-check)", "Accept": "application/json"}


def get(path):
    try:
        req = urllib.request.Request(BASE + path, headers=UA)
        with urllib.request.urlopen(req, timeout=40) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")[:200]
    except Exception as error:
        return 0, f"{type(error).__name__}: {error}"


def post(path, payload):
    try:
        req = urllib.request.Request(
            BASE + path,
            data=json.dumps(payload).encode(),
            method="POST",
            headers={"Content-Type": "application/json", **UA},
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")[:400]
    except Exception as error:
        return 0, f"{type(error).__name__}: {error}"


page_req = urllib.request.Request(f"{BASE}/chat/{TOKEN}", headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(page_req, timeout=45) as response:
    html = response.read().decode("utf-8", "replace")
uuids = sorted(set(re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", html)))
app_id = uuids[0] if uuids else ""
print("app_id:", app_id)

for path in (
    f"/api/parameters?app_id={app_id}",
    f"/api/meta?app_id={app_id}&conversation_id=probe",
    f"/api/apps/{app_id}/parameters",
    f"/api/site/{TOKEN}",
):
    status, body = get(path)
    print(f"\nGET {path[:70]} -> {status}")
    if status == 200:
        try:
            data = json.loads(body)
            pretty = json.dumps(data, ensure_ascii=False, indent=2)
            print(pretty[:1800])
        except Exception:
            print(body[:600])

status, body = post(
    "/api/chat-messages",
    {"app_id": app_id, "query": "HNSW 向量索引的建表语句是什么？", "inputs": {},
     "response_mode": "blocking", "conversation_id": ""},
)
print(f"\nPOST /api/chat-messages -> {status}")
print(body[:2500])
