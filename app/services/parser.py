"""
文件名: parser.py
描述: 文档解析工具，提供最简文本提取。
主要功能:
    - 解析字符串（去除首尾空白）
    - 简单文件解析：仅支持 .txt / .md，其他类型返回空
依赖: pathlib
"""

from pathlib import Path
from typing import Optional


def parse_text(content: str) -> str:
    """对原始字符串做基础清洗。"""
    return (content or "").strip()


def parse_file(file_path: str) -> Optional[str]:
    """
    解析文件为文本。

    仅支持 .txt / .md；其他类型返回 None。
    """
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return None
    if path.suffix.lower() not in {".txt", ".md"}:
        return None
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return None
