# services/LineListConfig.py
"""一行一项的文本配置基类（UTF-8；缺失时按默认值创建；空行忽略、去重保序）。"""
import os
from typing import Iterable, List


class LineListConfig:
    def __init__(self, path: str, defaults: Iterable[str]) -> None:
        self.path = path
        self.defaults = list(defaults)

    def load(self) -> List[str]:
        if not os.path.exists(self.path):
            self.save(self.defaults)
            return list(self.defaults)
        try:
            # utf-8-sig：兼容带 BOM 的文件（如记事本另存），无 BOM 文件行为不变
            with open(self.path, "r", encoding="utf-8-sig") as f:
                items = [line.strip() for line in f]
        except OSError:
            return list(self.defaults)
        return self._dedupe(items)

    def save(self, items: Iterable[str]) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            for item in self._dedupe(items):
                f.write(item + "\n")

    @staticmethod
    def _dedupe(items: Iterable[str]) -> List[str]:
        seen, result = set(), []
        for item in items:
            item = (item or "").strip()
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result
