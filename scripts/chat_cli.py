"""
简单终端聊天 CLI，模拟流式输出：
1) 先打印“正在查询结果...”
2) 显示最终返回内容
使用 /api/v1/chat 接口。
"""

import argparse
import sys

import httpx


# ============================================
# region CLI
# ============================================
def chat_once(base_url: str, message: str) -> None:
    print("正在查询结果...")
    url = f"{base_url.rstrip('/')}/api/v1/chat/"
    try:
        resp = httpx.post(
            url,
            json={"message": message},
            timeout=30.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"输出：{data.get('message', '')}")
    except Exception as exc:
        print(f"调用失败：{exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="终端聊天 CLI")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8001",
        help="后端服务地址（默认 http://127.0.0.1:8001）",
    )
    args = parser.parse_args()

    print("输入内容回车发送，输入 exit 退出。")
    for line in sys.stdin:
        message = line.strip()
        if not message:
            continue
        if message.lower() in {"exit", "quit"}:
            break
        chat_once(args.base_url, message)
# endregion
# ============================================


if __name__ == "__main__":
    main()
