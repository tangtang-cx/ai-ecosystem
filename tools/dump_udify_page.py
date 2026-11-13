import json
import re
import urllib.request

PAGE = "https://udify.app/chat/CTbEyrNETzo7iVA7"
req = urllib.request.Request(PAGE, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=45) as response:
    html = response.read().decode("utf-8", "replace")

print("len:", len(html))

# collect every JSON-looking blob and look for Dify app fields
blobs = []
for match in re.finditer(r"<script[^>]*>([\s\S]{20,400000}?)</script>", html):
    blobs.append(match.group(1))
print("script blobs:", len(blobs), [len(b) for b in blobs][:10])

interesting = ["opening_statement", "suggested_questions", "site", "app_token", "workflow",
               "app_id", "conversation", "features", "file_upload", "retriever_resource",
               "text_to_speech", "openingStatement", "use_icon_as_answer_icon"]
for blob in blobs:
    for key in interesting:
        if key in blob:
            index = blob.find(key)
            print(f"\n--- found {key!r} in a blob ---")
            print(blob[max(0, index - 200): index + 900][:1200])
            break

# also dump any inline __NEXT_DATA__ / __NUXT__ style payload
for pattern in (r"__NEXT_DATA__[^>]*>([\s\S]{50,200000})<", r"window\.__NUXT__[^=]*=\s*(\{[\s\S]{50,200000})"):
    hit = re.search(pattern, html)
    if hit:
        print("\n=== embedded payload found ===")
        print(hit.group(1)[:1500])
        break

# list any api endpoints referenced
print("\napi paths referenced:", sorted(set(re.findall(r"/api/[A-Za-z0-9/_\-\.]+", html)))[:20])
print("chat-api refs:", sorted(set(re.findall(r"/chat-api/[A-Za-z0-9/_\-\.]+", html)))[:20])
