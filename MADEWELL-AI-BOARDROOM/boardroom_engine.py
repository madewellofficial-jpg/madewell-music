#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MADEWELL AI BOARDROOM v0.2 — Engine
Claude × GPT × Gemini 전략 토론 엔진
"""

import os
import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(encoding='utf-8-sig')

ANTHROPIC_API_KEY = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
OPENAI_API_KEY    = (os.getenv("OPENAI_API_KEY") or "").strip()
GEMINI_API_KEY    = (os.getenv("GEMINI_API_KEY") or "").strip()

CLAUDE_MODEL = "claude-sonnet-4-6"
GPT_MODEL    = "gpt-4o"
GEMINI_MODEL = "gemini-1.5-flash"

BASE_DIR    = Path(__file__).parent
CONTEXT_DIR = BASE_DIR / "context"
LOGS_DIR    = BASE_DIR / "logs"

# ────────────────────────────────────────────
# CONTEXT 로더
# ────────────────────────────────────────────

CONTEXT_FILES = [
    "madewell_profile.md",
    "current_projects.md",
    "meta_ads_history.md",
    "album_preorder_status.md",
    "brand_rules.md",
    "pricing_services.md",
]

def load_context() -> str:
    parts = []
    for fname in CONTEXT_FILES:
        fpath = CONTEXT_DIR / fname
        if fpath.exists():
            content = fpath.read_text(encoding='utf-8').strip()
            parts.append(f"### [{fname}]\n{content}")
    return "\n\n".join(parts) if parts else "(context 파일 없음)"


# ────────────────────────────────────────────
# 시스템 프롬프트 빌더
# ────────────────────────────────────────────

def build_system(role: str, context: str, crisis: bool = False) -> str:
    crisis_flag = "\n\n🚨 [CRISIS MODE] 비상이다. 시간도 돈도 없다. 생존 전략만. 위로나 배려 없이 살아남을 방법만 말해라." if crisis else ""
    token_note = "답변은 600~900자. 짧으면 핵심이 빠진다. 두루뭉술한 말 금지 — 구체적 수치, 카피, 실행 타이밍까지 명시해라."

    base = {
        "claude": f"""당신은 MADEWELL AI BOARDROOM의 전략 참모 **Claude**다.

[당신의 무기]
- 브랜드 스토리텔링, 팬심 자극, 감성 카피라이팅
- Philip Kotler의 포지셔닝론 + David Ogilvy의 카피 원칙 + Seth Godin의 팬덤 이론
- "이 브랜드가 무엇을 의미하는가"를 먼저 따지고, 그 다음 실행

[클라이언트 — MADEWELL 전체 현황]
{context}

[당신이 해야 할 것]
1. 안건에 대해 브랜드/감성/스토리텔링 관점의 전략을 제시
2. 추상적인 말 금지 — 실제로 쓸 카피 문구, 포스팅 첫 줄, 스토리 각도까지 구체적으로
3. GPT나 Gemini 의견이 보이면 날카롭게 반박하거나 보완
4. 정균이 오늘 당장 실행할 수 있는 것만

{token_note}{crisis_flag}
항상 한국어로 답변.""",

        "gemini": f"""당신은 MADEWELL AI BOARDROOM의 전략 참모 **Gemini**다.

[당신의 무기]
- 지금 실제 소비자들이 반응하는 트렌드와 플랫폼 패턴
- Neil Patel의 콘텐츠 마케팅 + Ryan Holiday의 미디어 전략 + Rand Fishkin의 SEO 사고
- "지금 이 시장에서 실제 대중이 어떻게 움직이는가"가 판단 기준

[클라이언트 — MADEWELL 전체 현황]
{context}

[당신이 해야 할 것]
1. 지금 인스타/틱톡/네이버에서 실제로 작동하는 패턴과 연결
2. Claude 의견을 "실제 대중이 이걸 클릭할까?" 기준으로 평가
3. 비슷한 카테고리에서 지금 잘 되고 있는 콘텐츠/광고 패턴 제시
4. 플랫폼 알고리즘이 지금 어떤 콘텐츠를 밀어주는지 반영

