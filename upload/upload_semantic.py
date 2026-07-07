# -*- coding: utf-8 -*-
"""시맨틱 청킹 결과 → OpenAI 임베딩 → Supabase docs_semantic_v2 업로드"""
import json
from openai import OpenAI
from supabase import create_client

# ===== 설정 (직접 입력) =====
OPENROUTER_API_KEY = "sk-or-..."
SUPABASE_URL   = "https://xxxx.supabase.co"
SUPABASE_KEY   = "eyJ..."

EMBED_MODEL = "openai/text-embedding-3-small"   # OpenRouter 모델명 (접두사 필요)  # 1536차원
TABLE_NAME  = "docs_semantic_v2"
INPUT_PATH  = "../chunking/semantic_chunks.jsonl"
BATCH_SIZE  = 20

# ===== 클라이언트 =====
oai = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)
sb  = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===== 1) 청크 로드 (JSONL: 줄 단위) =====
records = []
with open(INPUT_PATH, "r", encoding="utf-8") as f:
    for line in f:
        records.append(json.loads(line))
print(f"로드된 청크: {len(records)}개")

# ===== 2) 배치 임베딩 + upsert =====
for start in range(0, len(records), BATCH_SIZE):
    batch = records[start:start + BATCH_SIZE]
    texts = [r["text"] for r in batch]

    resp = oai.embeddings.create(model=EMBED_MODEL, input=texts)

    rows = []
    for r, emb in zip(batch, resp.data):
        rows.append({
            "id": r["chunk_id"],
            "content": r["text"],
            "metadata": {"token_count": r["token_count"], "chunking": "semantic"},
            "embedding": emb.embedding,
        })

    sb.table(TABLE_NAME).upsert(rows).execute()
    print(f"업로드: {start + 1} ~ {start + len(batch)}")

# ===== 3) 건수 검증 =====
res = sb.table(TABLE_NAME).select("id", count="exact").execute()
print(f"\n[검증] {TABLE_NAME} 테이블 건수: {res.count} / 원본 청크: {len(records)}")
print("일치" if res.count == len(records) else "불일치 — 확인 필요")