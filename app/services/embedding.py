"""
向量嵌入服务
调用 SiliconFlow API 生成文本向量
"""

from typing import List, Optional
import httpx

from app.config import (
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    EMBEDDING_MODEL,
)


# ============================================
# region 单条向量生成
# ============================================

def get_embedding(text: str) -> Optional[List[float]]:
    """
    生成单条文本的向量嵌入
    
    参数:
        text: 待向量化的文本
    
    返回:
        向量列表，失败返回 None
    """
    if not text or not text.strip():
        return None
    
    try:
        response = httpx.post(
            f"{SILICONFLOW_BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": text,
                "encoding_format": "float"
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["data"][0]["embedding"]
        else:
            print(f"❌ Embedding API 错误: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 获取向量失败: {e}")
        return None

# endregion
# ============================================


# ============================================
# region 批量向量生成
# ============================================

def get_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """
    批量生成文本向量（提高效率）
    
    参数:
        texts: 文本列表
    
    返回:
        对应的向量列表
    """
    if not texts:
        return []
    
    # 过滤空文本
    valid_texts = [t if t and t.strip() else "" for t in texts]
    
    try:
        response = httpx.post(
            f"{SILICONFLOW_BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": valid_texts,
                "encoding_format": "float"
            },
            timeout=60.0
        )
        
        if response.status_code == 200:
            result = response.json()
            # 按 index 排序确保顺序正确
            data = sorted(result["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in data]
        else:
            print(f"❌ Batch Embedding 错误: {response.status_code}")
            return [None] * len(texts)
            
    except Exception as e:
        print(f"❌ 批量获取向量失败: {e}")
        return [None] * len(texts)

# endregion
# ============================================
