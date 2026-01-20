"""
文件名: parser.py
描述: 文档解析服务（转为 Markdown/纯文本）。
主要功能:
    - 解析文本/Markdown/HTML/图片等文件内容。
    - 生成统一的解析结果与元数据。
依赖: 标准库, FastAPI
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Callable, Dict, Optional

from app.errors import AppError, ErrorDetail

# ============================================
# region 数据结构
# ============================================


@dataclass(frozen=True)
class ParsedDocument:
    """解析后的文档结果。"""

    text: str
    metadata: Dict[str, Any]


# endregion
# ============================================

# ============================================
# region HTML 解析
# ============================================


class _HTMLTextExtractor(HTMLParser):
    """简单 HTML 文本提取器。"""

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self._chunks.append(data.strip())

    def get_text(self) -> str:
        return "\n".join(self._chunks)


def _html_to_text(content: str) -> str:
    """
    将 HTML 转换为纯文本。

    参数:
        content: HTML 字符串。
    返回:
        提取后的纯文本。
    """
    parser = _HTMLTextExtractor()
    parser.feed(content)
    return parser.get_text()


# endregion
# ============================================

# ============================================
# region 解析逻辑
# ============================================


SUPPORTED_TEXT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/html",
}

IMAGE_TYPES = {"image/png", "image/jpeg"}

DOC_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".pptx",
}


def _decode_bytes(data: bytes) -> str:
    """
    尝试解码文本内容。

    参数:
        data: 原始字节数据。
    返回:
        解码后的字符串。
    """
    for encoding in ("utf-8", "utf-16", "gb18030", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def parse_document(
    *,
    filename: str,
    content_type: str,
    content: bytes,
    ocr_handler: Optional[Callable[[bytes], str]] = None,
) -> ParsedDocument:
    """
    解析文档内容，返回 Markdown/文本与元数据。

    参数:
        filename: 文件名。
        content_type: 文件类型。
        content: 文件内容字节。
        ocr_handler: OCR 处理函数（图片专用）。
    返回:
        ParsedDocument 对象。
    """
    ext = os.path.splitext(filename.lower())[1]

    if content_type in SUPPORTED_TEXT_TYPES or ext in {".txt", ".md", ".markdown", ".html", ".htm"}:
        text = _decode_bytes(content)
        if content_type == "text/html" or ext in {".html", ".htm"}:
            text = _html_to_text(text)
        return ParsedDocument(
            text=text,
            metadata={"filename": filename, "page_range": None, "ocr_skipped": False},
        )

    if content_type in IMAGE_TYPES or ext in {".png", ".jpg", ".jpeg"}:
        if ocr_handler is None:
            return ParsedDocument(
                text="",
                metadata={"filename": filename, "page_range": None, "ocr_skipped": True},
            )
        ocr_text = ocr_handler(content)
        return ParsedDocument(
            text=ocr_text,
            metadata={"filename": filename, "page_range": None, "ocr_skipped": False},
        )

    if ext in DOC_EXTENSIONS:
        try:
            from markitdown import MarkItDown
        except ImportError as exc:
            raise AppError(
                status_code=500,
                code="INTERNAL_ERROR",
                message="文档解析组件未安装",
                details=[ErrorDetail(field="file", code="PARSER_MISSING", message=str(exc))],
            ) from exc

        converter = MarkItDown()
        with io.BytesIO(content) as stream:
            result = converter.convert(stream, filename=filename)
        return ParsedDocument(
            text=result.text_content,
            metadata={"filename": filename, "page_range": None, "ocr_skipped": False},
        )

    raise AppError(
        status_code=415,
        code="UNSUPPORTED_MEDIA_TYPE",
        message="不支持的文件格式",
        details=[ErrorDetail(field="file", code="UNSUPPORTED", message="文件格式不被支持")],
    )


# endregion
# ============================================
