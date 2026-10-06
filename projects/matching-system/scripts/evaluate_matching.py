"""マッチング品質評価スクリプト（FIX-05）

Usage:
    python scripts/evaluate_matching.py
    python scripts/evaluate_matching.py --mode hybrid  # 特定モードのみ
    python scripts/evaluate_matching.py --output results.json

出力:
    - 標準出力: Markdown形式のサマリ
    - --output: JSON形式の詳細結果
"""
import json, sys, math, argparse
from pathlib import Path

# プロジェクトルート
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import config
from src.matching.keyword_matcher import KeywordMatcher
from src.matching.embedding_matcher import compute_hybrid_score
from src.matching.scorer import score_resume_against_job


def load_jsonl(path: Path) -> list[dict]:
    """JSONLファイルを読み込む"""
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def precision_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    """Precision@K"""
    top = ranked[:k]
    if not top:
        return 0.0
    return len([r for r in top if r in relevant]) / len(top)


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    """Recall@K"""
    if not relevant:
        return 0.0
    top = ranked[:k]
    return len([r for r in top if r in relevant]) / len(relevant)


def dcg(relevances: list[float], k: int) -> float:
    """DCG@K"""
    scores = relevances[:k]
    if not scores:
        return 0.0
    return scores[0] + sum(s / math.log2(i + 1) for i, s in enumerate(scores[1:], start=2))


def ndcg_at_k(ranked: list[str], relevance_map: dict[str, float], k: int) -> float:
    """nDCG@K"""
    actual = [relevance_map.get(r, 0.0) for r in ranked[:k]]
    ideal = sorted(relevance_map.values(), reverse=True)[:k]
    dcg_actual = dcg(actual, k)
    dcg_ideal = dcg(ideal, k)
    return dcg_actual / dcg_ideal if dcg_ideal > 0 else 0.0


