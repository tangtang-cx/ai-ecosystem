import asyncio
import json
import urllib.request

BASE = "https://sql-review-assistant-8ptbxy0nhc9.qoder.zone/"


def head():
    req = urllib.request.Request(BASE, headers={"User-Agent": "opencode-check"})
    with urllib.request.urlopen(req, timeout=40) as response:
        body = response.read().decode("utf-8", "replace")
        return response.status, response.headers.get("content-type", ""), body


status, ctype, body = head()
print("HTTP", status, "| content-type:", ctype)
print("title:", body.split("<title>")[1].split("</title>")[0] if "<title>" in body else "?")

# Streamlit exposes a websocket endpoint; a missing st-websocket means it is not a
# live Streamlit server (e.g. a static mirror of the page).
print("has _stcore/health ref:", "_stcore/health" in body)
print("has st-websocket marker:", "st-websocket" in body or "websocket" in body.lower())

for probe in ("/_stcore/health", "/healthz", "/_stcore/host-config"):
    try:
        req = urllib.request.Request(BASE.rstrip("/") + probe, headers={"User-Agent": "opencode-check"})
        with urllib.request.urlopen(req, timeout=25) as response:
            data = response.read()[:200].decode("utf-8", "replace")
            print(f"{probe} -> HTTP {response.status} {data[:120]!r}")
    except Exception as error:
        print(f"{probe} -> {type(error).__name__}: {error}")
