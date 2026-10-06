"""マッチングページ"""
import streamlit as st
import requests
import pandas as pd

API_BASE = "http://localhost:8000/api"

st.title("🎯 マッチング")

# --- データ取得 ---
@st.cache_data(ttl=10)
def load_data():
    try:
        resp_r = requests.get(f"{API_BASE}/resumes")
        resumes = resp_r.json() if resp_r.status_code == 200 else []
        resp_j = requests.get(f"{API_BASE}/jobs")
        jobs = resp_j.json() if resp_j.status_code == 200 else []
        return resumes, jobs
    except Exception:
        return [], []


def _render_breakdown(m: dict):
    """モードに応じてスコア内訳を表示（REQ-01: Hybrid 10軸 / Keyword 5軸）"""
    mode = m.get("mode", "keyword")
    degraded = m.get("degraded", False)

    # mode 表示
    mode_label = {"hybrid": "🧠 Hybrid", "hybrid_degraded": "⚠️ Hybrid(Degraded)", "keyword": "📋 Keyword", "semantic": "🤖 Semantic"}
    st.caption(f"方式: {mode_label.get(mode, mode)}")

    if degraded:
        st.warning("⚠️ Embeddingモデルが利用不可のため Degraded Mode で動作中")

    # weights 表示
    weights = m.get("weights", {})
    if weights:
        with st.expander("使用した重み"):
            for k, v in weights.items():
                st.markdown(f"- {k}: {v*100:.1f}%")

    # RAG参照情報表示（REQ-RE2-07）
    rag_sources = m.get("rag_sources", [])
    if rag_sources:
        with st.expander(f"📚 RAG参照情報 ({len(rag_sources)}件)"):
            for rid in rag_sources:
                st.markdown(f"- {rid}")

    if mode in ("hybrid", "hybrid_degraded"):
        hb = m.get("hybrid_breakdown", {})
        if hb:
            col1, col2, col3, col4, col5 = st.columns(5)
            axis_1_5 = [
                ("必須スキル", hb.get("required_skill_score", 0)),
                ("歓迎スキル", hb.get("preferred_skill_score", 0)),
                ("スキル深度", hb.get("skill_depth_score", 0)),
                ("スキル階層", hb.get("skill_hierarchy_score", 0)),
                ("総経験", hb.get("experience_score", 0)),
            ]
            for col, (label, val) in zip([col1, col2, col3, col4, col5], axis_1_5):
                col.metric(label, f"{val*100:.0f}%")

            col6, col7, col8, col9, col10 = st.columns(5)
            axis_6_10 = [
                ("勤務地", hb.get("location_score", 0)),
                ("文脈", hb.get("context_score", 0)),
                ("ロール", hb.get("role_score", 0)),
                ("単価", hb.get("unit_price_score", 0)),
                ("Embedding", hb.get("embedding_score", 0)),
            ]
            for col, (label, val) in zip([col6, col7, col8, col9, col10], axis_6_10):
                col.metric(label, f"{val*100:.0f}%")
    else:
        bd = m.get("breakdown", {})
        if bd:
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("スキル", f"{bd.get('skill_match', 0)*100:.0f}%")
            col2.metric("経験", f"{bd.get('experience_match', 0)*100:.0f}%")
            col3.metric("勤務地", f"{bd.get('location_match', 0)*100:.0f}%")
            col4.metric("業界", f"{bd.get('industry_match', 0)*100:.0f}%")
            col5.metric("単価", f"{bd.get('unit_price_match', 0)*100:.0f}%")


def _render_schedule(m: dict):
    """候補者の稼働可能日と案件開始日のスケジュール適合状況を表示する"""
    schedule = m.get("schedule")
    if not schedule:
        return

    status = schedule.get("status", "unknown")
    message = schedule.get("message", "")
    if status == "conflict":
        st.error(f"🗓️ スケジュール不一致: {message}")
    elif status == "match":
        st.success(f"🗓️ スケジュール適合: {message}")
    else:
        st.info(f"🗓️ スケジュール: {message}")


