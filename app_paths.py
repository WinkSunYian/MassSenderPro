# app_paths.py
"""应用数据目录：配置 / 日志放 %APPDATA%\\MassSenderPro。

只负责算路径（不迁移、不建目录——目录在真正写文件时随写随建）：
- 可写数据 configs / logs → %APPDATA%\\MassSenderPro\\
- 只读资源 resources → 仓库根 / PyInstaller 包目录（sys._MEIPASS）
"""
import os
import sys

APP_NAME = "MassSenderPro"


def is_frozen() -> bool:
    """是否运行在 PyInstaller 打包产物里。"""
    return bool(getattr(sys, "frozen", False))


def project_root() -> str:
    """只读资源根：源码 = 仓库根；打包 = _internal（onefile 为临时解包目录）。"""
    if is_frozen():
        return getattr(sys, "_MEIPASS", None) or os.path.dirname(
            os.path.abspath(sys.executable)
        )
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(*parts: str) -> str:
    """只读资源路径（打包后指到包内 _internal，源码运行指到仓库根）。"""
    return os.path.join(project_root(), *parts)


def appdata_dir() -> str:
    """%APPDATA%\\MassSenderPro"""
    base = os.environ.get("APPDATA") or os.path.join(
        os.path.expanduser("~"), "AppData", "Roaming"
    )
    return os.path.join(base, APP_NAME)


def config_dir() -> str:
    """%APPDATA%\\MassSenderPro\\configs"""
    return os.path.join(appdata_dir(), "configs")


def logs_dir() -> str:
    """%APPDATA%\\MassSenderPro\\logs"""
    return os.path.join(appdata_dir(), "logs")
