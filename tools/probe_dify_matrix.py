import json
import urllib.error
import urllib.request

HOST = "https://cloud.dify.ai"
TOKEN = "CTbEyrNETzo7iVA7"
APP_ID = "6d6a7cea-15e5-43a0-a9c6-54a13816ef30"

PREFIXES = ["/api", "/console/api", "/v1"]
TOKEN_CARRIERS = [
    ("header X-App-Token", {"X-App-Token": TOKEN}, ""),
    ("header Authorization", {"Authorization": f"Bearer {TOKEN}"}, ""),
    ("query token", {}, f"?token={TOKEN}"),
    ("query app_token", {}, f"?app_token={TOKEN}"),
    ("header+query", {"X-App-Token": TOKEN}, f"?token={TOKEN}"),
]


def call(path, method="GET", payload=None, headers=None):
    url = HOST + path
    base = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "Mozilla/5.0"}
    base.update(headers or {})
    data = json.dumps(payload).encode() if payload is not None else None
    try:
        req = urllib.request.Request(url, data=data, method=method, headers=base)
        with urllib.request.urlopen(req, timeout=90) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")[:200]
    except Exception as error:
        return 0, f"{type(error).__name__}: {error}"


for prefix in PREFIXES:
    for label, headers, query in TOKEN_CARRIERS:
        path = f"{prefix}/parameters?app_id={APP_ID}{query}"
        status, body = call(path, headers=headers)
        marker = "  <<< WORKS" if status == 200 else ""
        snippet = ""
        if status == 200:
            try:
                data = json.loads(body)
                snippet = " | opening_statement=" + str(data.get("opening_statement"))[:120]
            except Exception:
                snippet = body[:120]
        else:
            snippet = body[:90]
        print(f"{prefix:14} {label:22} -> {status}{marker} {snippet}")
        if status == 200:
            break
    else:
        continue
    break
