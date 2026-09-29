# services/SkipKeywordConfig.py
"""跳过关键字配置：备注包含任一关键字则不发送。

数据存在 %APPDATA%\\MassSenderPro\\configs\\skip_keywords.txt，一行一个关键字。
"""
import os

from app_paths import config_dir
from services.LineListConfig import LineListConfig

# 与历史版本保持一致的默认关键字（文件不存在时写入）
DEFAULT_KEYWORDS = ["不催", "请假", "异动", "冻结", "转班", "退课"]


class SkipKeywordConfig(LineListConfig):
    def __init__(self, path: str = None) -> None:
        if path is None:
            path = os.path.join(config_dir(), "skip_keywords.txt")
        super().__init__(path, DEFAULT_KEYWORDS)
