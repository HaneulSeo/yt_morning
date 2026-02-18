from __future__ import annotations

import json as jsonlib
import urllib.error
import urllib.parse
import urllib.request


class HTTPError(Exception):
    pass


class Response:
    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self._body = body

    def json(self):
        return jsonlib.loads(self._body.decode("utf-8") or "{}")

    @property
    def text(self) -> str:
        return self._body.decode("utf-8", errors="replace")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError(f"HTTP {self.status_code}: {self.text}")


class Session:
    def request(self, method, url, headers=None, params=None, json=None, timeout=30):
        if params:
            q = urllib.parse.urlencode(params)
            url = f"{url}{'&' if '?' in url else '?'}{q}"
        data = None
        req_headers = headers or {}
        if json is not None:
            data = jsonlib.dumps(json).encode("utf-8")
            req_headers = {**req_headers, "Content-Type": "application/json"}
        req = urllib.request.Request(url=url, method=method, data=data, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return Response(resp.status, resp.read())
        except urllib.error.HTTPError as exc:
            return Response(exc.code, exc.read())

    def get(self, url, params=None, timeout=30):
        return self.request("GET", url, params=params, timeout=timeout)

    def post(self, url, params=None, json=None, timeout=30):
        if params:
            q = urllib.parse.urlencode(params)
            url = f"{url}{'&' if '?' in url else '?'}{q}"
        return self.request("POST", url, json=json, timeout=timeout)
