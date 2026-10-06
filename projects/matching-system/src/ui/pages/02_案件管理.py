"""案件管理ページ"""
import streamlit as st
import requests
import json
from datetime import date
from pathlib import Path

API_BASE = "http://localhost:8000/api"

st.title("📌 案件管理")

# --- サンプルデータ読み込み ---
col1, col2 = st.columns([3, 1])
with col2:
    if st.button("📥 サンプルデータ読込", use_container_width=True):
        try:
            resp = requests.post(f"{API_BASE}/jobs/load-samples", timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                parts = []
                if result.get("created", 0):
                    parts.append(f"✅ {result['created']}件成功")
                if result.get("skipped", 0):
                    parts.append(f"⏭️ {result['skipped']}件重複")
                if result.get("failed"):
                    parts.append(f"❌ {result['failed']}件失敗")
                    for e in result.get("errors", []):
                        st.error(f"{e['id']}: {e['error']}")
                committed = result.get("committed", False)
                if not committed and result.get("failed", 0) > 0:
                    st.error(f"❌ 検証失敗: {result['failed']}件が保存できませんでした")
                elif committed:
                    if parts:
                        st.success(" / ".join(parts))
                else:
                    st.info("読込結果が空です")

                # unresolved_skills 警告表示（REQ-RE2-06）
                unresolved = result.get("unresolved_skills", [])
                if unresolved:
                    with st.expander(f"⚠️ 未解決スキル ({len(unresolved)}件)"):
                        for us in unresolved:
                            st.warning(f"ID: {us.get('record_id')} | 項目: {us.get('field')} | 値: {us.get('raw_value')} | 理由: {us.get('reason')}")
            elif resp.status_code == 404:
                st.warning("サンプルデータ読込はAPI側で無効です")
            else:
                st.error(f"読込失敗: {resp.status_code}")
        except Exception as e:
            st.error(f"API接続エラー: {e}")
        st.rerun()

# --- 案件一覧 ---
try:
    resp = requests.get(f"{API_BASE}/jobs")
    if resp.status_code == 200:
        jobs = resp.json()
    else:
        jobs = []
except Exception:
    jobs = []
    st.warning("APIに接続できません。`python run.py` で起動してください。")

st.markdown(f"### 登録済み案件一覧（{len(jobs)}件）")

if jobs:
    for job in jobs:
        with st.expander(f"**{job.get('title', '不明')}** — {job.get('company', '不明')} — {job.get('unit_price_min', 0)}〜{job.get('unit_price_max', 0)}万円/月"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**ID:** {job.get('id')}")
                st.markdown(f"**企業:** {job.get('company')}")
                st.markdown(f"**業界:** {job.get('industry')}")
                st.markdown(f"**職種:** {job.get('job_type')}")
                st.markdown(f"**勤務地:** {job.get('location')}")
                st.markdown(f"**リモート:** {job.get('remote_policy')}")
            with col2:
                st.markdown(f"**必要経験年数:** {job.get('required_experience_years')}年")
                st.markdown(f"**雇用形態:** {job.get('employment_type')}")
                st.markdown(f"**期間:** {job.get('duration')}")
                st.markdown(f"**募集人数:** {job.get('headcount')}名")
                st.markdown(f"**プロジェクト開始日:** {job.get('project_start_date') or '未設定'}")

                st.markdown("**必須スキル:**")
                req = job.get("required_skills", {})
                for cat, items in req.items():
                    if items:
                        st.markdown(f"- {cat}: {', '.join(items)}")

                st.markdown("**歓迎スキル:**")
                pref = job.get("preferred_skills", {})
                for cat, items in pref.items():
                    if items:
                        st.markdown(f"- {cat}: {', '.join(items)}")

            st.markdown(f"**業務内容:** {job.get('description')}")

            # 保留スキル表示（FIX-02）
            pending_skills = job.get("pending_skills", [])
            if pending_skills:
                with st.expander(f"⏳ 保留スキル ({len(pending_skills)}件)"):
                    for ps in pending_skills:
                        st.markdown(f"- **{ps.get('raw_name')}** (type: {ps.get('usage_type')}, status: {ps.get('status')})")
                        if ps.get("status") == "pending":
                            col_a, col_b, col_c = st.columns(3)
                            pid = ps["pending_id"]
                            jid = job["id"]
                            with col_a:
                                if st.button(f"📝 新規登録", key=f"jreg_{jid}_{pid}"):
                                    resp = requests.post(f"{API_BASE}/jobs/{jid}/pending-skills/{pid}/register")
                                    if resp.status_code == 200:
                                        st.success("登録しました")
                                        st.rerun()
                                    else:
                                        st.error(f"登録失敗: {resp.text}")
                            with col_b:
                                similar_resp = requests.get(f"{API_BASE}/skills/similar", params={"name": ps.get("raw_name", "")})
                                similar_options = []
                                if similar_resp.status_code == 200:
                                    similar_options = [s["id"] for s in similar_resp.json().get("results", [])[:5]]
                                link_id = st.selectbox(f"既存ID", options=[""] + similar_options + ["他"],
                                                       key=f"jlink_{jid}_{pid}", label_visibility="collapsed")
                                if link_id == "他":
                                    link_id = st.text_input(f"手入力", key=f"jlink_custom_{jid}_{pid}", label_visibility="collapsed")
                                if st.button(f"🔗 紐付け", key=f"jlnk_{jid}_{pid}") and link_id:
                                    resp = requests.post(f"{API_BASE}/jobs/{jid}/pending-skills/{pid}/link",
                                                          json={"skill_id": link_id})
                                    if resp.status_code == 200:
                                        st.success("紐付けました")
                                        st.rerun()
                                    else:
                                        st.error(f"紐付失敗: {resp.text}")
                            with col_c:
                                if st.button(f"⏭ 無視", key=f"jign_{jid}_{pid}"):
                                    requests.post(f"{API_BASE}/jobs/{jid}/pending-skills/{pid}/ignore")
                                    st.rerun()

            # 削除ボタン
            if st.button(f"🗑️ 削除", key=f"del_job_{job['id']}"):
                try:
                    resp = requests.delete(f"{API_BASE}/jobs/{job['id']}")
                    if resp.status_code == 204:
                        st.success("削除しました")
                        st.rerun()
                    else:
                        st.error("削除に失敗しました")
                except Exception as e:
                    st.error(f"エラー: {e}")
else:
    st.info("案件がまだ登録されていません。「サンプルデータ読込」ボタンでサンプルを追加できます。")

# --- 新規案件登録フォーム ---
st.markdown("---")
st.markdown("### ➕ 新規案件登録")

with st.form("new_job_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        new_id = st.text_input("ID *", placeholder="job-006")
        new_title = st.text_input("案件名 *", placeholder="Pythonエンジニア")
        new_company = st.text_input("企業名 *", placeholder="株式会社サンプル")
        new_industry = st.text_input("業界", placeholder="IT・通信")
        new_job_type = st.text_input("職種", placeholder="ITエンジニア")
    with col2:
        new_location = st.text_input("勤務地", placeholder="東京都渋谷区")
        new_remote = st.text_input("リモートポリシー", placeholder="週2回リモート可")
        new_req_years = st.number_input("必要経験年数", min_value=0, max_value=30, value=3)
        new_emp_type = st.selectbox("雇用形態", ["正社員", "契約社員", "業務委託", "派遣"])
        new_headcount = st.number_input("募集人数", min_value=1, max_value=20, value=1)
        new_project_start = st.date_input("プロジェクト開始日（稼働開始日）", value=date.today())
        new_posted_date = st.date_input("掲載日（募集開始日）", value=date.today())
    with col3:
        new_unit_price_min = st.number_input("最低単価（万円/月）", min_value=0, max_value=300, value=60)
        new_unit_price_max = st.number_input("最高単価（万円/月）", min_value=0, max_value=300, value=90)
        new_duration = st.text_input("案件期間", placeholder="長期")
        # 必須スキル
        st.markdown("**必須スキル（カンマ区切り）**")
        new_req_lang = st.text_input("必須:言語", placeholder="Python, SQL")
        new_req_fw = st.text_input("必須:FW", placeholder="Django")
        new_req_tools = st.text_input("必須:ツール", placeholder="Docker, Git")
        # 歓迎スキル
        st.markdown("**歓迎スキル（カンマ区切り）**")
        new_pref_lang = st.text_input("歓迎:言語", placeholder="TypeScript")
        new_pref_fw = st.text_input("歓迎:FW", placeholder="React")

    new_description = st.text_area("業務内容", placeholder="案件の詳細な説明")

    submitted = st.form_submit_button("登録", use_container_width=True)
    if submitted:
        if not new_id or not new_title or not new_company:
            st.error("ID、案件名、企業名は必須です")
        else:
            job_data = {
                "id": new_id,
                "title": new_title,
                "company": new_company,
                "industry": new_industry,
                "job_type": new_job_type,
                "location": new_location,
                "remote_policy": new_remote,
                "required_skills": {
                    "languages": [x.strip() for x in new_req_lang.split(",") if x.strip()],
                    "frameworks": [x.strip() for x in new_req_fw.split(",") if x.strip()],
                    "tools": [x.strip() for x in new_req_tools.split(",") if x.strip()],
                    "certifications": [],
                    "other": [],
                },
                "preferred_skills": {
                    "languages": [x.strip() for x in new_pref_lang.split(",") if x.strip()],
                    "frameworks": [x.strip() for x in new_pref_fw.split(",") if x.strip()],
                    "tools": [],
                    "certifications": [],
                    "other": [],
                },
                "description": new_description,
                "required_experience_years": new_req_years,
                "unit_price_min": int(new_unit_price_min),
                "unit_price_max": int(new_unit_price_max),
                "employment_type": new_emp_type,
                "duration": new_duration,
                "headcount": int(new_headcount),
                "project_start_date": new_project_start.isoformat(),
                "posted_date": new_posted_date.isoformat(),
            }
            try:
                resp = requests.post(f"{API_BASE}/jobs", json=job_data)
                if resp.status_code == 201:
                    st.success(f"案件 '{new_title}' を登録しました")
                    st.rerun()
                elif resp.status_code == 409:
                    st.error(f"ID '{new_id}' は既に存在します")
                else:
                    st.error(f"登録に失敗しました: {resp.text}")
            except Exception as e:
                st.error(f"API接続エラー: {e}")
