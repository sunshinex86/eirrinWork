"""経歴書管理ページ"""
import streamlit as st
import requests
import json
from datetime import date
from pathlib import Path

API_BASE = "http://localhost:8000/api"

st.title("📋 経歴書管理")

# --- サンプルデータ読み込み ---
col1, col2 = st.columns([3, 1])
with col2:
    if st.button("📥 サンプルデータ読込", use_container_width=True):
        try:
            resp = requests.post(f"{API_BASE}/resumes/load-samples", timeout=30)
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
                    # 失敗のみの場合、成功メッセージは表示しない
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

# --- 経歴書一覧 ---
try:
    resp = requests.get(f"{API_BASE}/resumes")
    if resp.status_code == 200:
        resumes = resp.json()
    else:
        resumes = []
except Exception:
    resumes = []
    st.warning("APIに接続できません。`python run.py` で起動してください。")

st.markdown(f"### 登録済み経歴書一覧（{len(resumes)}件）")

if resumes:
    for resume in resumes:
        with st.expander(f"**{resume.get('name', '不明')}** — {resume.get('years_of_experience', 0)}年経験 — 希望単価{resume.get('desired_unit_price_min', 0)}〜{resume.get('desired_unit_price_max', 0)}万円/月"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**ID:** {resume.get('id')}")
                st.markdown(f"**年齢:** {resume.get('age')}歳")
                st.markdown(f"**居住地:** {resume.get('location')}")
                st.markdown(f"**希望勤務地:** {', '.join(resume.get('desired_locations', []))}")
                st.markdown(f"**雇用形態:** {resume.get('employment_type')}")
            with col2:
                st.markdown(f"**メール:** {resume.get('email')}")
                st.markdown(f"**電話:** {resume.get('phone')}")

                skills = resume.get("skills", {})
                st.markdown("**スキル:**")
                for cat, items in skills.items():
                    if items:
                        st.markdown(f"- {cat}: {', '.join(items)}")

            # 職歴
            st.markdown("**職歴:**")
            for wh in resume.get("work_history", []):
                end = wh.get("end_date") or "現在"
                st.markdown(f"- {wh.get('start_date')} 〜 {end} | **{wh.get('company')}** | {wh.get('position')}（{wh.get('industry')}）")

            # 自己PR
            if resume.get("self_pr"):
                st.markdown(f"**自己PR:** {resume.get('self_pr')}")

            # 保留スキル表示（FIX-02）
            pending_skills = resume.get("pending_skills", [])
            if pending_skills:
                with st.expander(f"⏳ 保留スキル ({len(pending_skills)}件)"):
                    for ps in pending_skills:
                        st.markdown(f"- **{ps.get('raw_name')}** (status: {ps.get('status')})")
                        if ps.get("status") == "pending":
                            col_a, col_b, col_c = st.columns(3)
                            pid = ps["pending_id"]
                            rid = resume["id"]
                            with col_a:
                                if st.button(f"📝 新規登録", key=f"reg_{rid}_{pid}"):
                                    resp = requests.post(f"{API_BASE}/resumes/{rid}/pending-skills/{pid}/register")
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
                                                       key=f"link_{rid}_{pid}", label_visibility="collapsed")
                                if link_id == "他":
                                    link_id = st.text_input(f"手入力", key=f"link_custom_{rid}_{pid}", label_visibility="collapsed")
                                if st.button(f"🔗 紐付け", key=f"lnk_{rid}_{pid}") and link_id:
                                    resp = requests.post(f"{API_BASE}/resumes/{rid}/pending-skills/{pid}/link",
                                                          json={"skill_id": link_id})
                                    if resp.status_code == 200:
                                        st.success("紐付けました")
                                        st.rerun()
                                    else:
                                        st.error(f"紐付失敗: {resp.text}")
                            with col_c:
                                if st.button(f"⏭ 無視", key=f"ign_{rid}_{pid}"):
                                    requests.post(f"{API_BASE}/resumes/{rid}/pending-skills/{pid}/ignore")
                                    st.rerun()

            # 削除ボタン
            if st.button(f"🗑️ 削除", key=f"del_resume_{resume['id']}"):
                try:
                    resp = requests.delete(f"{API_BASE}/resumes/{resume['id']}")
                    if resp.status_code == 204:
                        st.success("削除しました")
                        st.rerun()
                    else:
                        st.error("削除に失敗しました")
                except Exception as e:
                    st.error(f"エラー: {e}")
