import json
import re
import urllib.error
import urllib.request

BASE = "https://udify.app"
TOKEN = "CTbEyrNETzo7iVA7"
PAGE = f"{BASE}/chat/{TOKEN}"

print("== page ==")
try:
    req = urllib.request.Request(PAGE, headers={"User-Agent": "Mozilla/5.0 (opencode-check)"})
    with urllib.request.urlopen(req, timeout=45) as response:
        html = response.read().decode("utf-8", "replace")
        print("HTTP", response.status, "| len", len(html))
except urllib.error.HTTPError as error:
    html = ""
    print("HTTP", error.code, error.reason)
except Exception as error:
    html = ""
    print("ERR", error)

if html:
    title = re.search(r"<title[^>]*>([^<]*)</title>", html)
    print("title:", title.group(1) if title else "?")
    for marker in ("dify", "Dify", "chat-messages", "conversation", "workflow", "appId",
                   "SQL", "老中医", "医书", "OB-0", "seekdb", "六段", "药方", "忌口"):
        print(f"  contains {marker!r}: {marker in html}")
    ids = sorted(set(re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", html)))
    print("  uuids in page:", len(ids), ids[:4])

print("\n== chat api probes ==")
for path, body in (
    (f"/chat-api/{TOKEN}/chat-messages", {"query": "ping", "inputs": {}, "response_mode": "blocking"}),
    (f"/chat-api/{TOKEN}/messages", None),
):
    try:
        data = json.dumps(body).encode() if body else b"{}"
        req = urllib.request.Request(
            BASE + path,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "opencode-check"},
        )
        with urllib.request.urlopen(req, timeout=45) as response:
            print(f"  POST {path} -> HTTP {response.status} {response.read()[:200]!r}")
    except urllib.error.HTTPError as error:
        detail = error.read()[:200].decode("utf-8", "replace")
        print(f"  POST {path} -> HTTP {error.code} {detail!r}")
    except Exception as error:
        print(f"  POST {path} -> {type(error).__name__}: {error}")

for path in ("/console/api/system-features", "/api/system-features", "/v1/parameters", "/health"):
    try:
        req = urllib.request.Request(BASE + path, headers={"User-Agent": "opencode-check"})
        with urllib.request.urlopen(req, timeout=25) as response:
            print(f"  GET {path} -> HTTP {response.status}")
    except urllib.error.HTTPError as error:
        print(f"  GET {path} -> HTTP {error.code}")
    except Exception as error:
        print(f"  GET {path} -> {type(error).__name__}")
