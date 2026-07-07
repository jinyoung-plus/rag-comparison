# RAG 기반 문서 검색·답변 시스템 구현 — 청킹 × RAG 방식 4조합 비교

세종특별자치시교육청 자체감사 규정(훈령 제140호)을 대상으로,
**청킹 방식(시맨틱/계층형) × RAG 방식(Naive/Advanced)** 총 4가지 조합의 검색·답변 품질을
하나의 웹 화면(2×2 그리드)에서 동시 비교하는 시스템입니다.

---

## 1. 아키텍처

```
[원본 문서 .md]
   │
   ├─ 시맨틱 청킹 (chonkie SemanticChunker + BAAI/bge-m3) ──► semantic_chunks.jsonl (37청크)
   └─ 계층형 청킹 (제목 구조: 문서 > 장 > 조)            ──► hierarchical_chunks.json (35청크)
   │
   ▼ OpenRouter 임베딩 API (openai/text-embedding-3-small, 1536차원)
   │
   ▼ Supabase (pgvector)
   ├─ docs_semantic_v2  + match_docs_semantic_v2()  ← 코사인 유사도 검색
   └─ docs_hier_v2      + match_docs_hier_v2()
   │
   ▼ 웹 서비스 (단일 HTML)
   ├─ Naive RAG    : 질문 임베딩 → Top-K 벡터 검색 → 답변 생성
   └─ Advanced RAG : 질문 임베딩 → Top-20 검색 → Cohere Rerank(rerank-v3.5) → Top-K → 답변 생성
   │
   ▼ 답변 생성: OpenRouter Chat API (gpt-4o-mini / gemini-flash-1.5 / llama-3.1-8b 선택)
```

- 답변 프롬프트 원칙: **제공된 근거만 사용, [근거 N] 번호 명시, 근거에 없으면 모른다고 답변, 개조식**
- API 키는 화면 설정 패널에서 입력하며 **메모리에만 유지** (localStorage 미사용)

## 2. 레포지토리 구성

```
rag-comparison/
├── README.md              # 본 문서
├── docs/                  # 원본 문서 (Markdown)
│   └── 세종시교육청_자체감사규정.md
├── chunking/              # 청킹 노트북 2개 + 결과 파일
│   ├── chunking_semantic.ipynb      → semantic_chunks.jsonl
│   └── chunking_hierarchical.ipynb  → hierarchical_chunks.json
├── upload/                # 임베딩·업로드 스크립트 2개
│   ├── upload_semantic.py
│   └── upload_hier.py
├── sql/                   # Supabase 테이블·함수 생성 SQL
│   └── create_tables_functions.sql
└── app/                   # RAG 비교 웹 서비스
    └── rag_compare.html
```

## 3. 대상 문서 및 청킹

- **문서**: 세종특별자치시교육청 자체감사 규정 (훈령 제140호, 국가법령정보센터 공개 자료)
  - 장(章) 구분은 계층형 청킹 실험을 위해 임의 부여 (원문은 조문 평면 나열)
  - 개정 이력·조문 이동 표기는 검색 노이즈 제거를 위해 삭제
- **시맨틱 청킹**: chonkie `SemanticChunker`, `BAAI/bge-m3`, threshold=0.3, chunk_size=1024, min_sentences=2 → **37청크**
- **계층형 청킹**: `# 문서 > ## 장 > ### 조` 구조 기반 조(條) 단위 분할 → **35청크**
  - 임베딩 입력에 `source_path`(문서명 > 장 > 조)를 본문 앞에 결합하여 검색 정확도 향상

## 4. 실행 방법

### 사전 준비
- OpenRouter API 키 (임베딩 + 답변 생성), Cohere API 키 (리랭크), Supabase 프로젝트 (URL + anon 키)

### 절차
1. **환경 구성**: `conda create -n chunk python=3.11` 후
   `pip install chonkie sentence-transformers transformers tokenizers jupyter openai supabase`
2. **청킹**: `chunking/` 노트북 2개 실행 → 결과 파일 생성
3. **DB 구성**: Supabase SQL Editor에서 `sql/create_tables_functions.sql` 실행
4. **업로드**: `upload/` 스크립트 상단에 API 키·URL 입력 후 실행 (upsert 방식, 재실행 안전)
5. **웹 서비스**: `app/rag_compare.html`을 브라우저에서 열고 설정 패널에 키 입력 후 사용

## 5. 4조합 비교 결과 (샘플 질문 5개 실측)

| 질문 (정답 조문) | ①시맨틱×Naive | ②계층형×Naive | ③시맨틱×Adv | ④계층형×Adv | 핵심 관찰 |
|---|:---:|:---:|:---:|:---:|---|
| Q1 일상감사 의뢰 대상 업무 (제7조) | ○ | ○ | ○ | ◎ | 리랭크가 무관 조문 제거, 항·호 단위 인용 |
| Q2 감사결과 처분의 종류 (제17조) | ◎ | ○ | ○ | ○ | 대형 시맨틱 청크가 ②항 세부까지 포착 / 리랭크가 정답을 2위로 내린 반례 |
| Q3 재심의 신청 기한 (제23조) | ○ | ○ | ◎ | ◎ | 전원 정답("1개월 이내"), Advanced가 답변 초점 우수 |
| Q4 적극행정 면책 요건 (제20조) | △ | ◎ | ○ | ◎ | 시맨틱 청킹의 조문 분할 → Naive 요건 누락, 리랭크가 복구 |
| Q5 감사자료 제출 기한 (제13조) | ○ | ○ | ○ | ○ | 전원 정답("2일 전/종합감사 5일 전"), 검색 명확 시 리랭크 무차별 |

◎ 정확 + 출처·세부 정밀 / ○ 정확 / △ 부분 정답(누락) / ✕ 오답

### 종합 결론

1. **계층형 청킹이 규정류 문서에 안정적**
   - 조(條) 단위 완결성 덕에 요건·항·호 누락이 없음 (Q4에서 시맨틱×Naive만 요건 누락)
   - `source_path`가 근거 카드에 표시되어 **출처 추적성 우수** — 감사 업무의 "출처 명시" 원칙과 부합
   - 단, 조문이 매우 길면 LLM이 근거 뒷부분을 활용하지 못하는 경우 발생 (Q2)
2. **리랭크(Advanced)는 "보험" 역할**
   - 벡터 검색이 애매하거나 청킹이 조문을 분할했을 때 복구 효과가 큼 (Q1, Q4)
   - 검색이 명확하면 결과 차이 없이 속도만 손해 (Q5: Naive 1.5초 vs Advanced 5.1초)
   - 드물게 역효과도 존재 (Q2: 정답 조문을 2위로 강등)
3. **최고 안정 조합: ④ 계층형 × Advanced** (5문항 중 ◎3 / ○2 / 실패 0)
   - 단, 평균 소요시간 최장 → 실서비스에서는 비용·지연 대비 효과 검토 필요
4. **유사도 절대값보다 상대 순위·청크 완결성이 중요**
   - Q4에서 계층형 정답 유사도가 0.40에 불과했으나 1위 검색 + 완전한 답변

## 6. 유의 사항

- 스크립트·HTML의 API 키는 플레이스홀더(`sk-...`) 상태로 커밋되어 있음 — 실행 시 본인 키 입력 필요
- 임베딩 차원(1536)과 Supabase `vector(1536)` 컬럼은 반드시 일치해야 함
- 본 저장소는 교육 과제용이며, 대상 문서는 공개 훈령임
