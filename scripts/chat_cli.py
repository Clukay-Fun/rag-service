"""
文件名: chat_cli.py
描述: 终端 CLI，便于本地测试 /api/v1/chat 与 /api/v1/search 接口。
主要功能:
    - 发送聊天请求，查看技能路由输出
    - 发送搜索请求，验证 RAG 检索结果
    - 批量索引简单文档，便于快速造数
依赖: httpx, argparse
"""

import argparse
import sys
from typing import List

import httpx


def _call_api(method: str, url: str, **kwargs):
    resp = httpx.request(method, url, timeout=30.0, follow_redirects=True, **kwargs)
    resp.raise_for_status()
    return resp.json()


def chat_once(base_url: str, message: str) -> None:
    """调用 /api/v1/chat/"""
    url = f"{base_url.rstrip('/')}/api/v1/chat/"
    data = _call_api("POST", url, json={"message": message})
    print(f"[skill:{data.get('skill_used')}] {data.get('message')}")


def search_once(base_url: str, query: str, collection: str, top_k: int, use_rerank: bool) -> None:
    """调用 /api/v1/search/"""
    url = f"{base_url.rstrip('/')}/api/v1/search/"
    payload = {
        "query": query,
        "collection": collection,
        "top_k": top_k,
        "use_rerank": use_rerank,
    }
    data = _call_api("POST", url, json=payload)
    print(f"query='{data['query']}', count={data['count']}")
    for i, item in enumerate(data.get("results", []), 1):
        print(f"{i}. [sim={item['similarity']}] {item['content'][:120]}")


def index_docs(base_url: str, collection: str, docs: List[str]) -> None:
    """调用 /api/v1/search/index，批量索引简单文档。"""
    url = f"{base_url.rstrip('/')}/api/v1/search/index"
    payload = {
        "collection": collection,
        "documents": [{"content": text} for text in docs],
    }
    data = _call_api("POST", url, json=payload)
    print(f"indexed={data['indexed']}, failed={data['failed']}, collection={data['collection']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG Service CLI")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001", help="后端服务地址")
    sub = parser.add_subparsers(dest="cmd", required=True)

    chat_p = sub.add_parser("chat", help="聊天模式，测试技能路由")
    chat_p.add_argument("--message", help="单次发送的消息；不填则进入交互输入")

    search_p = sub.add_parser("search", help="搜索模式，测试 RAG 检索")
    search_p.add_argument("--query", required=True, help="查询文本")
    search_p.add_argument("--collection", required=True, help="集合名")
    search_p.add_argument("--top-k", type=int, default=5, help="返回数量")
    search_p.add_argument("--no-rerank", action="store_true", help="关闭 rerank")

    index_p = sub.add_parser("index", help="索引模式，快速写入文档")
    index_p.add_argument("--collection", required=True, help="集合名")
    index_p.add_argument(
        "--doc",
        action="append",
        required=True,
        help="要写入的文档内容，可重复传多次",
    )

    args = parser.parse_args()
    base_url = args.base_url

    try:
        if args.cmd == "chat":
            if args.message:
                chat_once(base_url, args.message)
            else:
                print("输入内容回车发送，exit/quit 退出。")
                for line in sys.stdin:
                    msg = line.strip()
                    if not msg:
                        continue
                    if msg.lower() in {"exit", "quit"}:
                        break
                    chat_once(base_url, msg)
        elif args.cmd == "search":
            search_once(
                base_url=base_url,
                query=args.query,
                collection=args.collection,
                top_k=args.top_k,
                use_rerank=not args.no_rerank,
            )
        elif args.cmd == "index":
            index_docs(base_url=base_url, collection=args.collection, docs=args.doc)
    except httpx.HTTPStatusError as exc:
        print(f"[HTTP {exc.response.status_code}] {exc.response.text}")
    except Exception as exc:  # pragma: no cover - CLI 调用打印即可
        print(f"调用失败: {exc}")


if __name__ == "__main__":
    main()
