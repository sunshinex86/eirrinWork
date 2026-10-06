"""Schedule ページ"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st
import requests

from src.ui.display_utils import build_candidate_availability_from_resume

API_BASE = "http://localhost:8000/api"


def _build_recommendation_text(candidate_available_from: str, project_start_date: str) -> tuple[str, str, str]:
    try:
        candidate_date = datetime.fromisoformat(candidate_available_from).date()
        project_date = datetime.fromisoformat(project_start_date).date()
    except Exception:
        return "warn", "判定不可", "可上岗日とプロジェクト開始日の形式を確認してください"

    if candidate_date > project_date:
        return "bad", "プロジェクト開始日より遅く、進めないおすすめ", "候補者はプロジェクト開始日より後に稼働可能"
    if candidate_date == project_date:
        return "good", "このプロジェクトに適合。開始日にそのまま稼働可能", "候補者はプロジェクト開始日に稼働可能"

    days_gap = (project_date - candidate_date).days
    if days_gap <= 14:
        return "good", "このプロジェクトに適合。開始日までに準備可能", f"候補者は開始日の{days_gap}日前から準備可能"
    return "warn", "可開始日が早すぎるため、バッファを要する", f"候補者は開始日の{days_gap}日前から準備可能。バッファを検討"


def _status_badge(tone: str) -> str:
    if tone == "good":
        return "<span style='color:#047857; background:#dcfce7; padding:3px 8px; border-radius:999px; font-weight:700;'>強</span>"
    if tone == "warn":
        return "<span style='color:#b45309; background:#fef3c7; padding:3px 8px; border-radius:999px; font-weight:700;'>中</span>"
    return "<span style='color:#b91c1c; background:#fee2e2; padding:3px 8px; border-radius:999px; font-weight:700;'>弱</span>"


st.title("🗓️ Schedule")
st.caption("候補者の「稼働可能日」と案件の「開始日」を直接比較して、最適な候補を見極めます")

resume_options = []
job_options = []
try:
    resume_resp = requests.get(f"{API_BASE}/resumes", timeout=5)
    if resume_resp.status_code == 200:
        for r in resume_resp.json():
            resume_options.append((r.get("id"), r.get("name", r.get("id"))))

    jobs_resp = requests.get(f"{API_BASE}/jobs", timeout=5)
    if jobs_resp.status_code == 200:
        for job in jobs_resp.json():
            job_options.append((job.get("id"), job.get("title", job.get("id")), job))
except Exception:
    st.warning("APIに接続できません。`python run.py` で起動してください。")
    st.stop()

if not resume_options:
    st.info("経歴書が登録されていません")
    st.stop()
if not job_options:
    st.info("案件が登録されていません")
    st.stop()

selected_resume = st.selectbox("候補者を選択", options=[name for _, name in resume_options], key="schedule_resume")
resume_id = next(rid for rid, name in resume_options if name == selected_resume)
selected_job_title = st.selectbox("対象プロジェクトを選択", options=[title for _, title, _ in job_options], key="schedule_project")
selected_job = next(job for _, title, job in job_options if title == selected_job_title)

resume_resp = requests.get(f"{API_BASE}/resumes/{resume_id}", timeout=5)
resume = resume_resp.json() if resume_resp.status_code == 200 else {}
availability_info = build_candidate_availability_from_resume(resume)
project_start = selected_job.get("project_start") or selected_job.get("start_date") or selected_job.get("start") or datetime.today().date().isoformat()
job_window = {
    "project_name": selected_job.get("title", selected_job.get("id", "-")),
    "project_start": project_start,
    "start": f"{project_start}T10:00:00",
    "end": f"{project_start}T18:00:00",
}

availability_payload = {
    "candidate_availability": availability_info,
    "job_window": job_window,
}

conflict_payload = {
    "candidate_availability": availability_info,
    "other_events": [
        {"start": "2026-07-23T10:00:00", "end": "2026-07-23T11:00:00"},
        {"start": "2026-07-23T15:00:00", "end": "2026-07-23T16:00:00"},
    ],
}

st.subheader("対象プロジェクト")
st.markdown(f"**プロジェクト名：{job_window.get('project_name', '-')}**")
st.markdown(f"**プロジェクト開始日：{job_window.get('project_start', '-')}**")

st.subheader("候補者の稼働可能日 / プロジェクト開始日 / マッチングスコア")
comparison_cols = st.columns(3)
comparison_cols[0].metric("稼働可能日", availability_info.get("available_from", "-"))
comparison_cols[1].metric("プロジェクト開始日", job_window.get("project_start", "-"))
comparison_cols[2].metric("マッチングスコア", "-", help="選択されたプロジェクト開始日を基準に計算")

st.subheader("候補者可用時間")
availability_df = pd.DataFrame(availability_info.get("slots", []))

if availability_df.empty:
    st.info("候補者の available slots が見つかりませんでした")
else:
    availability_df["start"] = pd.to_datetime(availability_df["start"])
    availability_df["end"] = pd.to_datetime(availability_df["end"])
    st.dataframe(availability_df, use_container_width=True)

    if not availability_df.empty:
        chart_data = []
        for row in availability_info.get("slots", []):
            start = datetime.fromisoformat(row["start"])
            end = datetime.fromisoformat(row["end"])
            chart_data.append({"start": start, "end": end, "label": f"{start:%H:%M} - {end:%H:%M}"})
        st.bar_chart(pd.DataFrame(chart_data).set_index("label")[[]], use_container_width=True)

if st.button("📌 Schedule を確認", type="primary"):
    with st.spinner("Schedule を計算中..."):
        try:
            avail_resp = requests.post(
                f"{API_BASE}/skills/schedule/availability",
                json=availability_payload,
                timeout=10,
            )
            conflict_resp = requests.post(
                f"{API_BASE}/skills/schedule/conflicts",
                json=conflict_payload,
                timeout=10,
            )

            selected_candidate = None
            if avail_resp.status_code == 200:
                availability = avail_resp.json()
                score = availability.get("availability_score", 0.0)
                status = availability.get("status", "unknown")
                candidate_available_from = availability.get("candidate_available_from", availability_info.get("available_from", "-"))
                project_start_date = availability.get("project_start", job_window.get("project_start", "-"))
                tone, recommendation_text, recommendation_detail = _build_recommendation_text(
                    candidate_available_from,
                    project_start_date,
                )

                selected_candidate = {
                    "candidate": resume.get("name", resume_id),
                    "candidate_available_from": candidate_available_from,
                    "project_start_date": project_start_date,
                    "score": score,
                    "status": status,
                    "tone": tone,
                    "recommendation_text": recommendation_text,
                    "recommendation_detail": recommendation_detail,
                }

                st.subheader("比較カード")
                st.markdown(f"**プロジェクト名：{job_window.get('project_name', '-')}**")
                st.markdown(f"**プロジェクト開始日：{project_start_date}**")
                st.markdown(
                    f"<div style='margin-bottom:12px; padding:10px 12px; border-left:4px solid {'#10b981' if tone == 'good' else '#f59e0b' if tone == 'warn' else '#ef4444'}; background:#f9fafb; border-radius:8px;'>"
                    f"<b>推奨:</b> {recommendation_text}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div style='margin-bottom:12px; padding:10px 12px; border:1px solid #d1d5db; border-radius:8px; background:#ffffff;'>"
                    f"<b>判定:</b> この候補者は <span style='font-weight:700;'>{candidate_available_from}</span> から稼働可能で、"
                    f"選択中のプロジェクト開始日 <span style='font-weight:700;'>{project_start_date}</span> に合わせて稼働できるかを評価しています。"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                card_cols = st.columns(3)
                card_cols[0].markdown(
                    f"""
                    <div style="padding:14px; border:1px solid #d1fae5; border-radius:12px; background:#ecfdf5;">
                        <div style="font-size:12px; color:#6b7280; margin-bottom:4px;">稼働可能日</div>
                        <div style="font-size:18px; font-weight:700; color:#047857;">{candidate_available_from}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                card_cols[1].markdown(
                    f"""
                    <div style="padding:14px; border:1px solid #bfdbfe; border-radius:12px; background:#eff6ff;">
                        <div style="font-size:12px; color:#6b7280; margin-bottom:4px;">プロジェクト開始日</div>
                        <div style="font-size:18px; font-weight:700; color:#1d4ed8;">{project_start_date}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                card_cols[2].markdown(
                    f"""
                    <div style="padding:14px; border:1px solid {'#bbf7d0' if tone == 'good' else '#fde68a' if tone == 'warn' else '#fecaca'}; border-radius:12px; background:{'#f0fdf4' if tone == 'good' else '#fffbeb' if tone == 'warn' else '#fef2f2'};">
                        <div style="font-size:12px; color:#6b7280; margin-bottom:4px;">マッチングスコア</div>
                        <div style="font-size:18px; font-weight:700; color:{'#047857' if tone == 'good' else '#b45309' if tone == 'warn' else '#b91c1c'};">{score:.2%}</div>
                        <div style="font-size:13px; color:#374151;">{recommendation_detail}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.subheader("Availability Result")
                st.json(availability)
            else:
                st.error("Availability API 呼び出し失敗")

            if conflict_resp.status_code == 200:
                conflicts = conflict_resp.json()
                st.subheader("Conflict Detection Result")
                st.json(conflicts)
            else:
                st.error("Conflict API 呼び出し失敗")

            if selected_candidate is None:
                st.stop()

            st.subheader("複数候補者の横並びランキング：プロジェクト開始日に対する適合度順")
            ranking_rows = []
            resume_list = requests.get(f"{API_BASE}/resumes", timeout=5).json()
            for candidate_resume in resume_list:
                candidate_availability = build_candidate_availability_from_resume(candidate_resume)
                payload = {"candidate_availability": candidate_availability, "job_window": job_window}
                score_resp = requests.post(f"{API_BASE}/skills/schedule/availability", json=payload, timeout=10)
                if score_resp.status_code != 200:
                    continue
                result = score_resp.json()
                score = result.get("availability_score", 0.0)
                tone, recommendation_text, recommendation_detail = _build_recommendation_text(
                    result.get("candidate_available_from", candidate_availability.get("available_from", "-")),
                    job_window.get("project_start", "-"),
                )
                ranking_rows.append({
                    "candidate": candidate_resume.get("name", candidate_resume.get("id")),
                    "可上岗日": result.get("candidate_available_from", candidate_availability.get("available_from", "-")),
                    "プロジェクト開始日": job_window.get("project_start", "-"),
                    "プロジェクト名": job_window.get("project_name", "-"),
                    "マッチングスコア": round(score, 3),
                    "状态": _status_badge(tone),
                    "why": recommendation_text,
                    "detail": recommendation_detail,
                })

            ranking_rows = sorted(ranking_rows, key=lambda row: row["マッチングスコア"], reverse=True)
            ranking_html = "<table style='width:100%; border-collapse:collapse;'><thead><tr><th style='padding:8px; border-bottom:1px solid #d1d5db; text-align:left;'>候補者</th><th style='padding:8px; border-bottom:1px solid #d1d5db; text-align:left;'>プロジェクト</th><th style='padding:8px; border-bottom:1px solid #d1d5db; text-align:left;'>プロジェクト開始日</th><th style='padding:8px; border-bottom:1px solid #d1d5db; text-align:left;'>稼働可能日</th><th style='padding:8px; border-bottom:1px solid #d1d5db; text-align:left;'>マッチングスコア</th><th style='padding:8px; border-bottom:1px solid #d1d5db; text-align:left;'>状態</th><th style='padding:8px; border-bottom:1px solid #d1d5db; text-align:left;'>理由</th></tr></thead><tbody>"
            for index, row in enumerate(ranking_rows, start=1):
                ranking_html += (
                    f"<tr><td style='padding:8px; border-bottom:1px solid #f3f4f6;'><b>{index}. {row['candidate']}</b></td>"
                    f"<td style='padding:8px; border-bottom:1px solid #f3f4f6;'>{row['プロジェクト名']}</td>"
                    f"<td style='padding:8px; border-bottom:1px solid #f3f4f6;'>{row['プロジェクト開始日']}</td>"
                    f"<td style='padding:8px; border-bottom:1px solid #f3f4f6;'>{row['可上岗日']}</td>"
                    f"<td style='padding:8px; border-bottom:1px solid #f3f4f6;'>{row['マッチングスコア']:.2%}</td>"
                    f"<td style='padding:8px; border-bottom:1px solid #f3f4f6;'>{row['状態']}</td>"
                    f"<td style='padding:8px; border-bottom:1px solid #f3f4f6;'>{row['why']}</td></tr>"
                )
            ranking_html += "</tbody></table>"
            st.markdown(ranking_html, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"API接连接エラー: {e}")
