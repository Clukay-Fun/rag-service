"""
文件名: metrics.py
描述: 内置 Prometheus 指标采集与输出。
主要功能:
    - 记录 HTTP 请求量与延迟直方图。
    - 记录文档摄取成功/失败计数与资源数量 Gauge。
    - 输出 Prometheus 文本格式指标。
依赖: 标准库
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Dict, List, Tuple

# ============================================
# region 常量与状态
# ============================================


PROMETHEUS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"
HISTOGRAM_BUCKETS = [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

_lock = Lock()
_http_requests_total: Dict[Tuple[str, str, str], int] = {}
_http_request_duration: Dict[Tuple[str, str], "HistogramState"] = {}
_document_ingestion_total: Dict[str, int] = {}
_knowledge_bases_active = 0
_chunks_total = 0


@dataclass
class HistogramState:
    """直方图状态。"""

    bucket_counts: List[int]
    count: int = 0
    total: float = 0.0

    def observe(self, value: float) -> None:
        """
        记录一次观测值。

        参数:
            value: 观测值。
        """
        self.count += 1
        self.total += value
        for index, bound in enumerate(HISTOGRAM_BUCKETS):
            if value <= bound:
                self.bucket_counts[index] += 1


# endregion
# ============================================

# ============================================
# region 记录接口
# ============================================


def record_http_request(method: str, endpoint: str, status: str, duration_seconds: float) -> None:
    """
    记录 HTTP 请求计数与延迟。

    参数:
        method: HTTP 方法。
        endpoint: 路由模板或路径。
        status: 状态码字符串。
        duration_seconds: 耗时秒数。
    """
    normalized_method = (method or "UNKNOWN").upper()
    normalized_endpoint = endpoint or "unknown"
    normalized_status = status or "0"
    with _lock:
        key = (normalized_method, normalized_endpoint, normalized_status)
        _http_requests_total[key] = _http_requests_total.get(key, 0) + 1
        hist_key = (normalized_method, normalized_endpoint)
        state = _http_request_duration.get(hist_key)
        if state is None:
            state = HistogramState(bucket_counts=[0 for _ in HISTOGRAM_BUCKETS])
            _http_request_duration[hist_key] = state
        state.observe(max(duration_seconds, 0.0))


def record_document_ingestion(status: str) -> None:
    """
    记录文档摄取结果计数。

    参数:
        status: 摄取状态（completed/failed）。
    """
    normalized_status = status or "unknown"
    with _lock:
        _document_ingestion_total[normalized_status] = _document_ingestion_total.get(normalized_status, 0) + 1


def set_active_knowledge_bases(count: int) -> None:
    """
    设置活跃知识库数量。

    参数:
        count: 活跃知识库数量。
    """
    with _lock:
        global _knowledge_bases_active
        _knowledge_bases_active = max(count, 0)


def set_chunks_total(count: int) -> None:
    """
    设置向量分块总数。

    参数:
        count: 分块总数。
    """
    with _lock:
        global _chunks_total
        _chunks_total = max(count, 0)


# endregion
# ============================================

# ============================================
# region Prometheus 文本输出
# ============================================


def _escape_label(value: str) -> str:
    """
    转义 Prometheus 标签值。

    参数:
        value: 原始标签值。
    返回:
        转义后的标签值。
    """
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _format_labels(labels: Dict[str, str]) -> str:
    """
    格式化标签字典为 Prometheus 标签串。

    参数:
        labels: 标签字典。
    返回:
        格式化标签串。
    """
    if not labels:
        return ""
    parts = [f'{key}="{_escape_label(labels[key])}"' for key in sorted(labels.keys())]
    return "{" + ",".join(parts) + "}"


def format_metrics() -> str:
    """
    生成 Prometheus 文本格式指标。

    返回:
        Prometheus 文本格式字符串。
    """
    with _lock:
        http_requests_total = dict(_http_requests_total)
        http_request_duration = {
            key: HistogramState(bucket_counts=list(state.bucket_counts), count=state.count, total=state.total)
            for key, state in _http_request_duration.items()
        }
        document_ingestion_total = dict(_document_ingestion_total)
        knowledge_bases_active = _knowledge_bases_active
        chunks_total = _chunks_total

    lines: List[str] = []

    # http_requests_total
    lines.append("# HELP http_requests_total HTTP 请求计数")
    lines.append("# TYPE http_requests_total counter")
    for key in sorted(http_requests_total.keys()):
        method, endpoint, status = key
        labels = _format_labels({"method": method, "endpoint": endpoint, "status": status})
        lines.append(f"http_requests_total{labels} {http_requests_total[key]}")

    # http_request_duration_seconds
    lines.append("# HELP http_request_duration_seconds HTTP 请求耗时分布")
    lines.append("# TYPE http_request_duration_seconds histogram")
    for key in sorted(http_request_duration.keys()):
        method, endpoint = key
        state = http_request_duration[key]
        for bound, count in zip(HISTOGRAM_BUCKETS, state.bucket_counts):
            labels = _format_labels(
                {"method": method, "endpoint": endpoint, "le": f"{bound:.2f}".rstrip("0").rstrip(".")}
            )
            lines.append(f"http_request_duration_seconds_bucket{labels} {count}")
        labels = _format_labels({"method": method, "endpoint": endpoint, "le": "+Inf"})
        lines.append(f"http_request_duration_seconds_bucket{labels} {state.count}")
        labels = _format_labels({"method": method, "endpoint": endpoint})
        lines.append(f"http_request_duration_seconds_sum{labels} {state.total:.6f}")
        lines.append(f"http_request_duration_seconds_count{labels} {state.count}")

    # document_ingestion_total
    lines.append("# HELP document_ingestion_total 文档摄取计数")
    lines.append("# TYPE document_ingestion_total counter")
    for status in sorted(document_ingestion_total.keys()):
        labels = _format_labels({"status": status})
        lines.append(f"document_ingestion_total{labels} {document_ingestion_total[status]}")

    # knowledge_bases_active
    lines.append("# HELP knowledge_bases_active 活跃知识库数量")
    lines.append("# TYPE knowledge_bases_active gauge")
    lines.append(f"knowledge_bases_active {knowledge_bases_active}")

    # chunks_total
    lines.append("# HELP chunks_total 分块向量总数")
    lines.append("# TYPE chunks_total gauge")
    lines.append(f"chunks_total {chunks_total}")

    return "\n".join(lines) + "\n"


# endregion
# ============================================
