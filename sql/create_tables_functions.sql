-- ============================================
-- RAG 비교 과제용 테이블 + 검색 함수 (v2)
-- ============================================

-- 0) pgvector 확장 활성화 (이미 있으면 무시됨)
create extension if not exists vector;

-- 1) 시맨틱 청킹 테이블
create table docs_semantic_v2 (
  id bigint primary key,
  content text,
  metadata jsonb,
  embedding vector(1536)
);

-- 2) 계층형 청킹 테이블
create table docs_hier_v2 (
  id bigint primary key,
  content text,
  metadata jsonb,
  embedding vector(1536)
);

-- 3) 시맨틱 테이블 검색 함수 (코사인 유사도)
create or replace function match_docs_semantic_v2 (
  query_embedding vector(1536),
  match_count int default 5
)
returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    id,
    content,
    metadata,
    1 - (embedding <=> query_embedding) as similarity
  from docs_semantic_v2
  order by embedding <=> query_embedding
  limit match_count;
$$;

-- 4) 계층형 테이블 검색 함수 (코사인 유사도)
create or replace function match_docs_hier_v2 (
  query_embedding vector(1536),
  match_count int default 5
)
returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    id,
    content,
    metadata,
    1 - (embedding <=> query_embedding) as similarity
  from docs_hier_v2
  order by embedding <=> query_embedding
  limit match_count;
$$;