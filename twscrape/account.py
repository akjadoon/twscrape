import json
import os
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime

from httpx import AsyncClient, AsyncHTTPTransport

from .models import JSONTrait
from .utils import utc

TOKEN = "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"


@dataclass
class Account(JSONTrait):
    username: str
    password: str
    email: str
    email_password: str
    user_agent: str
    active: bool
    locks: dict[str, datetime] = field(default_factory=dict)  # queue: datetime
    stats: dict[str, int] = field(default_factory=dict)  # queue: requests
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    mfa_code: str | None = None
    proxy: str | None = None
    error_msg: str | None = None
    last_used: datetime | None = None
    _tx: str | None = None

    @staticmethod
    def from_rs(rs: sqlite3.Row):
        doc = dict(rs)
        doc["locks"] = {k: utc.from_iso(v) for k, v in json.loads(doc["locks"]).items()}
        doc["stats"] = {k: v for k, v in json.loads(doc["stats"]).items() if isinstance(v, int)}
        doc["headers"] = json.loads(doc["headers"])
        doc["cookies"] = json.loads(doc["cookies"])
        doc["active"] = bool(doc["active"])
        doc["last_used"] = utc.from_iso(doc["last_used"]) if doc["last_used"] else None
        return Account(**doc)

    def to_rs(self):
        rs = asdict(self)
        rs["locks"] = json.dumps(rs["locks"], default=lambda x: x.isoformat())
        rs["stats"] = json.dumps(rs["stats"])
        rs["headers"] = json.dumps(rs["headers"])
        rs["cookies"] = json.dumps(rs["cookies"])
        rs["last_used"] = rs["last_used"].isoformat() if rs["last_used"] else None
        return rs

    def make_client(self, proxy: str | None = None) -> AsyncClient:
        proxies = [proxy, os.getenv("TWS_PROXY"), self.proxy]
        proxies = [x for x in proxies if x is not None]
        proxy = proxies[0] if proxies else None

        transport = AsyncHTTPTransport(retries=2)
        client = AsyncClient(proxy=proxy, follow_redirects=True, transport=transport)

        # saved from previous usage
        client.cookies.update(self.cookies)
        client.headers.update(self.headers)

        # default settings
        client.headers["user-agent"] = self.user_agent
        client.headers["content-type"] = "application/json"
        client.headers["authorization"] = TOKEN
        client.headers["X-Twitter-Active-User"] = "yes"
        client.headers["X-Twitter-Client-Language"] = "en"
        client.headers["X-Client-Transaction-Id"] = "eD0hCT0DlVck/2twHEDA7l98KItZFCoyyCupbVx6wj6VR9BhPZKCdkjwidakXFgDXLCGC3o4WNhc3Fws0iWAO2X7LZsUew"
        client.headers["X-Twitter-Auth-Type"] = "OAuth2Session"
        # client.headers["X-Client-UUID":] = "648945bf-7ca2-4326-a4e9-cb4cbba2f99b"
        if "ct0" in client.cookies:
            client.headers["x-csrf-token"] = client.cookies["ct0"]
        print("twscrape-log:", "req with headers", client.headers, client.headers.multi_items())
        return client
