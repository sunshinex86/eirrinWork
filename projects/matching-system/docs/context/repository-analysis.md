# Repository Analysis

> Generated: 2026-07-01
> Status: CONFIRMED
> Skill: 01_understand_repository

## 1. Project Overview

| Item | Value |
|------|-------|
| Project | 経歴書×案件マッチングシステム (Resume-Job Matching System) |
| Language | Python 3.9–3.11 |
| API Framework | FastAPI (port 8000) |
| UI Framework | Streamlit (port 8501) |
| Data Storage | JSON files with OS-level file locking |
| Validation | Pydantic v2 |
| Test Framework | pytest (397 test functions across 19 files) |
| CI | GitHub Actions (3.9/3.10/3.11) |

**Entry points:**
- `run.py` — launches both API (`uvicorn`) and UI (`streamlit`)
- `mcp_server.py` — standalone FastMCP server (experimental)

## 2. Directory Structure [CONFIRMED]

```
matching-system/
├── src/
│   ├── api/           # FastAPI routes (resumes, jobs, match, skills)
│   ├── agent/         # AI agent skills (matching_skills.py)
│   ├── matching/      # Matching engines (scorer, keyword, embedding, semantic, hierarchy)
│   ├── models/        # Pydantic v2 models (resume, job, match_result)
│   ├── repository/    # Data access layer (JSON-based CRUD with locking)
│   ├── ui/            # Streamlit pages (resume mgmt, job mgmt, matching, skill mgmt)
│   └── utils/         # Utilities (text, skills, vectors, RAG, extraction)
├── tests/             # 397 test functions
├── data/              # JSON data, skills dict/tree, knowledge base
├── docs/              # Documentation
└── .ai/               # AI development workflow
```

## 3. Matching System Architecture [CONFIRMED]

### Three Matching Modes

| Mode | Description | Default |
|------|-------------|---------|
| **keyword** | 5-axis weighted scorer (skill 40%, exp 20%, location 15%, industry 10%, salary 15%) | No |
| **hybrid** | 10-axis scorer + embedding + RAG (default mode) | **Yes** |
| **semantic** | Claude API-based semantic matching | No (requires API key) |

### Hybrid 10-Axis Breakdown (REQ-FIX-02)

| Axis | Weight | Description |
|------|--------|-------------|
| required_skill | 0.20 | skill_id match rate + level bonus |
| preferred_skill | 0.08 | Preferred skill match rate |
| skill_depth | 0.12 | Level, years, last-used freshness |
| skill_hierarchy | 0.08 | Skill tree parent/child relations |
| experience | 0.07 | Required experience years ratio |
| location | 0.08 | Prefecture-level + remote policy |
| context | 0.10 | Industry/project context (embedding or rule-based) |
| role | 0.08 | 9 role categories (SE, PM, Architect, etc.) |
| salary | 0.07 | Salary range overlap |
| embedding | 0.12 | Vector cosine similarity |

**Graceful degradation:** When embedding model unavailable, its 12% weight is redistributed proportionally across other 9 axes.

### Explanation System (Current) [CONFIRMED]

Current explanation is generated in `compute_hybrid_score()` → `embedding_matcher.py:581-603`:
- Simple rule-based text from score thresholds
- e.g., "必須スキルを十分満たしている。経験深度が十分。意味的類似度が高い。"
- Only covers: required_skill adequacy, depth adequacy, embedding similarity, RAG references, degraded mode notice
- No structured breakdown by recommendation reason categories
- No explicit risk assessment for insufficient experience/industry
- No detailed gap analysis beyond `missing_required_skills` / `missing_preferred_skills` lists

### Skill Gap Information (Current) [CONFIRMED]

Already captured in MatchItem model:
- `matched_skills: list[str]` — matched skill IDs
- `missing_required_skills: list[str]` — missing required skill IDs
- `missing_preferred_skills: list[str]` — missing preferred skill IDs
- `rag_corrections: list[RagCorrection]` — RAG score adjustment records with reasons
- `explanation: str` — simple text summary (current)

## 4. Data Models [CONFIRMED]

