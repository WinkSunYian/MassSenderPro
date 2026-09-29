import os
from typing import List

from models.roster_item import RosterItem


def _pandas():
    """按需导入 pandas：只有读取 Excel/CSV 名册时才需要。"""
    import pandas as pd

    return pd


class RosterServiceImpl:
    def __init__(self, rosters_dir: str = None, logs_dir: str = None):
        self.rosters_dir = rosters_dir or ""
        self.logs_dir = logs_dir or ""

    def load_from_excel(self, path: str, payload: list = None) -> List[RosterItem]:
        pd = _pandas()
        file_path = self._resolve(path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Excel 名册文件不存在: {file_path}")

        df = pd.read_excel(file_path, header=None, dtype=str)
        items: List[RosterItem] = []
        for _, row in df.iterrows():
            user_id = str(row.iloc[0]).strip()
            if not user_id or user_id.lower() in [
                "user_id", "用户id", "账号", "姓名", "roster",
            ]:
                continue
            row_payload = []
            for cell in row.iloc[1:]:
                if pd.isna(cell):
                    continue
                s = str(cell).strip()
                if not s:
                    continue
                if os.path.exists(s):
                    row_payload.append({"type": "file", "data": s})
                else:
                    row_payload.append({"type": "text", "data": s})
            items.append(RosterItem(user_id=user_id, payload=row_payload or payload or []))
        return items

    def load_from_txt(self, path: str, payload: list = None) -> List[RosterItem]:
        file_path = self._resolve(path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"TXT 名册文件不存在: {file_path}")

        users = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                uid = line.strip()
                if uid:
                    users.append(uid)

        items_payload = payload if payload is not None else []
        return [RosterItem(user_id=u, payload=items_payload) for u in users]

    def load_from_csv(self, path: str, payload: list = None) -> List[RosterItem]:
        pd = _pandas()
        file_path = self._resolve(path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV 名册文件不存在: {file_path}")

        df = pd.read_csv(file_path, header=None, dtype=str)
        items: List[RosterItem] = []
        for _, row in df.iterrows():
            user_id = str(row.iloc[0]).strip()
            if not user_id or user_id.lower() in [
                "user_id", "用户id", "账号", "姓名", "roster",
            ]:
                continue
            row_payload = []
            for cell in row.iloc[1:]:
                if pd.isna(cell):
                    continue
                s = str(cell).strip()
                if not s:
                    continue
                if os.path.exists(s):
                    row_payload.append({"type": "file", "data": s})
                else:
                    row_payload.append({"type": "text", "data": s})
            items.append(RosterItem(user_id=user_id, payload=row_payload or payload or []))
        return items

    def save_failed_roster(self, failed: List[str]):
        if not self.logs_dir:
            return
        os.makedirs(self.logs_dir, exist_ok=True)
        with open(
            os.path.join(self.logs_dir, "failed_roster.txt"), "w", encoding="utf-8"
        ) as f:
            for uid in failed:
                f.write(uid + "\n")

    def _resolve(self, path_or_name: str) -> str:
        if self.rosters_dir and not os.path.isabs(path_or_name):
            return os.path.join(self.rosters_dir, path_or_name)
        return path_or_name