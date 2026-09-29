# models/roster_item.py
"""名册任务条目：一个待发送用户及其消息负载。"""
from dataclasses import dataclass
from typing import List


@dataclass
class RosterItem:
    user_id: str
    payload: List[dict] = None

    def __post_init__(self):
        if self.payload is None:
            self.payload = []
