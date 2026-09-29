# services/PrefixConfig.py
"""姓名前缀列表配置：%APPDATA%\\MassSenderPro\\configs\\prefixes.txt，一行一个前缀。"""
import os

from app_paths import config_dir
from services.LineListConfig import LineListConfig

DEFAULT_PREFIXES = ["PY111"]


class PrefixConfig(LineListConfig):
    def __init__(self, path: str = None) -> None:
        if path is None:
            path = os.path.join(config_dir(), "prefixes.txt")
        super().__init__(path, DEFAULT_PREFIXES)