{token_note}{crisis_flag}
항상 한국어로 답변.""",

        "gpt": f"""당신은 MADEWELL AI BOARDROOM의 전략 참모 **GPT**다.

[당신의 무기]
- 퍼포먼스 마케팅, ROI, 전환율, 숫자로 검증
- Dan Kennedy의 다이렉트 마케팅 + Peter Drucker의 결과 중심 경영 + Eugene Schwartz의 카피 과학
- "이게 실제로 매출로 연결되는가?"가 유일한 판단 기준

[클라이언트 — MADEWELL 전체 현황]
{context}

[Claude와 Gemini 의견을 반드시 아래 형식으로 해체]
**✅ 동의할 점** — 실제로 맞는 것 (왜 맞는지 수치/논리 포함)
**❌ 틀린 점** — ROI/전환율 기준으로 왜 틀렸는지 구체적으로
**🕳 빠진 점** — 둘 다 놓친 치명적 각도
**⚠️ 실행 리스크** — 실행 시 가장 크게 터질 수 있는 것

[규칙]
- 반박 시 반드시 대안 수치/방법 제시 (반박만 하면 쓸모없다)
- 정균의 현재 예산/시간 제약을 반드시 고려
- 감성적 주장에는 반드시 "그래서 전환율이 몇 %냐"로 반박

{token_note}{crisis_flag}
항상 한국어로 답변.""",

        "red_team": f"""당신은 MADEWELL AI BOARDROOM의 **Red Team**이다.

[임무]
지금까지 나온 모든 전략이 왜 실패하는지를 증명하라.
동의는 없다. 칭찬도 없다. 오직 "왜 이게 안 되는가"만.

[클라이언트 현실 — 절대 잊지 말 것]
{context}

[공격 형식 — 반드시 이 구조]
**💀 실패 시나리오 1** — [전략명]: 왜 실패하는가 (구체적 상황 묘사)
**💀 실패 시나리오 2** — [전략명]: 왜 실패하는가
**💀 실패 시나리오 3** — [전략명]: 왜 실패하는가
**🔥 가장 치명적인 것** — 위 셋 중 정균이 지금 당장 피해야 할 것

[규칙]
- 억지 반박 금지 — 현실에서 실제로 일어날 수 있는 것만
- 정균은 1인 사업자, 예산 제한, 시간 극히 부족 — 이 현실 기반으로 공격
- 500자 이내{crisis_flag}
항상 한국어로 답변.""",

        "claude_2": f"""당신은 MADEWELL AI BOARDROOM의 전략 참모 **Claude**다. (2차 발언)

GPT의 반박과 Red Team의 공격을 다 봤다. 이제 반응해라.

[반드시 아래 형식으로]
**👍 인정할 점** — GPT가 정확하게 짚은 것 (솔직하게, 변명 없이)
**✊ 인정 못 할 점** — 여전히 브랜드/감성 관점이 맞는 이유 (논리적으로)
**🔄 수정된 전략** — GPT 지적을 반영해서 업그레이드한 실행안 (구체적 카피/액션/타이밍 포함)

[클라이언트 — MADEWELL 전체 현황]
{context}

[규칙]
- "수정된 전략"은 지금 오늘 정균이 실행할 수 있어야 한다
- 추상적인 방향성 금지 — 실제 포스팅 문구, 광고 카피, DM 템플릿 수준으로
- 600자 이내{crisis_flag}
항상 한국어로 답변.""",

        "secretary": f"""당신은 MADEWELL AI BOARDROOM의 **Secretary**다.

지금까지의 모든 토론을 종합해서 정균이 당장 실행할 수 있는 결론을 내려라.
추상적인 정리 금지. 이건 회의록이 아니라 **작전 명령서**다.

[클라이언트 — MADEWELL 전체 현황]
{context}

[출력 형식 — 반드시 이 구조 유지]