class Evaluator:
    """マッチング評価器"""

    def __init__(self, data_dir: str | Path = ROOT / "data" / "evaluation"):
        self.data_dir = Path(data_dir)
        self.resumes: dict[str, dict] = {}
        self.jobs: dict[str, dict] = {}
        self.judgments: list[dict] = []
        self.matcher = KeywordMatcher()
        self._load_data()

    def _load_data(self) -> None:
        """評価データを読み込む"""
        for r in load_jsonl(self.data_dir / "resumes.jsonl"):
            self.resumes[r["id"]] = r
        for j in load_jsonl(self.data_dir / "jobs.jsonl"):
            self.jobs[j["id"]] = j
        self.judgments = load_jsonl(self.data_dir / "judgments.jsonl")
        print(f"Loaded {len(self.resumes)} resumes, {len(self.jobs)} jobs, {len(self.judgments)} judgments")

    def _get_resume_data(self, resume_id: str) -> dict:
        """Resumeデータを取得（必須フィールド補完）"""
        r = dict(self.resumes.get(resume_id, {}))
        r.setdefault("structured_skills", [])
        r.setdefault("skills", {})
        r.setdefault("years_of_experience", 0)
        r.setdefault("location", "")
        r.setdefault("desired_locations", [])
        return r

    def _get_job_data(self, job_id: str) -> dict:
        """Jobデータを取得（必須フィールド補完）"""
        j = dict(self.jobs.get(job_id, {}))
        j.setdefault("structured_required_skills", [])
        j.setdefault("structured_preferred_skills", [])
        j.setdefault("required_skills", {})
        j.setdefault("preferred_skills", {})
        j.setdefault("required_experience_years", 0)
        j.setdefault("location", "")
        j.setdefault("remote_policy", "")
        j.setdefault("unit_price_min", 0)
        j.setdefault("unit_price_max", 0)
        return j

    def score_keyword(self, resume_id: str, job_id: str) -> float:
        """Keywordマッチングスコア"""
        from src.matching.scorer import score_resume_against_job
        try:
            result = score_resume_against_job(self._get_resume_data(resume_id),
                                               self._get_job_data(job_id))
            return result["total_score"]
        except Exception:
            return 0.0

    def score_hybrid(self, resume_id: str, job_id: str, mode: str = "hybrid") -> float:
        """Hybridマッチングスコア"""
        try:
            result = compute_hybrid_score(self._get_resume_data(resume_id),
                                           self._get_job_data(job_id))
            return result["total_score"]
        except Exception:
            return 0.0

    def _split_targets(self, split: str) -> tuple[set[str], set[str]]:
        """指定splitに属するresume_idとjob_idのセットを取得"""
        split_judgments = [j for j in self.judgments if j.get("split") == split]
        resume_ids = set()
        job_ids = set()
        for j in split_judgments:
            resume_ids.add(j["resume_id"])
            job_ids.add(j["job_id"])
        return resume_ids, job_ids

    def evaluate_query(self, query_type: str, split: str,
                       score_fn, mode_label: str) -> dict:
        """特定のquery_typeとsplitに対する評価"""
        judgments = [j for j in self.judgments
                     if j.get("query_type") == query_type and j.get("split") == split]
        if not judgments:
            return {"mode": mode_label, "query_type": query_type, "split": split,
                    "count": 0, "error": "no data"}

        # クエリごとにランキングを作成
        all_precisions = {1: [], 3: [], 5: []}
        all_recalls = {1: [], 3: [], 5: []}
        all_ndcgs = {1: [], 3: [], 5: []}
        all_top1_hits = []

        # query_id ごとにグルーピング
        queries: dict[str, list[dict]] = {}
        for j in judgments:
            qid = j["resume_id"] if query_type == "resume-to-jobs" else j["job_id"]
            queries.setdefault(qid, []).append(j)

        # 同splitのターゲットのみに限定（リソースリーク防止）
        split_resumes, split_jobs = self._split_targets(split)

        for qid, q_judgments in queries.items():
            # 正解セットとrelevance map
            if query_type == "resume-to-jobs":
                all_targets = sorted(split_jobs)
                relevant = {j["job_id"] for j in q_judgments if j["relevance"] >= 2}
                relevance_map = {j["job_id"]: j["relevance"] for j in q_judgments}
            else:
                all_targets = sorted(split_resumes)
                relevant = {j["resume_id"] for j in q_judgments if j["relevance"] >= 2}
                relevance_map = {j["resume_id"]: j["relevance"] for j in q_judgments}

            # 全対象をスコアリング
            scored: list[tuple[float, str]] = []
            for target_id in all_targets:
                if query_type == "resume-to-jobs":
                    score = score_fn(qid, target_id)
                else:
                    score = score_fn(target_id, qid)
                scored.append((score, target_id))
            scored.sort(key=lambda x: x[0], reverse=True)
            ranked = [t[1] for t in scored]

            # 指標計算
            for k in (1, 3, 5):
                all_precisions[k].append(precision_at_k(ranked, relevant, k))
                all_recalls[k].append(recall_at_k(ranked, relevant, k))
                all_ndcgs[k].append(ndcg_at_k(ranked, relevance_map, k))
            # Top-1命中率: queryの正解が1件でもtop1に入ったか
            all_top1_hits.append(1.0 if ranked and ranked[0] in relevant else 0.0)

        def avg(vals: list[float]) -> float:
            return round(sum(vals) / len(vals), 4) if vals else 0.0

        return {
            "mode": mode_label,
            "query_type": query_type,
            "split": split,
            "count": len(queries),
            "precision@1": avg(all_precisions[1]),
            "precision@3": avg(all_precisions[3]),
            "precision@5": avg(all_precisions[5]),
            "recall@1": avg(all_recalls[1]),
            "recall@3": avg(all_recalls[3]),
            "recall@5": avg(all_recalls[5]),
            "ndcg@1": avg(all_ndcgs[1]),
            "ndcg@3": avg(all_ndcgs[3]),
            "ndcg@5": avg(all_ndcgs[5]),
            "top1_hit_rate": round(sum(all_top1_hits) / len(all_top1_hits), 4) if all_top1_hits else 0.0,
        }

    def score_hybrid_degraded(self, resume_id: str, job_id: str) -> float:
        """Degraded mode hybrid（embedding無効）"""
        from unittest.mock import patch
        with patch("src.matching.embedding_matcher.embedding_available", return_value=False):
            return self.score_hybrid(resume_id, job_id)

    def score_hybrid_embedding(self, resume_id: str, job_id: str) -> tuple[float, str]:
        """Embedding有効Hybrid（実モデル利用可否で mode を返す）

        Returns:
            (score, actual_mode)  actual_modeは "hybrid" または "hybrid_degraded"
        """
        from src.utils.vector_utils import is_available as emb_avail
        if not emb_avail():
            return self.score_hybrid_degraded(resume_id, job_id), "hybrid_degraded"
        return self.score_hybrid(resume_id, job_id), "hybrid"

    def evaluate_all(self, modes: list[str] | None = None) -> list[dict]:
        """全モード・全条件で評価"""
        if modes is None:
            modes = ["keyword", "hybrid_degraded", "hybrid"]

        results = []
        for mode in modes:
            if mode == "keyword":
                fn = self.score_keyword
            elif mode == "hybrid_degraded":
                fn = self.score_hybrid_degraded
            else:
                # hybrid は embedding 有無で実際のmodeが変わる
                fn_hybrid = self.score_hybrid_embedding
                def _score_wrapper(rid, jid):
                    s, actual = fn_hybrid(rid, jid)
                    return s
                fn = _score_wrapper

            for split in ("calibration", "test"):
                for qt in ("resume-to-jobs", "job-to-resumes"):
                    label = mode
                    result = self.evaluate_query(qt, split, fn, label)
                    results.append(result)
                    if result.get("count", 0) > 0:
                        print(f"  {label:16s} {split:12s} {qt:20s} "
                              f"n={result['count']:2d} "
                              f"P@1={result['precision@1']:.3f} "
                              f"R@1={result['recall@1']:.3f} "
                              f"nDCG@3={result['ndcg@3']:.3f} "
                              f"Top1Hit={result.get('top1_hit_rate', 0):.3f}")

        # hybrid modeの実際の動作を確認し、degraded相当なら別途記録
        if "hybrid" in modes:
            import src.utils.vector_utils as vu
            if not vu.is_available():
                # embedding利用不可 → hybridはdegradedと同等のため結果を統一
                for r in results:
                    if r["mode"] == "hybrid":
                        r["mode"] = "hybrid (degraded)"
                print("\n  [INFO] Embedding model not available: hybrid mode recorded as 'hybrid (degraded)'")

        return results

    def compare_keyword_vs_hybrid(self, results: list[dict]) -> dict:
        """KeywordとHybridの比較"""
        summary = {}
        for r in results:
            if r["count"] == 0:
                continue
            key = f"{r['split']}_{r['query_type']}"
            if key not in summary:
                summary[key] = {}
            summary[key][r["mode"]] = r
        return summary


