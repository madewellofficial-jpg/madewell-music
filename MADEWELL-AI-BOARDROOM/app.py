#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MADEWELL AI BOARDROOM v0.2
Streamlit 브라우저 UI
실행: streamlit run app.py
"""

import streamlit as st
import boardroom_engine as engine

# ────────────────────────────────────────────
# 페이지 설정
# ────────────────────────────────────────────

st.set_page_config(
    page_title="MADEWELL AI BOARDROOM",
    page_icon="🎙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ────────────────────────────────────────────
# 전역 스타일
# ────────────────────────────────────────────

st.markdown("""
<style>
  /* 배경 */
  .stApp { background-color: #0d0d0d; }

  /* 카드 공통 */
  .board-card {
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 18px;
    border-left: 5px solid;
    background: #1a1a1a;
    color: #e8e8e8;
    font-size: 0.95rem;
    line-height: 1.7;
  }
  .board-card h4 { margin: 0 0 10px 0; font-size: 1.05rem; letter-spacing: 0.5px; }

  .card-claude   { border-color: #4a9eff; }
  .card-gemini   { border-color: #a855f7; }
  .card-gpt      { border-color: #22c55e; }
  .card-redteam  { border-color: #ef4444; }
  .card-claude2  { border-color: #60a5fa; }
  .card-final    { border-color: #f59e0b; background: #1e1a0e; }

  .card-claude   h4 { color: #4a9eff; }
  .card-gemini   h4 { color: #a855f7; }
  .card-gpt      h4 { color: #22c55e; }
  .card-redteam  h4 { color: #ef4444; }
  .card-claude2  h4 { color: #60a5fa; }
  .card-final    h4 { color: #f59e0b; }

  /* 헤더 */
  .boardroom-header {
    text-align: center;
    padding: 32px 0 8px 0;
  }
  .boardroom-header h1 {
    font-size: 2.2rem;
    font-weight: 800;
    letter-spacing: 2px;
    color: #f8f8f8;
    margin: 0;
  }
  .boardroom-header p {
    color: #666;
    font-size: 0.85rem;
    margin: 6px 0 0 0;
    letter-spacing: 1px;
  }

  /* 모드 배지 */
  .mode-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 1px;
    margin-right: 6px;
  }
  .badge-quick    { background:#1e3a5f; color:#4a9eff; }
  .badge-standard { background:#1a2e1a; color:#22c55e; }
  .badge-debate   { background:#2d1a1a; color:#f59e0b; }
  .badge-crisis   { background:#3d0a0a; color:#ef4444; }

  /* 입력 레이블 */
  .stTextInput label, .stTextArea label, .stSelectbox label {
    color: #999 !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.5px !important;
  }

  /* 구분선 */
  hr { border-color: #222; }

  /* 사이드바 */
  .css-1d391kg, section[data-testid="stSidebar"] {
    background-color: #111 !important;
  }

  /* 버튼 */
  .stButton > button {
    width: 100%;
    background: linear-gradient(135deg, #1a3a6e, #2d1a5e);
    color: #e8e8e8;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 14px;
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: 1px;
    transition: all 0.2s;
  }
  .stButton > button:hover {
    background: linear-gradient(135deg, #2a5aae, #4d3a8e);
    border-color: #555;
  }

  /* API 상태 */
  .api-ok   { color: #22c55e; font-size: 0.8rem; }
  .api-fail { color: #ef4444; font-size: 0.8rem; }

  /* Provider 배지 */
  .provider-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.72rem;
    color: #888;
    margin-bottom: 10px;
    padding: 3px 8px;
    background: #111;
    border-radius: 4px;
    border: 1px solid #2a2a2a;
    letter-spacing: 0.3px;
  }
  .provider-badge .prov { color: #aaa; font-weight: 600; }
  .provider-badge .mdl  { color: #666; }
  .provider-badge .fb-ok  { color: #22c55e; }
  .provider-badge .fb-warn { color: #f59e0b; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# ────────────────────────────────────────────
# 헬퍼: 카드 렌더링
# ────────────────────────────────────────────

def render_card(card_class: str, title: str, content: str, meta: dict = None):
    safe = content.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

    badge_html = ""
    if meta:
        provider = meta.get("provider", "?")
        model    = meta.get("model", "?")
        fallback = meta.get("fallback", False)
        fb_reason = meta.get("fallback_reason", "")

        if fallback:
            fb_html = f'<span class="fb-warn">⚠ FALLBACK ({fb_reason})</span>'
        else:
            fb_html = '<span class="fb-ok">✓ 직접 호출</span>'

        badge_html = f"""
        <div class="provider-badge">
          <span class="prov">{provider}</span>
          <span style="color:#333;">|</span>
          <span class="mdl">{model}</span>
          <span style="color:#333;">|</span>
          {fb_html}
        </div>"""

    st.markdown(f"""
    <div class="board-card {card_class}">
      <h4>{title}</h4>
      {badge_html}
      <div>{safe}</div>
    </div>
    """, unsafe_allow_html=True)


# ────────────────────────────────────────────
# 헤더
# ────────────────────────────────────────────

st.markdown("""
<div class="boardroom-header">
  <h1>🎙 MADEWELL AI BOARDROOM</h1>
  <p>CLAUDE × GEMINI × GPT — 전략 토론 시스템 v0.4 · Provider Verified</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")


# ────────────────────────────────────────────
# 사이드바
# ────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ 회의 설정")
    st.markdown("---")

    # API 상태
    keys = engine.check_keys()
    st.markdown("**API 연결 상태**")
    st.markdown(f"{'<span class=api-ok>✅ Claude</span>' if keys['claude'] else '<span class=api-fail>❌ Claude (키 없음)</span>'}", unsafe_allow_html=True)
    st.markdown(f"{'<span class=api-ok>✅ OpenAI GPT</span>' if keys['openai'] else '<span class=api-fail>❌ OpenAI (키 없음)</span>'}", unsafe_allow_html=True)
    st.markdown(f"{'<span class=api-ok>✅ Gemini</span>' if keys['gemini'] else '<span class=api-fail>❌ Gemini (키 없음)</span>'}", unsafe_allow_html=True)
    st.markdown("---")

    # 모드 선택
    st.markdown("**회의 모드**")
    mode_options = {
        "⚡ Quick — Claude + Gemini + 정리 (~30초)": "quick",
        "📊 Standard — 3AI 토론 + 정리 (~60초)": "standard",
        "⚔️ Debate — 풀 토론 + Red Team (~90초)": "debate",
        "🚨 Crisis — 비상 모드, 생존 전략 (~90초)": "crisis",
    }
    selected_mode_label = st.selectbox(
        "모드 선택",
        list(mode_options.keys()),
        index=1,
        label_visibility="collapsed"
    )
    selected_mode = mode_options[selected_mode_label]

    mode_desc = {
        "quick":    "Claude + Gemini 분석 → Secretary 정리. 빠른 판단용.",
        "standard": "Claude → Gemini → GPT 반박 → Secretary. 기본 전략 회의.",
        "debate":   "Claude → Gemini → GPT → Red Team → Claude 2차 → Secretary. 중요 결정용.",
        "crisis":   "Debate 전체 + Crisis 프레임. 돈/시간 없을 때 생존 전략.",
    }
    st.caption(mode_desc[selected_mode])

    st.markdown("---")

    # 안건 종류
    st.markdown("**안건 종류**")
    category = st.selectbox(
        "안건 종류",
        ["📣 광고 (Meta/Instagram)", "💿 앨범 프리오더", "📝 블로그 SEO", "🎬 릴스/콘텐츠", "💰 수익/가격 전략", "🎯 기타"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("**context 파일 상태**")
    from pathlib import Path
    ctx_dir = Path(__file__).parent / "context"
    ctx_files = [
        "madewell_profile.md", "current_projects.md", "meta_ads_history.md",
        "album_preorder_status.md", "brand_rules.md", "pricing_services.md"
    ]
    for f in ctx_files:
        exists = (ctx_dir / f).exists()
        icon = "✅" if exists else "❌"
        st.caption(f"{icon} {f}")


# ────────────────────────────────────────────
# 메인 입력 영역
# ────────────────────────────────────────────

col1, col2 = st.columns([3, 2])

with col1:
    st.markdown("#### 📌 오늘의 안건")
    agenda = st.text_area(
        "안건",
        placeholder="예) 메타 광고 1차 실험 종료. 117,915원 소진, 메시지 12건, 결제 0명. 다음 광고를 어떻게 재설계해야 하는가?",
        height=100,
        label_visibility="collapsed"
    )

with col2:
    st.markdown("#### 📍 현재 상황")
    situation = st.text_area(
        "현재 상황",
        placeholder="예) 프리오더 20/100장. 광고비 소진 중. 크몽 등록 완료. 레슨 0명.",
        height=100,
        label_visibility="collapsed"
    )

col3, col4 = st.columns([1, 1])

with col3:
    st.markdown("#### 🤔 내가 느끼는 우려")
    concerns = st.text_area(
        "우려",
        placeholder="예) 광고 효율이 너무 낮다. 타겟이 맞는지 모르겠다. 예산이 얼마 안 남았다.",
        height=80,
        label_visibility="collapsed"
    )

with col4:
    st.markdown("#### 📋 원하는 출력 형식")
    output_format = st.text_area(
        "출력 형식",
        placeholder="예) 오늘 당장 바꿀 광고 카피 3개, 새 타겟 설정, 예산 배분 제안",
        height=80,
        label_visibility="collapsed"
    )

st.markdown("")

# 회의 시작 버튼
btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
with btn_col2:
    start = st.button("🎙 회의 시작", use_container_width=True)

st.markdown("---")


# ────────────────────────────────────────────
# 세션 상태 초기화
# ────────────────────────────────────────────

if "results" not in st.session_state:
    st.session_state.results = None
if "last_agenda" not in st.session_state:
    st.session_state.last_agenda = ""
if "last_mode" not in st.session_state:
    st.session_state.last_mode = ""
if "log_path" not in st.session_state:
    st.session_state.log_path = None


# ────────────────────────────────────────────
# 회의 실행
# ────────────────────────────────────────────

if start:
    if not agenda.strip():
        st.error("❌ 안건을 입력해주세요.")
    elif not all(keys.values()):
        missing = [k for k, v in keys.items() if not v]
        st.error(f"❌ API 키가 없습니다: {', '.join(missing)} — .env 파일을 확인해주세요.")
    else:
        st.session_state.results = None
        st.session_state.last_agenda = agenda
        st.session_state.last_mode = selected_mode

        progress_placeholder = st.empty()
        status_text = st.empty()

        def update_progress(msg: str):
            status_text.markdown(f"<p style='color:#666;font-size:0.9rem;'>⏳ {msg}</p>", unsafe_allow_html=True)

        with st.spinner(""):
            try:
                if selected_mode == "quick":
                    results = engine.run_quick(agenda, category, situation, concerns, output_format, update_progress)
                elif selected_mode == "standard":
                    results = engine.run_standard(agenda, category, situation, concerns, output_format, update_progress)
                elif selected_mode == "debate":
                    results = engine.run_debate(agenda, category, situation, concerns, output_format, crisis=False, progress_cb=update_progress)
                elif selected_mode == "crisis":
                    results = engine.run_crisis(agenda, category, situation, concerns, output_format, update_progress)

                log_path = engine.save_log(agenda, selected_mode, category, results)
                st.session_state.results = results
                st.session_state.log_path = str(log_path)
                status_text.empty()

            except Exception as e:
                status_text.empty()
                st.error(f"❌ 오류 발생: {str(e)}")
                st.info("💡 .env 파일에 API 키가 올바르게 설정되어 있는지 확인해주세요.")


# ────────────────────────────────────────────
# 결과 출력
# ────────────────────────────────────────────

if st.session_state.results:
    results = st.session_state.results
    mode = st.session_state.last_mode
    agenda_shown = st.session_state.last_agenda

    badge_class = f"badge-{mode}"
    st.markdown(f"""
    <div style="margin-bottom:20px;">
      <span class="mode-badge {badge_class}">{mode.upper()}</span>
      <span style="color:#888;font-size:0.9rem;">{agenda_shown[:60]}{'...' if len(agenda_shown) > 60 else ''}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Claude 1차 ──
    if "claude_1" in results:
        render_card("card-claude", "🔵 Claude — 크리에이티브 / 브랜드 / 감성 전략",
                    results["claude_1"], results.get("claude_1_meta"))

    # ── Gemini ──
    if "gemini_1" in results:
        render_card("card-gemini", "🟣 Gemini — 대중성 / 트렌드 / 소비자 심리 분석",
                    results["gemini_1"], results.get("gemini_1_meta"))

    # ── GPT ──
    if "gpt_1" in results:
        render_card("card-gpt", "🟢 GPT — 퍼포먼스 / ROI / 리스크 반박",
                    results["gpt_1"], results.get("gpt_1_meta"))

    # ── Red Team ──
    if "red_team" in results:
        render_card("card-redteam", "🔴 Red Team — 실패 가능성 공격",
                    results["red_team"], results.get("red_team_meta"))

    # ── Claude 2차 ──
    if "claude_2" in results:
        render_card("card-claude2", "🔵 Claude 2차 — GPT 반박 검토 & 전략 수정",
                    results["claude_2"], results.get("claude_2_meta"))

    # ── 최종 결론 ──
    if "final" in results:
        st.markdown("---")
        render_card("card-final", "📋 Secretary — 최종 결론 & 실행 플랜",
                    results["final"], results.get("final_meta"))

    # 로그 경로 안내
    if st.session_state.log_path:
        st.markdown(f"<p style='color:#444;font-size:0.78rem;margin-top:12px;'>💾 회의록 저장됨: {st.session_state.log_path}</p>", unsafe_allow_html=True)

    # 다시 하기
    st.markdown("")
    if st.button("🔄 새 안건으로 다시 시작"):
        st.session_state.results = None
        st.session_state.last_agenda = ""
        st.rerun()

else:
    # 안내 화면
    st.markdown("""
    <div style="text-align:center; padding:60px 0; color:#333;">
      <div style="font-size:3rem;">🎙</div>
      <div style="font-size:1.1rem; color:#555; margin-top:12px;">안건을 입력하고 회의를 시작하세요</div>
      <div style="font-size:0.82rem; color:#444; margin-top:8px;">Claude × Gemini × GPT가 전략을 토론합니다</div>
    </div>
    """, unsafe_allow_html=True)