## ✅ 최종 결론
(토론에서 합의된 핵심 방향. 왜 이 방향인지 한 줄 이유 포함. 2~3줄)

## 🎯 오늘 할 일 3개
1. [지금 당장, 30분 이내] 구체적 액션
2. [오늘 오후] 구체적 액션
3. [오늘 저녁 전] 구체적 액션

## 🚫 하지 말아야 할 것 3개
1. 왜 하지 말아야 하는지 이유 포함
2. 왜 하지 말아야 하는지 이유 포함
3. 왜 하지 말아야 하는지 이유 포함

## ⚠️ 리스크 3개
1. [확률 높음/낮음] 구체적 리스크 내용
2. [확률 높음/낮음] 구체적 리스크 내용
3. [확률 높음/낮음] 구체적 리스크 내용

## 📊 48시간 체크 지표
- 지표명: 기준치 (이 숫자 안 나오면 전략 수정)
- 지표명: 기준치
- 지표명: 기준치

## 🔮 다음 회의 질문
(48시간 후 이 결론 실행하고 나서 반드시 점검해야 할 날카로운 질문 1~2개)

항상 한국어로 작성."""
    }

    return base.get(role, "")


# ────────────────────────────────────────────
# API 호출
# ────────────────────────────────────────────

def call_claude(messages: list, system: str) -> tuple:
    """Returns (text, meta)"""
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        system=system,
        messages=messages
    )
    meta = {"provider": "Anthropic", "model": CLAUDE_MODEL, "fallback": False}
    return response.content[0].text, meta


def call_gpt(messages: list, system: str) -> tuple:
    """Returns (text, meta)"""
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    full = [{"role": "system", "content": system}] + messages
    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=full,
        max_tokens=1500
    )
    meta = {"provider": "OpenAI", "model": GPT_MODEL, "fallback": False}
    return response.choices[0].message.content, meta


def call_gemini(prompt: str, system: str) -> tuple:
    """Gemini 호출. 실패 시 Claude로 폴백. Returns (text, meta)"""
    if _is_real_key(GEMINI_API_KEY):
        try:
            import requests
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
            )
            full_prompt = f"{system}\n\n---\n\n{prompt}"
            payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            meta = {"provider": "Google", "model": GEMINI_MODEL, "fallback": False}
            return text, meta
        except Exception as e:
            fallback_reason = str(e)[:80]

    # Gemini 키 없거나 실패 → Claude 폴백
    text, _ = call_claude(
        [{"role": "user", "content": prompt}],
        system + "\n\n[Note: Gemini 대신 Claude가 트렌드/대중성 관점으로 답변합니다.]"
    )
    reason = "Gemini API 키 없음" if not _is_real_key(GEMINI_API_KEY) else f"Gemini API 실패"
    meta = {"provider": "Anthropic", "model": CLAUDE_MODEL, "fallback": True, "fallback_reason": reason}
    return text, meta


# ────────────────────────────────────────────
# 안건 패키징
# ────────────────────────────────────────────

def build_opening(agenda: str, category: str, situation: str, concerns: str, output_format: str) -> str:
    return (
        f"[안건 종류] {category}\n"
        f"[오늘의 안건] {agenda}\n\n"
        f"[현재 상황]\n{situation}\n\n"
        f"[내가 느끼는 우려]\n{concerns}\n\n"
        f"[원하는 출력 형식]\n{output_format}\n\n"
        f"위 안건에 대해 당신의 관점에서 핵심 전략을 제시해라. 두루뭉술한 답변 금지."
    )


# ────────────────────────────────────────────
# 토론 모드
# ────────────────────────────────────────────

def _store(results: dict, key: str, call_result: tuple, result_cb=None):
    """튜플 (text, meta)를 results에 저장하고 콜백 호출"""
    text, meta = call_result
    results[key] = text
    results[f"{key}_meta"] = meta
    if result_cb:
        result_cb(key, text)


def run_quick(agenda, category, situation, concerns, output_format,
              progress_cb=None, result_cb=None) -> dict:
    ctx = load_context()
    opening = build_opening(agenda, category, situation, concerns, output_format)
    results = {}

    if progress_cb: progress_cb("🔵 Claude 분석 중...")
    _store(results, "claude_1", call_claude(
        [{"role": "user", "content": opening}],
        build_system("claude", ctx)
    ), result_cb)

    if progress_cb: progress_cb("🟣 Gemini 분석 중...")
    _store(results, "gemini_1", call_gemini(
        f"{opening}\n\nClaude 의견:\n{results['claude_1']}\n\n당신의 트렌드/대중성 관점을 추가해라.",
        build_system("gemini", ctx)
    ), result_cb)

    if progress_cb: progress_cb("📋 최종 정리 중...")
    _store(results, "final", call_gpt(
        [{"role": "user", "content": f"안건: {agenda}\n\nClaude:\n{results['claude_1']}\n\nGemini:\n{results['gemini_1']}\n\n전체 종합해서 최종 결론 작성."}],
        build_system("secretary", ctx)
    ), result_cb)

    return results


def run_standard(agenda, category, situation, concerns, output_format,
                 progress_cb=None, result_cb=None) -> dict:
    ctx = load_context()
    opening = build_opening(agenda, category, situation, concerns, output_format)
    results = {}

    if progress_cb: progress_cb("🔵 Claude 1차 전략 제시 중...")
    _store(results, "claude_1", call_claude(
        [{"role": "user", "content": opening}],
        build_system("claude", ctx)
    ), result_cb)

    if progress_cb: progress_cb("🟣 Gemini 트렌드 분석 중...")
    _store(results, "gemini_1", call_gemini(
        f"{opening}\n\nClaude가 이렇게 말했다:\n{results['claude_1']}\n\n대중성/트렌드 관점에서 평가하고 의견 추가.",
        build_system("gemini", ctx)
    ), result_cb)

    if progress_cb: progress_cb("🟢 GPT 반박/분석 중...")
    _store(results, "gpt_1", call_gpt(
        [{"role": "user", "content": f"안건: {agenda}\n\nClaude:\n{results['claude_1']}\n\nGemini:\n{results['gemini_1']}\n\n위 두 의견을 형식에 맞게 분석해라."}],
        build_system("gpt", ctx)
    ), result_cb)

    if progress_cb: progress_cb("📋 최종 정리 중...")
    _store(results, "final", call_gpt(
        [{"role": "user", "content": f"안건: {agenda}\n\nClaude:\n{results['claude_1']}\n\nGemini:\n{results['gemini_1']}\n\nGPT:\n{results['gpt_1']}\n\n전체 종합 최종 결론."}],
        build_system("secretary", ctx)
    ), result_cb)

    return results


def run_debate(agenda, category, situation, concerns, output_format,
               crisis=False, progress_cb=None, result_cb=None) -> dict:
    ctx = load_context()
    opening = build_opening(agenda, category, situation, concerns, output_format)
    results = {}

    if progress_cb: progress_cb("🔵 Claude 1차 — 브랜드/감성 전략 제시 중...")
    _store(results, "claude_1", call_claude(
        [{"role": "user", "content": opening}],
        build_system("claude", ctx, crisis)
    ), result_cb)

    if progress_cb: progress_cb("🟣 Gemini — 트렌드/대중 분석 중...")
    _store(results, "gemini_1", call_gemini(
        f"{opening}\n\nClaude가 이렇게 말했다:\n{results['claude_1']}\n\nClaude 의견 평가하고 트렌드/대중성 관점의 전략 추가.",
        build_system("gemini", ctx, crisis)
    ), result_cb)

    if progress_cb: progress_cb("🟢 GPT — ROI/리스크 반박 중...")
    _store(results, "gpt_1", call_gpt(
        [{"role": "user", "content": f"안건: {agenda}\n\nClaude:\n{results['claude_1']}\n\nGemini:\n{results['gemini_1']}\n\n위 두 의견을 퍼포먼스/ROI 기준으로 해체해라."}],
        build_system("gpt", ctx, crisis)
    ), result_cb)

    if progress_cb: progress_cb("🔴 Red Team — 실패 가능성 공격 중...")
    full_so_far = f"Claude:\n{results['claude_1']}\n\nGemini:\n{results['gemini_1']}\n\nGPT:\n{results['gpt_1']}"
    _store(results, "red_team", call_claude(
        [{"role": "user", "content": f"안건: {agenda}\n\n지금까지 나온 전략:\n{full_so_far}\n\n이 전략들의 실패 가능성을 공격해라."}],
        build_system("red_team", ctx, crisis)
    ), result_cb)

    if progress_cb: progress_cb("🔵 Claude 2차 — GPT 반박 검토 & 전략 수정 중...")
    _store(results, "claude_2", call_claude(
        [{"role": "user", "content": f"안건: {agenda}\n\nGPT 반박:\n{results['gpt_1']}\n\nRed Team 공격:\n{results['red_team']}\n\n형식에 맞게 반응해라."}],
        build_system("claude_2", ctx, crisis)
    ), result_cb)

    if progress_cb: progress_cb("📋 Secretary — 최종 결론 작성 중...")
    _store(results, "final", call_gpt(
        [{"role": "user", "content": (
            f"안건: {agenda}\n\n"
            f"Claude 1차:\n{results['claude_1']}\n\n"
            f"Gemini:\n{results['gemini_1']}\n\n"
            f"GPT:\n{results['gpt_1']}\n\n"
            f"Red Team:\n{results['red_team']}\n\n"
            f"Claude 2차:\n{results['claude_2']}\n\n"
            f"전체를 종합해서 최종 결론을 작성해라."
        )}],
        build_system("secretary", ctx, crisis)
    ), result_cb)

    return results


def run_crisis(agenda, category, situation, concerns, output_format,
               progress_cb=None, result_cb=None) -> dict:
    return run_debate(
        agenda, category, situation, concerns, output_format,
        crisis=True, progress_cb=progress_cb, result_cb=result_cb
    )


# ────────────────────────────────────────────
# 로그 저장
# ────────────────────────────────────────────

def save_log(agenda: str, mode: str, category: str, results: dict) -> Path:
    LOGS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    safe_agenda = agenda[:25].replace(" ", "_").replace("/", "-")
    filename = f"{timestamp}_{safe_agenda}.md"

    label_map = {
        "claude_1":  "🔵 Claude — 1차 전략",
        "gemini_1":  "🟣 Gemini — 트렌드/대중 분석",
        "gpt_1":     "🟢 GPT — 반박/리스크 분석",
        "red_team":  "🔴 Red Team — 실패 가능성 공격",
        "claude_2":  "🔵 Claude — 2차 (GPT 반박 검토)",
        "final":     "📋 Secretary — 최종 결론",
    }

    lines = [
        "# MADEWELL AI BOARDROOM v0.2\n",
        f"- **일시**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- **안건**: {agenda}",
        f"- **종류**: {category}",
        f"- **모드**: {mode.upper()}",
        "\n---\n",
    ]
    for key, label in label_map.items():
        if key in results:
            lines.append(f"## {label}\n\n{results[key]}\n\n---\n")

    filepath = LOGS_DIR / filename
    filepath.write_text("\n".join(lines), encoding='utf-8')
    return filepath


# ────────────────────────────────────────────
# API 키 체크
# ────────────────────────────────────────────

def _is_real_key(key: str) -> bool:
    """한국어 플레이스홀더나 빈 값이면 False"""
    if not key:
        return False
    try:
        key.encode('ascii')
        return True
    except UnicodeEncodeError:
        return False


def check_keys() -> dict:
    return {
        "claude": _is_real_key(ANTHROPIC_API_KEY),
        "openai": _is_real_key(OPENAI_API_KEY),
        "gemini": _is_real_key(GEMINI_API_KEY),
    }