### MatchItem (match_result.py)
```python
class MatchItem(BaseModel):
    target_id, target_name, target_company
    total_score: float                     # 0-1 overall score
    breakdown: MatchBreakdown              # 5-axis (backward compat)
    mode: str                              # keyword | hybrid | hybrid_degraded
    weights: dict[str, float]              # weights used
    degraded: bool                         # embedding degraded flag
    hybrid_breakdown: Optional[HybridBreakdown]  # 10-axis breakdown
    matched_skills: list[str]              # matched skill IDs
    missing_required_skills: list[str]     # missing required skill IDs
    missing_preferred_skills: list[str]    # missing preferred skill IDs
    rag_sources: list[str]                 # RAG knowledge IDs referenced
    rag_corrections: list[RagCorrection]   # RAG correction records
    explanation: str                       # match explanation text
```

### HybridBreakdown (match_result.py)
```python
class HybridBreakdown(BaseModel):
    required_skill_score, preferred_skill_score
    skill_depth_score, skill_hierarchy_score
    experience_score, location_score
    context_score, role_score, salary_score
    embedding_score
```

### SemanticMatchResponse (match_result.py) — for Claude API mode
```python
class SemanticMatchResponse(BaseModel):
    score: float
    strengths: list[str]     # match strengths
    gaps: list[str]          # gaps/concerns
    explanation: str         # comprehensive explanation in Japanese
    error: str
```

## 5. UI (Streamlit Matching Page) [CONFIRMED]

The matching page (`03_マッチング.py`) currently displays:
- Bar chart of match scores
- Expandable details per match with:
  - Mode label (Hybrid / Keyword / Semantic)
  - Score breakdown (10 axes or 5 axes depending on mode)
  - Weights expander
  - RAG reference info expander
  - ✅ Matched skills list
  - ❌ Missing required skills list
  - ⚠️ Missing preferred skills list
  - `st.info(m["explanation"])` — explanation box

**No structured recommendation explanation view exists yet.** The current display lacks:
- Categorized explanation (skill / industry / experience / risk)
- Visual gap analysis
- Risk indicators with severity
- Compare mode (before/after gap fill)

## 6. Existing Tests [CONFIRMED]

| File | Tests | Coverage |
|------|-------|----------|
| test_models.py | 30 | MatchItem, MatchBreakdown, HybridBreakdown validation |
| test_embedding_matcher.py | 38 | 10-axis scoring, hybrid score computation |
| test_api.py | 64 | CRUD + matching integration |
| test_ui_display.py | 12 | UI display utilities |

**Unverified paths:**
- No specific tests for explanation generation content
- No tests for risk/industry gap analysis in explanations
- UI display logic for recommendation explanation not tested

## 7. Key Dependencies [CONFIRMED]

| Dependency | Purpose |
|------------|---------|
| fastapi, uvicorn | API server |
| streamlit | UI framework |
| pydantic v2 | Data validation |
| janome | Japanese tokenization |
| sentence-transformers | Embedding generation (optional) |
| anthropic | Claude API (optional) |

## 8. Impact Analysis for Recommendation Explanation Feature [INFERRED]

### Existing Components That Can Be Extended

| Component | Current State | Extension Potential |
|-----------|--------------|-------------------|
| `MatchItem.explanation` | Simple text | Refactor to include structured data |
| `compute_hybrid_score()` | Returns explanation text | Enhance with categorized explanation |
| `HybridBreakdown` | 10-axis scores | Already provides per-axis data for explanation |
| `SemanticMatchResponse` | strengths/gaps model | Pattern to reuse for explanation |
| `missing_required_skills` | List of skill IDs | Enhance with industry/experience gap analysis |
| UI `_render_breakdown()` | Score display | Add explanation view section |

### New Components Likely Needed

| Component | Reason |
|-----------|--------|
| Explanation generation service | Centralize explanation logic |
| Risk assessment logic | Industry gap, experience insufficiency detection |
| Explanation data model | Structured explanation with categories |
| Enhanced UI display | Visual explanation rendering |

## 9. Configuration & Environment [CONFIRMED]

- `config.py` contains all weights and feature flags
- `.env.example` documents all environment variables
- Feature flags: `CLAUDE_ENABLED`, `EMBEDDING_ENABLED`, `RAG_ENABLED`, `ENABLE_SAMPLE_LOAD`

## 10. Unknowns [UNKNOWN]

- Exact user expectations for "explanation breakdown" granularity
- Whether explanation should be generated server-side only or also client-side
- Whether explanations should be stored/cached with match results
- Performance expectations for explanation generation on large datasets

*This analysis was created from reading the repository. No implementation was performed.*