else:
    st.info("経歴書がまだ登録されていません。「サンプルデータ読込」ボタンでサンプルを追加できます。")

# --- 新規経歴書登録フォーム ---
st.markdown("---")
st.markdown("### ➕ 新規経歴書登録")

with st.form("new_resume_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        new_id = st.text_input("ID *", placeholder="resume-004")
        new_name = st.text_input("氏名 *", placeholder="山田 太郎")
        new_age = st.number_input("年齢", min_value=18, max_value=80, value=30)
        new_email = st.text_input("メールアドレス", placeholder="yamada@example.com")
        new_phone = st.text_input("電話番号", placeholder="090-0000-0000")
    with col2:
        new_location = st.text_input("居住地", placeholder="東京都新宿区")
        new_desired_loc = st.text_input("希望勤務地（カンマ区切り）", placeholder="東京都23区内, リモート可")
        new_exp_years = st.number_input("経験年数", min_value=0, max_value=50, value=3)
        new_emp_type = st.selectbox("雇用形態", ["正社員", "契約社員", "業務委託", "派遣"])
        new_registered_at = st.date_input("登録日", value=date.today())
    with col3:
        new_unit_price_min = st.number_input("希望最低単価（万円/月）", min_value=0, max_value=300, value=60)
        new_unit_price_max = st.number_input("希望最高単価（万円/月）", min_value=0, max_value=300, value=90)
        # スキル
        st.markdown("**スキル（カンマ区切り）**")
        new_lang = st.text_input("プログラミング言語", placeholder="Python, SQL")
        new_fw = st.text_input("フレームワーク", placeholder="Django, React")
        new_tools = st.text_input("ツール", placeholder="Docker, Git")
        new_certs = st.text_input("資格", placeholder="基本情報技術者")

    new_self_pr = st.text_area("自己PR", placeholder="自己PR・備考")
    new_industry = st.text_input("直近の業界", placeholder="IT・通信")

    submitted = st.form_submit_button("登録", use_container_width=True)
    if submitted:
        if not new_id or not new_name:
            st.error("IDと氏名は必須です")
        else:
            resume_data = {
                "id": new_id,
                "name": new_name,
                "age": new_age,
                "email": new_email,
                "phone": new_phone,
                "location": new_location,
                "desired_locations": [x.strip() for x in new_desired_loc.split(",") if x.strip()],
                "education": [],
                "work_history": [
                    {
                        "company": "",
                        "position": "",
                        "start_date": "",
                        "end_date": None,
                        "description": new_self_pr,
                        "industry": new_industry,
                    }
                ],
                "skills": {
                    "languages": [x.strip() for x in new_lang.split(",") if x.strip()],
                    "frameworks": [x.strip() for x in new_fw.split(",") if x.strip()],
                    "tools": [x.strip() for x in new_tools.split(",") if x.strip()],
                    "certifications": [x.strip() for x in new_certs.split(",") if x.strip()],
                    "other": [],
                },
                "years_of_experience": new_exp_years,
                "desired_unit_price_min": int(new_unit_price_min),
                "desired_unit_price_max": int(new_unit_price_max),
                "employment_type": new_emp_type,
                "self_pr": new_self_pr,
                "registered_at": new_registered_at.isoformat(),
            }
            try:
                resp = requests.post(f"{API_BASE}/resumes", json=resume_data)
                if resp.status_code == 201:
                    st.success(f"経歴書 '{new_name}' を登録しました")
                    st.rerun()
                elif resp.status_code == 409:
                    st.error(f"ID '{new_id}' は既に存在します")
                else:
                    st.error(f"登録に失敗しました: {resp.text}")
            except Exception as e:
                st.error(f"API接続エラー: {e}")
