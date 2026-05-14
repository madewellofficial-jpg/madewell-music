#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MADEWELL AI BOARDROOM v0.3
Streamlit 브라우저 UI — Live War Room
실행: streamlit run app.py
"""

from __future__ import annotations

import html
import traceback
from pathlib import Path

import streamlit as st
import boardroom_engine as engine

st.set_page_config(
    page_title="MADEWELL AI BOARDROOM",
    page_icon="🎙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ────────────────────────────────────────────
# Style
# ────────────────────────────────────────────

st.markdown("""
<style>
  .stApp { background-color: #0d0d0d; color: #e8e8e8; }
  .boardroom-header { text-align:center; padding:30px 0 8px 0; }
  .boardroom-header h1 { font-size:2.1rem; font-weight:900; letter-spacing:3px; color:#f8f8f8; margin:0; }
  .boardroom-header p { color:#777; font-size:0.82rem; margin:8px 0 0 0; letter-spacing:1.2px; }
  hr { border-color:#222; }

  .board-card {
    border-radius:14px; padding:20px 24px; margin-bottom:18px;
    border-left:5px solid; background:#181818; color:#eaeaea;
    font-size:0.96rem; line-height:1.75; box-shadow:0 0 0 1px rgba(255,255,255,.03);
  }
  .board-card h4 { margin:0 0 12px 0; font-size:1.05rem; letter-spacing:.4px; }
  .card-claude { border-color:#4a9eff; } .card-claude h4 { color:#4a9eff; }
  .card-gemini { border-color:#a855f7; } .card-gemini h4 { color:#a855f7; }
  .card-gpt { border-color:#22c55e; } .card-gpt h4 { color:#22c55e; }
  .card-redteam { border-color:#ef4444; } .card-redteam h4 { color:#ef4444; }
  .card-claude2 { border-color:#60a5fa; } .card-claude2 h4 { color:#60a5fa; }
  .card-gemini2 { border-color:#c084fc; } .card-gemini2 h4 { color:#c084fc; }
  .card-issue { border-color:#eab308; background:#1c1809; } .card-issue h4 { color:#eab308; }
  .card-final { border-color:#f59e0b; background:#1e1a0e; } .card-final h4 { color:#f59e0b; }

  .status-card { background:#111827; border:1px solid #1f2937; border-radius:10px; padding:13px 16px; color:#9ca3af; margin:8px 0 14px 0; }
  .mini-note { color:#555; font-size:.8rem; }
  .api-ok { color:#22c55e; font-size:.82rem; }
  .api-fail { color:#ef4444; font-size:.82rem; }
  .mode-badge { display:inline-block; padding:5px 12px; border-radius:20px; font-size:.74rem; font-weight:800; letter-spacing:1px; margin-right:6px; }
  .badge-quick { background:#1e3a5f; color:#7cc4ff; }
  .badge-standard { background:#11311e; color:#34d399; }
  .badge-debate { background:#3b2308; color:#f59e0b; }
  .badge-crisis { background:#3d0a0a; color:#ef4444; }

  .stButton > button { width:100%; background:linear-gradient(135deg,#1a3a6e,#2d1a5e); color:#f2f2f2; border:1px solid #333; border-radius:9px; padding:14px; font-weight:800; letter-spacing:.8px; }
  .stButton > button:hover { background:linear-gradient(135deg,#2a5aae,#4d3a8e); border-color:#555; }
  textarea, input { font-family: -apple-system, BlinkMacSystemFont, 'Pretendard', sans-serif !important; }
</style>
""", unsafe_allow_html=True)

LABELS = {
    "task_lock": ("card-issue", "🔒 Round 0 — Task Lock / 안건 고정"),
    "branch_map": ("card-issue", "💣 Round 0.5 — 100-Branch 가설 지도"),
    "claude_1": ("card-claude", "🔵 Round 1 — Claude 최초 주장 / 브랜드·감정·카피"),
    "gemini_1": ("card-gemini", "🟣 Round 1 — Gemini 반박 / 대중성·트렌드"),
    "gpt_1": ("card-gpt", "🟢 Round 1 — GPT 검증 / 숫자·ROI·리스크"),
    "cross_attack": ("card-redteam", "⚔️ Round 2 — Cross Attack / 상호 공격"),
    "steelman": ("card-claude2", "🛡 Round 3 — Steelman / 상대 주장 강화"),
    "revision": ("card-gemini2", "🔧 Round 4 — Revision / 수정안 제출"),
    "red_team": ("card-redteam", "🔴 Round 5 — Red Team / 실패 가능성 공격"),
    "score_table": ("card-issue", "📊 Round 6 — Convergence Scoring / 수렴 점수화"),
    "final_negotiation": ("card-gpt", "🤝 Round 7 — Final Negotiation / 최종 협상"),
    "continuation_check": ("card-issue", "🧭 Continuation Check — 더 토론할지 판단"),
    "adaptive_loop": ("card-redteam", "♻️ Adaptive Extra Rounds — 조건부 추가 재공방"),
    "claude_2": ("card-claude2", "🔵 Round 3 — Claude 재반박 / 수정 전략"),
    "gemini_2": ("card-gemini2", "🟣 Round 3 — Gemini 재평가 / 플랫폼 검증"),
    "issue_table": ("card-issue", "⚖️ Round 4 — 쟁점 테이블 / 폐기·채택·수정 판정"),
    "final": ("card-final", "📋 Final Arbiter — 최종 결론 & 실행 플랜"),
}
ORDER = ["task_lock", "branch_map", "claude_1", "gemini_1", "gpt_1", "cross_attack", "steelman", "revision", "red_team", "score_table", "final_negotiation", "continuation_check", "adaptive_loop", "claude_2", "gemini_2", "issue_table", "final"]


def render_card(card_class: str, title: str, content: str):
    safe_title = html.escape(title)
    safe_content = html.escape("" if content is None else str(content)).replace("\n", "<br>")
    html_block = f'''<div class="board-card {card_class}">
      <h4>{safe_title}</h4>
      <div style="white-space: normal; word-break: keep-all;">{safe_content}</div>
    </div>'''
    st.markdown(html_block, unsafe_allow_html=True)


def render_result_by_key(key: str, content: str):
    card_class, title = LABELS.get(key, ("board-card", key))
    render_card(card_class, title, content)

# ────────────────────────────────────────────
# Header
# ────────────────────────────────────────────

st.markdown("""
<div class="boardroom-header">
  <h1>🎙 MADEWELL AI BOARDROOM</h1>
  <p>CLAUDE × GEMINI × GPT — LIVE WAR ROOM v0.3.9 ADAPTIVE ENDLESS + IMAGE UPLOAD</p>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# ────────────────────────────────────────────
# Sidebar
# ────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ 회의 설정")
    st.markdown("---")

    keys = engine.check_keys()
    st.markdown("**API 키 상태**")
    st.markdown(f"{'<span class=api-ok>✅ Claude</span>' if keys['claude'] else '<span class=api-fail>❌ Claude</span>'}", unsafe_allow_html=True)
    st.markdown(f"{'<span class=api-ok>✅ OpenAI GPT</span>' if keys['openai'] else '<span class=api-fail>❌ OpenAI GPT</span>'}", unsafe_allow_html=True)
    if keys.get('gemini_enabled'):
        st.markdown(f"{'<span class=api-ok>✅ Gemini API ON</span>' if keys.get('gemini_key_present') else '<span class=api-fail>❌ Gemini Key 없음</span>'}", unsafe_allow_html=True)
    else:
        st.markdown("<span class=api-ok>✅ Gemini 역할: GPT 안전 대체</span>", unsafe_allow_html=True)
    st.caption("※ Gemini API가 꺼져 있거나 실패하면 GPT가 Gemini 역할을 안전 대체합니다. 실제 Gemini를 쓰려면 .env에서 USE_GEMINI_API=1로 설정하세요.")
    st.markdown("---")

    mode_options = {
        "⚡ Quick — 빠른 2AI 판단": "quick",
        "📊 Standard — 3AI 검증": "standard",
        "⚔️ Debate — Live War Room": "debate",
        "♾ Endless Debate — 끝장토론": "endless",
        "⚖️ Adaptive Endless — 조건부 연장 끝장토론": "adaptive",
        "💣 100-Branch Debate — 100가설 끝장토론": "branch100",
        "🚨 Crisis — 비상 전쟁회의": "crisis",
    }
    selected_mode_label = st.selectbox("회의 모드", list(mode_options.keys()), index=2)
    selected_mode = mode_options[selected_mode_label]
    desc = {
        "quick": "Claude → Gemini → GPT Final. 빠른 초안/카피용.",
        "standard": "Claude → Gemini → GPT → 쟁점판정 → Final. 기본 전략용.",
        "debate": "Claude → Gemini → GPT → Red Team → Claude 재반박 → Gemini 재평가 → 쟁점판정 → Final.",
        "endless": "Task Lock → 최초 주장 → 상호공격 → Steelman → 수정안 → Red Team → 점수화 → 최종협상 → Final.",
        "branch100": "100개 가설/실패경로를 먼저 펼친 뒤 상위 10개만 놓고 끝장토론.",
        "adaptive": "끝장토론 후 새 반박/점수 변화/미해결 쟁점이 있으면 조건부로 추가 재공방. 최대 라운드 안에서만 연장.",
        "crisis": "Debate 전체 + 생존/위기 프레임. 광고비/프리오더 비상 시.",
    }
    st.caption(desc[selected_mode])

    adaptive_extra_rounds = 0
    if selected_mode in ["adaptive", "branch100"]:
        adaptive_extra_rounds = st.slider(
            "조건부 추가 재공방 최대 횟수",
            min_value=0, max_value=4, value=2, step=1,
            help="무한 토론 방지용 상한입니다. 새 반박/점수 변화/미해결 쟁점이 있을 때만 이 횟수 안에서 추가로 돕니다."
        )

    category = st.selectbox(
        "안건 종류",
        ["📣 광고 (Meta/Instagram)", "💿 앨범 프리오더", "📝 블로그 SEO", "🎬 릴스/콘텐츠", "💰 수익/가격 전략", "🧠 AI 회의실 개선", "🎯 기타"],
        index=0,
    )

    st.markdown("---")
    st.markdown("**context 로딩 상태**")
    total_chars = 0
    for row in engine.get_context_file_status():
        total_chars += row["chars"]
        icon = "✅" if row["exists"] else "❌"
        st.caption(f"{icon} {row['file']} · {row['chars']}자")
    st.caption(f"총 context: 약 {total_chars:,}자 + 최근 회의록 요약")

    st.markdown("---")
    st.markdown("**저장/인수인계**")
    latest_handoff = engine.get_latest_handoff()
    if latest_handoff:
        with st.expander("📤 최근 람보 인수인계 보기"):
            st.code(latest_handoff, language="text")

# ────────────────────────────────────────────
# Input
# ────────────────────────────────────────────

profile = engine.load_profile()

# ────────────────────────────────────────────
# Image Upload → GPT Vision Summary
# ────────────────────────────────────────────

if "image_summary" not in st.session_state:
    st.session_state.image_summary = ""
if "image_summary_error" not in st.session_state:
    st.session_state.image_summary_error = ""

st.markdown("#### 📎 캡쳐/이미지 자료 자동 요약")
st.caption("메타 광고 관리자, 인스타 인사이트, 결제/프리오더 현황 캡쳐를 올리면 GPT Vision이 회의실 입력용 텍스트로 요약합니다. API 키/개인정보가 보이는 캡쳐는 올리기 전에 가리는 것을 권장합니다.")
uploaded_images = st.file_uploader(
    "이미지 업로드",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)
img_btn_col1, img_btn_col2 = st.columns([1, 1])
with img_btn_col1:
    summarize_images = st.button("📎 이미지 요약해서 현재 상황에 삽입", use_container_width=True, disabled=not uploaded_images)
with img_btn_col2:
    clear_img_summary = st.button("🧹 이미지 요약 지우기", use_container_width=True, disabled=not bool(st.session_state.image_summary))

if clear_img_summary:
    st.session_state.image_summary = ""
    st.session_state.image_summary_error = ""
    st.rerun()

if summarize_images and uploaded_images:
    try:
        payloads = []
        for uf in uploaded_images[:6]:
            payloads.append({
                "name": uf.name,
                "mime_type": uf.type or "image/png",
                "data": uf.getvalue(),
            })
        with st.spinner("이미지 자료를 GPT Vision으로 읽고 회의실 입력용으로 정리하는 중..."):
            summary = engine.summarize_uploaded_images(payloads, agenda_hint=profile.get("agenda", ""))
        st.session_state.image_summary = summary
        st.session_state.image_summary_error = ""
        st.rerun()
    except Exception as e:
        st.session_state.image_summary_error = str(e)

if st.session_state.image_summary_error:
    st.error(f"이미지 요약 실패: {st.session_state.image_summary_error}")

if st.session_state.image_summary:
    with st.expander("📎 이미지 자동 요약 결과 보기", expanded=False):
        st.code(st.session_state.image_summary, language="text")


col1, col2 = st.columns([3, 2])
with col1:
    st.markdown("#### 📌 오늘의 안건")
    agenda = st.text_area(
        "안건",
        value=profile.get("agenda", ""),
        placeholder="예) 메타 광고 1차 실험 종료. 117,915원 소진, 메시지 12건, 결제 0명. 다음 광고를 어떻게 재설계해야 하는가?",
        height=110,
        label_visibility="collapsed",
    )
with col2:
    st.markdown("#### 📍 현재 상황")
    situation = st.text_area(
        "현재 상황",
        value=((profile.get("situation", "") + ("\n\n" if profile.get("situation", "") and st.session_state.get("image_summary") else "") + (st.session_state.get("image_summary") or ""))),
        placeholder="예) 프리오더 20/100장. 광고비 소진 중. 크몽 등록 완료. 레슨 0명.",
        height=110,
        label_visibility="collapsed",
    )

col3, col4 = st.columns(2)
with col3:
    st.markdown("#### 🤔 내가 느끼는 우려")
    concerns = st.text_area(
        "우려",
        value=profile.get("concerns", ""),
        placeholder="예) 광고 효율이 너무 낮다. 타겟이 맞는지 모르겠다. 이 말이 구걸처럼 보일까 봐 걱정된다.",
        height=90,
        label_visibility="collapsed",
    )
with col4:
    st.markdown("#### 📋 원하는 출력 형식")
    output_format = st.text_area(
        "출력 형식",
        value=profile.get("output_format", ""),
        placeholder="예) 오늘 당장 바꿀 광고 카피 3개, 새 타겟 설정, 예산 배분 제안",
        height=90,
        label_visibility="collapsed",
    )

st.markdown("#### 🛑 정균 중간 개입 / 회의 지시")
intervention = st.text_area(
    "중간 개입",
    value=profile.get("intervention", ""),
    placeholder="예) 너무 구걸처럼 보이는 표현은 폐기해라. 일본 팬에게 부담 주는 DM은 싫다. 오늘 촬영 가능 시간은 30분뿐이다.",
    height=80,
    label_visibility="collapsed",
)

btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
with btn_col2:
    start = st.button("⚔️ Live War Room 시작", use_container_width=True)

st.markdown("---")

# ────────────────────────────────────────────
# State
# ────────────────────────────────────────────

for k, default in {
    "results": None,
    "last_agenda": "",
    "last_mode": "",
    "log_path": None,
    "last_error": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = default

# ────────────────────────────────────────────
# Run
# ────────────────────────────────────────────

if start:
    if not agenda.strip():
        st.error("❌ 안건을 입력해주세요.")
    elif not keys["claude"] or not keys["openai"]:
        missing = [k for k, v in keys.items() if not v and k in ["claude", "openai"]]
        st.error(f"❌ 필수 API 키 형식이 비어 있거나 잘못되었습니다: {', '.join(missing)}")
        st.info(".env에는 최소 ANTHROPIC_API_KEY, OPENAI_API_KEY가 필요합니다. Gemini는 실패/쿼터 초과 시 GPT가 Gemini 역할로 임시 대체합니다.")
    else:
        st.session_state.results = None
        st.session_state.log_path = None
        st.session_state.last_error = None
        st.session_state.last_agenda = agenda
        st.session_state.last_mode = selected_mode

        engine.save_profile({
            "agenda": agenda,
            "situation": situation,
            "concerns": concerns,
            "output_format": output_format,
            "intervention": intervention,
        })

        status_box = st.empty()
        live_container = st.container()
        card_placeholders: dict[str, object] = {}

        with live_container:
            for key in ORDER:
                card_placeholders[key] = st.empty()

        partial_results: dict[str, str] = {}

        def update_progress(msg: str):
            status_box.markdown(f"<div class='status-card'>⏳ {html.escape(msg)}</div>", unsafe_allow_html=True)

        def add_live_result(key: str, content: str):
            content = "" if content is None else str(content)
            partial_results[key] = content
            with card_placeholders[key].container():
                render_result_by_key(key, content)

        try:
            if selected_mode == "quick":
                results = engine.run_quick(agenda, category, situation, concerns, output_format, intervention, update_progress, add_live_result)
            elif selected_mode == "standard":
                results = engine.run_standard(agenda, category, situation, concerns, output_format, intervention, update_progress, add_live_result)
            elif selected_mode == "debate":
                results = engine.run_debate(agenda, category, situation, concerns, output_format, intervention, crisis=False, progress_cb=update_progress, result_cb=add_live_result)
            elif selected_mode == "endless":
                results = engine.run_endless_debate(agenda, category, situation, concerns, output_format, intervention, branch100=False, progress_cb=update_progress, result_cb=add_live_result)
            elif selected_mode == "adaptive":
                results = engine.run_endless_debate(agenda, category, situation, concerns, output_format, intervention, branch100=False, adaptive=True, max_extra_rounds=adaptive_extra_rounds, progress_cb=update_progress, result_cb=add_live_result)
            elif selected_mode == "branch100":
                results = engine.run_endless_debate(agenda, category, situation, concerns, output_format, intervention, branch100=True, adaptive=True, max_extra_rounds=adaptive_extra_rounds, progress_cb=update_progress, result_cb=add_live_result)
            else:
                results = engine.run_crisis(agenda, category, situation, concerns, output_format, intervention, progress_cb=update_progress, result_cb=add_live_result)

            log_path = engine.save_log(agenda, selected_mode, category, situation, concerns, output_format, intervention, results)
            st.session_state.results = results
            st.session_state.log_path = str(log_path)
            status_box.markdown("<div class='status-card'>✅ 회의 완료. 회의록과 람보 인수인계 파일이 저장되었습니다.</div>", unsafe_allow_html=True)
            st.rerun()

        except Exception as e:
            status_box.empty()
            st.session_state.last_error = str(e)
            st.error(f"❌ 오류 발생: {e}")
            with st.expander("🔎 오류 상세 보기"):
                st.code(traceback.format_exc(), language="python")
            st.info("API 키 문제가 아니라 모델 호출/네트워크/패키지/Gemini 엔드포인트 문제일 수 있습니다. 위 상세 오류를 람보에게 보내면 됩니다.")

# ────────────────────────────────────────────
# Results
# ────────────────────────────────────────────

if st.session_state.results:
    mode = st.session_state.last_mode
    badge_class = f"badge-{mode}"
    st.markdown(f"<span class='mode-badge {badge_class}'>{mode.upper()}</span> <span class='mini-note'>{html.escape(st.session_state.last_agenda[:80])}</span>", unsafe_allow_html=True)
    st.markdown("")

    for key in ORDER:
        if key in st.session_state.results:
            render_result_by_key(key, st.session_state.results[key])

    if st.session_state.log_path:
        st.markdown(f"<p class='mini-note'>💾 회의록 저장됨: {html.escape(st.session_state.log_path)}</p>", unsafe_allow_html=True)

    handoff = engine.get_latest_handoff()
    if handoff:
        st.markdown("### 📤 람보 인수인계용 요약")
        st.code(handoff, language="text")
        st.caption("이 블록만 복사해서 ChatGPT 람보에게 붙여넣으면 이어받기 쉽습니다.")

    if st.button("🔄 새 안건으로 다시 시작"):
        st.session_state.results = None
        st.session_state.log_path = None
        st.rerun()

elif not st.session_state.last_error:
    st.markdown("""
    <div style="text-align:center; padding:56px 0; color:#333;">
      <div style="font-size:3rem;">🎙</div>
      <div style="font-size:1.1rem; color:#555; margin-top:12px;">안건을 입력하고 Live War Room을 시작하세요</div>
      <div style="font-size:0.82rem; color:#444; margin-top:8px;">이번 버전은 Task Lock / API Health Check / 이미지 업로드 / Endless Debate / 100-Branch / Adaptive Continuation을 포함합니다.</div>
    </div>
    """, unsafe_allow_html=True)
