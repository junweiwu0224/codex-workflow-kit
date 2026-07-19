"""Deliberately vulnerable sample for a read-only security-review exercise."""

import json
from urllib.request import Request, urlopen


def process_webhook(raw_body: bytes) -> int:
    event = json.loads(raw_body)
    callback_url = event["callback_url"]
    request = Request(callback_url, data=b'{"delivery":"complete"}', method="POST")
    with urlopen(request, timeout=3) as response:
        return response.status