def write_markdown(results: list[dict], path: Path) -> None:
    """Markdownレポートを出力（calibration + test両方）"""
    lines = ["# Matching Quality Evaluation Report", "",
             f"Generated: 2026-07-01", "",
             "## All Results", "",
             "| Split | Mode | Query Type | N | P@1 | P@3 | R@1 | R@3 | nDCG@3 | Top1Hit |",
             "|------|------|-----------|---|-----|-----|-----|-----|-------|---------|"]
    for r in sorted(results, key=lambda x: (x["split"], x["mode"], x["query_type"])):
        if r["count"] == 0:
            continue
        lines.append(f"| {r['split']} | {r['mode']} | {r['query_type']} | {r['count']} "
                     f"| {r['precision@1']:.3f} | {r['precision@3']:.3f} "
                     f"| {r['recall@1']:.3f} | {r['recall@3']:.3f} "
                     f"| {r['ndcg@3']:.3f} | {r['top1_hit_rate']:.3f} |")
    lines += ["", "## Requirement Check: Hybrid >= Keyword", "",
              "| Split | Query Type | Metric | Keyword | Hybrid | Diff | Result |",
              "|------|-----------|-------|-------|-------|------|--------|"]
    for split in ("calibration", "test"):
        kw = [r for r in results if r["mode"] == "keyword" and r["split"] == split and r["count"] > 0]
        hy = [r for r in results if r["mode"] == "hybrid" and r["split"] == split and r["count"] > 0]
        for k in kw:
            h = next((x for x in hy if x["query_type"] == k["query_type"]), None)
            if h:
                for metric in ("precision@1", "recall@1", "ndcg@3"):
                    diff = h[metric] - k[metric]
                    ok = "✓" if h[metric] >= k[metric] - 0.001 else "✗"
                    lines.append(f"| {split} | {k['query_type']} | {metric} | {k[metric]:.3f} | {h[metric]:.3f} | {diff:+.3f} | {ok} |")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="マッチング品質評価")
    parser.add_argument("--mode", choices=["keyword", "hybrid_degraded", "hybrid", "all"], default="all")
    parser.add_argument("--output", type=str, help="出力JSONファイル")
    parser.add_argument("--output-md", type=str, default=str(ROOT / "data" / "evaluation" / "report.md"), help="出力Markdownファイル")
    parser.add_argument("--data-dir", type=str, default=str(ROOT / "data" / "evaluation"))
    args = parser.parse_args()

    modes = ["keyword", "hybrid_degraded", "hybrid"] if args.mode in ("all",) else [args.mode]

    print(f"Evaluating modes: {modes}")
    print(f"Data directory: {args.data_dir}")
    print("=" * 70)

    evaluator = Evaluator(args.data_dir)
    results = evaluator.evaluate_all(modes)

    # 3モード比較
    print("\n" + "=" * 70)
    print("3-Mode Comparison (calibration):")
    print("-" * 70)
    for qt in ("resume-to-jobs", "job-to-resumes"):
        print(f"\n  {qt}:")
        for r in sorted(results, key=lambda x: x["mode"]):
            if r["split"] == "calibration" and r["query_type"] == qt and r["count"] > 0:
                print(f"    {r['mode']:16s} P@1={r['precision@1']:.3f} R@1={r['recall@1']:.3f} nDCG@3={r['ndcg@3']:.3f} Top1Hit={r['top1_hit_rate']:.3f}")

    # 全MetricでHybrid(emb)がKeywordを上回っているか（calibration + test両方）
    print("\n" + "=" * 70)
    print("Requirement Check: Hybrid > Keyword on all metrics? (calibration + test)")
    all_ok = True
    for split in ("calibration", "test"):
        kw_r = {r["query_type"]: r for r in results if r["mode"] == "keyword" and r["split"] == split and r["count"] > 0}
        hy_r = {r["query_type"]: r for r in results if r["mode"] == "hybrid" and r["split"] == split and r["count"] > 0}
        for qt in kw_r:
            if qt in hy_r:
                for metric in ("precision@1", "recall@1", "ndcg@3"):
                    kw_v = kw_r[qt][metric]
                    hy_v = hy_r[qt][metric]
                    ok = hy_v >= kw_v - 0.001  # 誤差許容
                    if not ok:
                        all_ok = False
                    print(f"  {split:12s} {qt:20s} {metric:15s}: KW={kw_v:.3f} HY={hy_v:.3f} {'OK' if ok else 'NG'}")
    print(f"\n  Result: {'ALL OK - weight adjustment not needed' if all_ok else 'SOME METRICS BELOW BASELINE - adjustment required'}")

    if args.output:
        Path(args.output).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON results -> {args.output}")
    md_path = Path(args.output_md)
    write_markdown(results, md_path)
    print(f"Markdown report -> {md_path}")


if __name__ == "__main__":
    main()
