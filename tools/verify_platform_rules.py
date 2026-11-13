"""Verify the platform's gitRepo validation rule and the submission field names.

We already know from the platform bundle:
  isValidSubmissionLink(M) -> https + hostname + NO username/password
  buildSubmissionFields(M, C) -> { gitRepo, commitId?, branch?, extraParams? }
  isArtifactSubmission(M) / isQoderSiteField(S) -> per-question field shapes

This script:
  1. re-checks the URL rule with our candidate strings;
  2. lists the extra field names the platform expects per question by calling
     submissionOptions (works unauthenticated for the field list).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

API = "https://openwebapi.oceanbase.com"


def check_url(url: str) -> tuple[bool, str]:
    """Mirror the platform's isValidSubmissionLink()."""
    if not isinstance(url, str) or len(url.strip()) > 2048:
        return False, "not a string / too long"
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url.strip())
    except Exception as error:  # noqa: BLE001
        return False, f"unparsable: {error}"
    if parsed.scheme != "https":
        return False, "protocol must be https"
    if not parsed.hostname:
        return False, "hostname required"
    if parsed.username or parsed.password:
        return False, "username/password NOT allowed in the repo URL"
    return True, "ok"


def options(question_id: int) -> object:
    url = f"{API}/api/testplatform/taskrecord/submissionOptions?questionId={question_id}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as error:
        return {"http": error.code, "body": error.read().decode("utf-8", "replace")[:200]}
    except Exception as error:  # noqa: BLE001
        return {"error": f"{type(error).__name__}: {error}"}


CANDIDATES = [
    "https://github.com/tangtang-cx/ai-ecosystem",
    "https://github.com/tangtang-cx/ai-ecosystem.git",
    "https://wzhaihqy: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@github.com/tangtang-cx/ai-ecosystem.git",
]

print("=== repo URL rule (platform's own isValidSubmissionLink) ===")
for candidate in CANDIDATES:
    ok, reason = check_url(candidate)
    shown = candidate if len(candidate) < 70 else candidate[:60] + "..."
    print(f"  {'OK ' if ok else 'BAD'}  {shown}   -> {reason}")

print("\n=== submissionOptions per question ===")
for question_id in (600076, 600077, 600069, 600070, 600072):
    data = options(question_id)
    text = json.dumps(data, ensure_ascii=False)
    print(f"  qid={question_id}: {text[:700]}")