def _render_recommendation_actions(actions: dict):
    """推薦アクションをカード形式で表示する。"""
    recommendations = actions.get("recommendations", [])
    if not recommendations:
        st.info("推薦アクションはありません")
        return

    st.markdown("### 🤖 推薦アクション")

    for idx, item in enumerate(recommendations, start=1):
        priority_map = {
            "high": "🟢 高",
            "medium": "🟡 中",
            "low": "🔴 低",
        }
        with st.container():
            st.markdown(
                f"""
                <div style="padding:14px; border:1px solid #d9e2f2; border-radius:12px; margin-bottom:12px; background:#f8fbff;">
                    <div style="font-size:16px; font-weight:700; margin-bottom:6px;">{idx}. {item.get('job_title', '')}</div>
                    <div style="font-size:13px; color:#4b5563; margin-bottom:8px;">{item.get('company', '')} · {priority_map.get(item.get('priority', 'low'), item.get('priority', 'low'))} · スコア {item.get('score', 0) * 100:.1f}%</div>
                    <div style="font-size:14px; margin-bottom:6px;"><b>推奨アクション:</b> {item.get('recommended_action', '')}</div>
                    <div style="font-size:14px; margin-bottom:6px;"><b>連絡文案:</b> {item.get('communication_text', '')}</div>
                    <div style="font-size:13px; color:#374151;"><b>一致スキル:</b> {', '.join(item.get('matched_skills', [])[:5]) or 'なし'}</div>
                    <div style="font-size:13px; color:#374151;"><b>不足スキル:</b> {', '.join(item.get('missing_required_skills', [])[:3]) or 'なし'}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


resumes, jobs = load_data()

if not resumes or not jobs:
    st.warning("経歴書と案件の両方が登録されている必要があります。各管理ページでデータを登録してください。")
    st.stop()

# --- タブ切り替え ---
tab1, tab2 = st.tabs(["📋 経歴書から案件を探す", "📌 案件から候補者を探す"])

# ====================
# タブ1: 経歴書 → 案件
# ====================
with tab1:
    st.markdown("### 経歴書を選んで、マッチする案件を探す")

    resume_options = {f"{r.get('name')}（{r.get('id')}）": r.get("id") for r in resumes}
    selected_resume_label = st.selectbox(
        "経歴書を選択",
        options=list(resume_options.keys()),
        key="resume_select",
    )

    if st.button("🔍 マッチング実行", type="primary", key="btn_resume_match"):
        resume_id = resume_options[selected_resume_label]
        with st.spinner("マッチング計算中..."):
            try:
                resp = requests.post(f"{API_BASE}/match/resume-to-jobs/{resume_id}")
                if resp.status_code == 200:
                    result = resp.json()
                    matches = result.get("matches", [])

                    if matches:
                        st.success(f"{len(matches)}件の案件が見つかりました")

                        try:
                            actions_resp = requests.post(
                                f"{API_BASE}/skills/recommendation/actions",
                                json={"resume_id": resume_id, "top_n": 5},
                                timeout=10,
                            )
                            if actions_resp.status_code == 200:
                                action_result = actions_resp.json()
                                _render_recommendation_actions(action_result)
                            else:
                                st.warning("推薦アクションの取得に失敗しました")
                        except Exception as e:
                            st.warning(f"推薦アクション取得エラー: {e}")

                        # スコア分布（横棒グラフ）
                        df_plot = pd.DataFrame([
                            {
                                "対象": m['target_name'][:30],
                                "総合スコア": m["total_score"] * 100,
                            }
                            for m in matches
                        ])
                        st.bar_chart(
                            df_plot.set_index("対象")["総合スコア"],
                            horizontal=True,
                        )

                        # 詳細結果テーブル
                        for m in matches:
                            score_pct = m["total_score"] * 100
                            color = "🟢" if score_pct >= 70 else ("🟡" if score_pct >= 50 else "🔴")

                            with st.expander(f"{color} **{score_pct:.1f}%** — {m['target_name']} | {m['target_company']}"):
                                _render_breakdown(m)
                                _render_schedule(m)

                                # 一致スキル・不足スキル
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    if m["matched_skills"]:
                                        st.markdown(f"✅ **一致スキル:** {', '.join(m['matched_skills'])}")
                                with col_b:
                                    if m["missing_required_skills"]:
                                        st.markdown(f"❌ **不足必須スキル:** {', '.join(m['missing_required_skills'])}")
                                    if m["missing_preferred_skills"]:
                                        st.markdown(f"⚠️ **不足歓迎スキル:** {', '.join(m['missing_preferred_skills'])}")

                                # 説明
                                st.info(m["explanation"])

                        # テーブル表示
                        st.markdown("### 一覧表")
                        table_data = []
                        for m in matches:
                            schedule = m.get("schedule") or {}
                            table_data.append({
                                "スコア": f"{m['total_score']*100:.1f}%",
                                "案件名": m["target_name"],
                                "企業": m["target_company"],
                                "一致スキル": ", ".join(m["matched_skills"][:5]),
                                "不足必須": ", ".join(m["missing_required_skills"][:3]),
                                "スケジュール": {"match": "✅ 適合", "conflict": "⚠️ 不一致"}.get(schedule.get("status"), "❔ 不明"),
                            })
                        st.dataframe(pd.DataFrame(table_data), use_container_width=True)
                    else:
                        st.info("マッチする案件が見つかりませんでした")
                else:
                    st.error(f"マッチングに失敗しました: {resp.text}")
            except Exception as e:
                st.error(f"API接続エラー: {e}")


# ====================
# タブ2: 案件 → 経歴書
# ====================
with tab2:
    st.markdown("### 案件を選んで、マッチする候補者を探す")

    job_options = {f"{j.get('title')}（{j.get('company')} | {j.get('id')}）": j.get("id") for j in jobs}
    selected_job_label = st.selectbox(
        "案件を選択",
        options=list(job_options.keys()),
        key="job_select",
    )

    if st.button("🔍 マッチング実行", type="primary", key="btn_job_match"):
        job_id = job_options[selected_job_label]
        with st.spinner("マッチング計算中..."):
            try:
                resp = requests.post(f"{API_BASE}/match/job-to-resumes/{job_id}")
                if resp.status_code == 200:
                    result = resp.json()
                    matches = result.get("matches", [])

                    if matches:
                        st.success(f"{len(matches)}名の候補者が見つかりました")

                        # スコア分布
                        df_plot = pd.DataFrame([
                            {
                                "候補者": m["target_name"],
                                "総合スコア": m["total_score"] * 100,
                            }
                            for m in matches
                        ])
                        st.bar_chart(
                            df_plot.set_index("候補者")["総合スコア"],
                            horizontal=True,
                        )

                        # 詳細結果（REQ-RE-05/06: 共通 _render_breakdown 使用）
                        for m in matches:
                            score_pct = m["total_score"] * 100
                            color = "🟢" if score_pct >= 70 else ("🟡" if score_pct >= 50 else "🔴")

                            with st.expander(f"{color} **{score_pct:.1f}%** — {m['target_name']}"):
                                _render_breakdown(m)
                                _render_schedule(m)

                                col_a, col_b = st.columns(2)
                                with col_a:
                                    if m["matched_skills"]:
                                        st.markdown(f"✅ **一致スキル:** {', '.join(m['matched_skills'])}")
                                with col_b:
                                    if m["missing_required_skills"]:
                                        st.markdown(f"❌ **不足必須スキル:** {', '.join(m['missing_required_skills'])}")
                                    if m["missing_preferred_skills"]:
                                        st.markdown(f"⚠️ **不足歓迎スキル:** {', '.join(m['missing_preferred_skills'])}")

                                st.info(m["explanation"])

                        # テーブル表示
                        st.markdown("### 一覧表")
                        table_data = []
                        for m in matches:
                            schedule = m.get("schedule") or {}
                            table_data.append({
                                "スコア": f"{m['total_score']*100:.1f}%",
                                "候補者名": m["target_name"],
                                "一致スキル": ", ".join(m["matched_skills"][:5]),
                                "不足必須": ", ".join(m["missing_required_skills"][:3]),
                                "スケジュール": {"match": "✅ 適合", "conflict": "⚠️ 不一致"}.get(schedule.get("status"), "❔ 不明"),
                            })
                        st.dataframe(pd.DataFrame(table_data), use_container_width=True)
                    else:
                        st.info("マッチする候補者が見つかりませんでした")
                else:
                    st.error(f"マッチングに失敗しました: {resp.text}")
            except Exception as e:
                st.error(f"API接続エラー: {e}")
