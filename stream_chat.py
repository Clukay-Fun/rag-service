# stream_chat.py
"""
用途: 测试 SSE 流式对话接口
运行: python stream_chat.py
"""

import json
import httpx

# 接口地址
URL = "http://127.0.0.1:8000/chat/stream"

# 请求数据（中文示例）
payload = {
    "query": "合同",
    "knowledge_base_id": 1,
    "top_k": 3,
}

def main() -> None:
    """发起 SSE 请求并打印流式输出。"""
    with httpx.Client(timeout=None) as client:
        with client.stream("POST", URL, json=payload) as response:
            response.raise_for_status()
            # SSE 按行输出（包含 event/data）
            for line in response.iter_lines():
                if not line:
                    continue
                print(line)

if __name__ == "__main__":
    main()
