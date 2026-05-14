#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MADEWELL AI BOARDROOM v0.3.6 — Live War Room Engine
Claude × Gemini × GPT 전략 토론 엔진

핵심 변화:
- 발표형 구조가 아니라 라운드형 Debate Engine
- 모든 답변은 이전 발언을 인용/반박/수정하도록 강제
- Red Flag / 쟁점 테이블 / 폐기·채택·수정 분류 / 람보 인수인계 저장
- 한글·이모지 UTF-8 안전 처리
"""

from __future__ import annotations

import os
import re
import json
import sys
import html
import datetime as _dt
import base64
from pathlib import Path
from typing import Callable, Optional, Dict, List, Any

from dotenv import load_dotenv

# 터미널 출력 인코딩 안전화
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv(encoding="utf-8-sig")

ANTHROPIC_API_KEY = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
OPENAI_API_KEY    = (os.getenv("OPENAI_API_KEY") or "").strip()
GEMINI_API_KEY    = (os.getenv("GEMINI_API_KEY") or "").strip()

# 필요하면 .env에서 모델명 오버라이드 가능
CLAUDE_MODEL = (os.getenv("CLAUDE_MODEL") or "claude-sonnet-4-6").strip()
GPT_MODEL    = (os.getenv("GPT_MODEL") or "gpt-5.5").strip()
GEMINI_MODEL = (os.getenv("GEMINI_MODEL") or "gemini-2.5-flash").strip()
USE_GEMINI_API = (os.getenv("USE_GEMINI_API") or "0").strip() == "1"

BASE_DIR     = Path(__file__).parent
CONTEXT_DIR  = BASE_DIR / "context"
LOGS_DIR     = BASE_DIR / "logs"
MEMORY_DIR   = BASE_DIR / "memory"
HANDOFF_DIR  = BASE_DIR / "handoff"
PROFILE_PATH = MEMORY_DIR / "profile.json"

CONTEXT_FILES = [
    "madewell_profile.md",
    "current_projects.md",
    "meta_ads_history.md",
    "album_preorder_status.md",
    "brand_rules.md",
    "pricing_services.md",
    "rambo_style.md",
]

# memory/*.md 는 정균 전용 사고규칙/현재상황/결정로그를 담는다.
# v0.3.5부터 context와 함께 자동 로딩한다.
# 단, API 연결 테스트/기술 테스트에서는 memory를 강제로 끈다.
MAX_MEMORY_FILE_CHARS = int(os.getenv("MAX_MEMORY_FILE_CHARS", "12000"))
MAX_TOTAL_MEMORY_CHARS = int(os.getenv("MAX_TOTAL_MEMORY_CHARS", "50000"))

StageCallback = Optional[Callable[[str], None]]
ResultCallback = Optional[Callable[[str, str], None]]

# ────────────────────────────────────────────
# 안전 유틸
# ────────────────────────────────────────────

def _is_real_key(key: str) -> bool:
    """빈 값/한글 플레이스홀더/각종 예시값을 걸러낸다. 실제 API 호출 성공은 별도 verify_api_connections에서 확인."""
    if not key:
        return False
    lowered = key.lower()
    fake_markers = ["여기에", "your_", "example", "xxxxx", "키", "api_key", "placeholder"]
    if any(m in lowered for m in fake_markers):
        return False
    try:
        key.encode("ascii")
    except UnicodeEncodeError:
        return False
    return len(key) > 20


def check_keys() -> dict:
    return {
        "claude": _is_real_key(ANTHROPIC_API_KEY),
        "openai": _is_real_key(OPENAI_API_KEY),
        # Gemini는 선택사항. 기본값(USE_GEMINI_API=0)에서는 GPT가 Gemini 역할을 안전 대체한다.
        "gemini": _is_real_key(GEMINI_API_KEY) and USE_GEMINI_API,
        "gemini_key_present": _is_real_key(GEMINI_API_KEY),
        "gemini_enabled": USE_GEMINI_API,
    }

def safe_slug(text: str, max_len: int = 32) -> str:
    """파일명은 영어/숫자 중심으로 안전하게. 한글 안건은 파일 내부에만 저장."""
    text = text.strip().lower()
    # 공백/슬래시 등만 처리하고 한글은 제거
    text = re.sub(r"[^a-z0-9_-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:max_len] or "meeting"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def count_context_chars() -> int:
    return len(load_context())


def get_context_file_status() -> list[dict]:
    rows = []
    for fname in CONTEXT_FILES:
        fpath = CONTEXT_DIR / fname
        rows.append({
            "file": f"context/{fname}",
            "exists": fpath.exists(),
            "chars": len(read_text(fpath)) if fpath.exists() else 0,
        })
    if MEMORY_DIR.exists():
        for fpath in sorted(MEMORY_DIR.glob("*.md")):
            rows.append({
                "file": f"memory/{fpath.name}",
                "exists": True,
                "chars": len(read_text(fpath)),
            })
    return rows

# ────────────────────────────────────────────
# Memory / Context
# ────────────────────────────────────────────

def load_memory_files() -> str:
    """memory 폴더의 .md 파일을 자동 로딩한다.

    - strategy_kernel.md / always_on_boardroom_rules.md 같은 사고 규칙을 여기에 둔다.
    - 너무 길어져 토큰이 폭발하지 않도록 파일별/총량 제한을 둔다.
    """
    if not MEMORY_DIR.exists():
        return ""
    chunks: list[str] = []
    used = 0
    # 우선순위: 항상 켜져야 하는 규칙과 현재상황을 먼저 읽는다.
    priority = [
        "always_on_boardroom_rules.md",
        "strategy_kernel.md",
        "current_status.md",
        "decisions_log.md",
        "deep_strategic_reasoning_protocol.md",
        "war_game_mode_prompt.md",
        "marketing_doctrine.md",
    ]
    files = []
    for name in priority:
        p = MEMORY_DIR / name
        if p.exists():
            files.append(p)
    for p in sorted(MEMORY_DIR.glob("*.md")):
        if p not in files:
            files.append(p)
    for p in files:
        try:
            text = read_text(p).strip()
        except Exception:
            continue
        if not text:
            continue
        if len(text) > MAX_MEMORY_FILE_CHARS:
            text = text[:MAX_MEMORY_FILE_CHARS] + "\n\n[...memory file truncated...]"
        if used + len(text) > MAX_TOTAL_MEMORY_CHARS:
            break
        used += len(text)
        chunks.append(f"### [memory/{p.name}]\n{text}")
    return "\n\n".join(chunks)


def load_context(include_memory: bool = True) -> str:
    parts: list[str] = []
    for fname in CONTEXT_FILES:
        fpath = CONTEXT_DIR / fname
        if fpath.exists():
            content = read_text(fpath).strip()
            parts.append(f"### [context/{fname}]\n{content}")
    if include_memory:
        memory = load_memory_files()
        if memory:
            parts.append(f"### [MEMORY / ALWAYS-ON RULES]\n{memory}")
    recent = load_recent_log_summaries(limit=3)
    if recent:
        parts.append(f"### [최근 회의 요약 3개]\n{recent}")
    return "\n\n".join(parts) if parts else "(context/memory 파일 없음)"


def load_recent_log_summaries(limit: int = 3) -> str:
    if not LOGS_DIR.exists():
        return ""
    logs = sorted(LOGS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    chunks = []
    for p in logs:
        try:
            text = read_text(p)
            # 너무 길게 넣지 않도록 후반 Final / Handoff 위주 추출
            take = text[-2500:] if len(text) > 2500 else text
            chunks.append(f"#### {p.name}\n{take}")
        except Exception:
            continue
    return "\n\n".join(chunks)


def save_profile(data: dict) -> None:
    MEMORY_DIR.mkdir(exist_ok=True)
    safe = {k: v for k, v in data.items() if isinstance(v, str)}
    write_text(PROFILE_PATH, json.dumps(safe, ensure_ascii=False, indent=2))


def load_profile() -> dict:
    if not PROFILE_PATH.exists():
        return {}
    try:
        return json.loads(read_text(PROFILE_PATH))
    except Exception:
        return {}

# ────────────────────────────────────────────
# Prompt Builders
# ────────────────────────────────────────────

WAR_ROOM_RULES = """
[MADEWELL WAR ROOM 절대 규칙]
1. 여기는 의견 발표회가 아니다. 이전 발언을 인용하고, 동의/반대/위험/수정안을 반드시 제시하라.
2. 좋은 말 금지. 정균의 돈·시간·브랜드·팬덤에 실제 영향이 있는 판단만 말하라.
3. 위험한 제안은 Red Flag로 표시하라. 특히 구걸처럼 보이는 문구, 팬에게 죄책감 주는 문구, 스팸 DM, 브랜드 품격 훼손, 근거 없는 수치, 오늘 못 할 실행은 반드시 잡아라.
4. 한 문장이라도 실행으로 이어지지 않으면 삭제하라.
5. 정균은 무조건 위로보다 냉정한 현실 브레이크를 원한다. 단, 무너뜨리는 말이 아니라 다음 액션으로 연결하라.
6. 항상 한국어로 답하라.
""".strip()


def base_identity(context: str) -> str:
    return f"""
[공통 기억 — 모든 모델이 반드시 공유]
{context}

[TASK LOCK / 최우선 규칙]
- 사용자가 방금 입력한 [오늘의 안건]이 최우선이다.
- context/memory는 보조 자료일 뿐이다. 오늘의 안건과 직접 관련 없는 과거 MAMA/광고/카피 이야기를 끌고 오지 마라.
- 답변 첫 줄에서 오늘의 안건을 한 문장으로 재진술한 뒤 시작하라.
- API 연결 테스트, 설정 테스트, 연결 확인이면 마케팅/카피/전략 회의로 해석하지 마라.

[정균 운영 원칙]
- 정균은 1인 사업자라 실행 시간이 극도로 부족하다.
- 최종 액션은 오늘 실제로 할 수 있어야 한다.
- MADEWELL 브랜드는 싸구려/구걸/동정팔이로 보이면 안 된다.
- 숫자와 감정선이 충돌하면 둘 다 버리지 말고, 브랜드 손상 없는 전환 구조로 재설계한다.
""".strip()


def build_system(role: str, context: str, crisis: bool = False) -> str:
    crisis_flag = "\n\n🚨 [CRISIS MODE] 비상 모드다. 단기 생존성과 브랜드 장기 손상을 동시에 따져라. 위로 금지, 실행 우선." if crisis else ""
    shared = base_identity(context)

    if role == "claude":
        return f"""너는 MADEWELL 회의실의 Claude야. 브랜드/카피/팬덤 담당.

출력 형식 — 이걸 어기면 회의 무효야:
- 헤더(#, ##, ###) 절대 쓰지 마. 한 글자도.
- 별표 두 개(**굵게**) 쓰지 마.
- 대시(-) 목록 쓰지 마.
- "---" 구분선 쓰지 마.
- 그냥 문장으로 써. 대화하듯이.

이렇게 써라 (예시):
"광고가 12건 문의에 결제 0건 나온 건 광고 탓이 아니야. 사람들이 문의 후에 살 이유를 못 찾은 거야. 광고는 사람을 데려왔는데, 다음 단계가 없었던 거지."

이런 식으로. 짧게. 핵심만. 사람처럼.

역할: Ogilvy 카피 원칙으로 멈추게 하는 한 줄 만들기. Godin 팬덤 이론으로 서사 짜기. 구걸/죄책감 카피 금지. Gemini GPT 틀리면 직접 반박해.

{shared}

{WAR_ROOM_RULES}
{crisis_flag}
"""

    if role == "gemini":
        return f"""당신은 MADEWELL 회의실의 Gemini입니다. 트렌드/플랫폼/대중성 담당입니다.

출력 형식 — 반드시 지켜주세요:
헤더(#, ##, ###)는 쓰지 마세요. 별표 굵게(**) 쓰지 마세요. 목록(-) 쓰지 마세요.
그냥 자연스러운 문장으로 말씀해 주세요. 존댓말로요.

이렇게 써주세요 (예시):
"Claude 말씀하신 카피 방향은 맞는데요, 릴스에서는 첫 0.5초에 텍스트가 많으면 바로 스킵돼요. 지금 제안하신 문장은 읽는 데 3초가 걸려요. 첫 프레임은 시각적 충격이 필요해요."

이런 톤으로요. 플랫폼 현실 기반으로 직접 말해주세요.

역할: 인스타/틱톡/릴스 첫 0.5~3초 기준으로 판단. Claude 카피가 실제로 먹힐지 검증. 안 먹히면 바로 말하기. 지금 잘 되는 콘텐츠 패턴과 연결하기.

{shared}

{WAR_ROOM_RULES}
{crisis_flag}
"""

    if role == "gpt":
        return f"""You are GPT, the Strategy Chief in MADEWELL's war room. You handle numbers, ROI, and final verdicts. Respond in Korean.

Format rules: No headers (#, ##). No bold (**). No bullet lists. Plain sentences only.

Your job: Look at what Claude and Gemini said. Decide what to keep, what to cut, what to fix. Give a verdict with specific numbers and next actions. If you disagree, say exactly why and offer an alternative with data.

{shared}

{WAR_ROOM_RULES}
{crisis_flag}
"""

    if role == "red_team":
        return f"""당신은 MADEWELL AI BOARDROOM의 **Red Team / Failure Attacker**다.

[역할]
- 지금까지 나온 전략이 왜 실패할 수 있는지 공격한다.
- 칭찬 금지. 단, 억지 반박 금지. 현실에서 실제로 터질 리스크만 공격.
- 팬에게 죄책감 주는 문구, 구걸처럼 보이는 문구, 스팸 DM, 브랜드 훼손, 실행 불가능을 반드시 잡아낸다.

{shared}

{WAR_ROOM_RULES}
{crisis_flag}
"""

    if role == "arbiter":
        return f"""당신은 MADEWELL AI BOARDROOM의 **Final Arbiter / 작전참모장**이다.

[역할]
- 토론을 단순 요약하지 말고 판정한다.
- 폐기할 주장, 채택할 주장, 수정해서 쓸 주장을 나눈다.
- 정균이 오늘 바로 실행할 작전 명령서로 끝낸다.
- '좋은 방향입니다' 같은 말 금지. 무엇을 할지/하지 않을지 명령형으로 정리.

{shared}

{WAR_ROOM_RULES}
{crisis_flag}
"""

    return f"{shared}\n\n{WAR_ROOM_RULES}{crisis_flag}"


def build_opening(agenda: str, category: str, situation: str, concerns: str, output_format: str, intervention: str = "") -> str:
    return f"""
[안건 종류]
{category}

[오늘의 안건 — 최우선 TASK LOCK]
{agenda}

[중요]
모든 모델은 이 안건에만 답해야 한다. context/memory는 보조 자료다. 오늘의 안건과 직접 관련 없는 과거 주제로 튀지 마라.

[현재 상황]
{situation or '(사용자 입력 없음)'}

[정균이 느끼는 우려]
{concerns or '(사용자 입력 없음)'}

[원하는 출력]
{output_format or '(최종 결론 / 오늘 할 일 / 하지 말 것 / 리스크 / 체크 지표)'}

[정균의 중간 개입/추가 지시]
{intervention or '(없음)'}
""".strip()

# ────────────────────────────────────────────
# API Calls
# ────────────────────────────────────────────

def call_claude(messages: list, system: str, max_tokens: int = 1800) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    return response.content[0].text.strip()


def call_gpt(messages: list, system: str, max_tokens: int = 1800) -> str:
    """OpenAI 호출.

    GPT-5 계열은 Chat Completions에서 legacy `max_tokens`를 받지 않고
    `max_completion_tokens` 또는 Responses API의 `max_output_tokens`를 요구할 수 있다.
    그래서 우선 Responses API를 사용하고, 실패하면 Chat Completions로 안전하게 폴백한다.
    """
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    user_text = "\n\n".join([m.get("content", "") for m in messages if m.get("role") == "user"]).strip()
    if not user_text:
        user_text = str(messages)

    # 1) 최신 권장 경로: Responses API
    try:
        response = client.responses.create(
            model=GPT_MODEL,
            instructions=system,
            input=user_text,
            max_output_tokens=max_tokens,
        )
        text = getattr(response, "output_text", None)
        if text:
            return text.strip()
        # SDK 버전에 따라 output_text가 비어 있을 때 수동 파싱
        chunks = []
        for item in getattr(response, "output", []) or []:
            for c in getattr(item, "content", []) or []:
                t = getattr(c, "text", None)
                if t:
                    chunks.append(t)
        if chunks:
            return "\n".join(chunks).strip()
        # Responses API가 성공했지만 텍스트가 비어 있는 경우 Chat Completions 폴백으로 넘긴다.
        raise RuntimeError("Responses API returned empty text")
    except Exception as first_exc:
        # 2) 폴백: Chat Completions. GPT-5 계열은 max_completion_tokens 사용.
        try:
            full = [{"role": "system", "content": system}] + messages
            kwargs = {
                "model": GPT_MODEL,
                "messages": full,
            }
            if GPT_MODEL.lower().startswith("gpt-5"):
                kwargs["max_completion_tokens"] = max_tokens
            else:
                kwargs["max_tokens"] = max_tokens
                kwargs["temperature"] = 0.65
            response = client.chat.completions.create(**kwargs)
            return (response.choices[0].message.content or "").strip()
        except Exception as second_exc:
            raise RuntimeError(
                f"OpenAI 호출 실패. Responses API 오류: {first_exc} / Chat Completions 폴백 오류: {second_exc}"
            ) from second_exc


def _gpt_as_gemini_fallback(prompt: str, system: str, max_tokens: int = 1600, reason: str = "") -> str:
    """Gemini가 quota/모델/엔드포인트 문제로 실패해도 회의가 죽지 않도록 GPT가 Gemini 역할을 대체한다."""
    fallback_system = system + f"""

[중요: Gemini API 대체 모드]
현재 실제 Gemini API 호출이 실패했다. 이유: {reason}
당신은 지금부터 **Gemini 역할(시장/트렌드/일반 소비자 시선)**만 대체한다.
OpenAI 전략실장처럼 굴지 말고, 반드시 대중성/릴스/첫 3초/일반 소비자 관점으로만 답하라.
응답 첫 줄에 '※ Gemini API 실패로 GPT가 Gemini 역할을 임시 대체합니다.'라고 명시하라.
"""
    return call_gpt([{"role": "user", "content": prompt}], fallback_system, max_tokens)


def call_gemini(prompt: str, system: str, max_tokens: int = 1600) -> str:
    """Gemini REST API 호출. 실패하면 회의 전체를 중단하지 않고 GPT가 Gemini 역할로 폴백한다.

    - GEMINI_STRICT=1 을 .env에 넣으면 폴백 없이 에러를 그대로 띄운다.
    - 기본값은 실전 운영용: Gemini quota/모델 문제가 나도 회의 계속 진행.
    """
    strict = (os.getenv("GEMINI_STRICT") or "0").strip() == "1"
    if not USE_GEMINI_API:
        reason = "USE_GEMINI_API=0: 실제 Gemini API 호출을 끄고 GPT가 Gemini 역할을 안전 대체합니다."
        return _gpt_as_gemini_fallback(prompt, system, max_tokens, reason)

    if not _is_real_key(GEMINI_API_KEY):
        reason = "Gemini API 키가 없거나 placeholder입니다."
        if strict:
            raise RuntimeError(reason + " .env의 GEMINI_API_KEY를 확인하세요.")
        return _gpt_as_gemini_fallback(prompt, system, max_tokens, reason)
    try:
        import requests
    except ImportError as exc:
        reason = "requests 패키지가 없습니다. pip install requests 필요."
        if strict:
            raise RuntimeError(reason) from exc
        return _gpt_as_gemini_fallback(prompt, system, max_tokens, reason)

    # v1beta REST API. Pro 모델은 무료 티어 quota가 0일 수 있어 기본값은 gemini-2.5-flash.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}
    full_prompt = f"{system}\n\n--- 사용자/회의 입력 ---\n{prompt}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.65,
            "maxOutputTokens": max_tokens,
        },
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=90)
    except Exception as exc:
        reason = f"Gemini 네트워크 호출 실패: {exc}"
        if strict:
            raise RuntimeError(reason) from exc
        return _gpt_as_gemini_fallback(prompt, system, max_tokens, reason)

    if resp.status_code >= 400:
        body = resp.text[:1200]
        reason = f"Gemini API 호출 실패: HTTP {resp.status_code} / {body}"
        if strict:
            raise RuntimeError(reason)
        return _gpt_as_gemini_fallback(prompt, system, max_tokens, reason)

    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0].get("text")
        if text:
            return str(text).strip()
        raise ValueError("Gemini response text is empty")
    except Exception as exc:
        reason = f"Gemini 응답 파싱 실패: {json.dumps(data, ensure_ascii=False)[:1000]}"
        if strict:
            raise RuntimeError(reason) from exc
        return _gpt_as_gemini_fallback(prompt, system, max_tokens, reason)



# ────────────────────────────────────────────
# Image Summarization / GPT Vision
# ────────────────────────────────────────────

def _data_uri_from_image_payload(payload: dict) -> str:
    mime = payload.get("mime_type") or "image/png"
    if mime == "image/jpg":
        mime = "image/jpeg"
    raw = payload.get("data") or b""
    if not isinstance(raw, (bytes, bytearray)):
        raise ValueError("image payload data must be bytes")
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def summarize_uploaded_images(image_payloads: list[dict], agenda_hint: str = "") -> str:
    """Uploaded screenshots/images → boardroom-ready text summary.

    Uses OpenAI vision. This is deliberately NOT a strategy debate; it only extracts/organizes visual facts so
    the boardroom can reason from cleaner text.
    """
    if not _is_real_key(OPENAI_API_KEY):
        raise RuntimeError("OpenAI API 키가 필요합니다. .env의 OPENAI_API_KEY를 확인하세요.")
    if not image_payloads:
        raise RuntimeError("요약할 이미지가 없습니다.")

    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    names = [p.get("name", f"image_{i+1}") for i, p in enumerate(image_payloads)]
    prompt = f"""
너는 MADEWELL AI BOARDROOM의 '이미지 자료 정리 담당'이다.
첨부된 캡쳐/이미지를 보고 회의실에 바로 붙여넣을 수 있는 텍스트 자료로 정리해라.

중요 규칙:
- 전략 조언을 길게 하지 마라. 먼저 이미지에 보이는 사실/숫자/문구를 최대한 정확히 추출한다.
- 확실히 안 보이는 숫자는 추측하지 말고 '불확실'이라고 적는다.
- API 키, 이메일, 전화번호, 결제정보 같은 민감정보가 보이면 전체 값을 적지 말고 '[민감정보 가림]'으로 표시한다.
- 메타 광고/인스타 인사이트 캡쳐라면 지출액, 노출, 도달, 메시지, 클릭, 구매, 전환, CTR/CPM/CPC/CPA, 기간, 광고명 등을 우선 추출한다.
- 디자인/캐러셀 캡쳐라면 첫 장 훅, 시각적 위계, CTA, 정보 과부하, 브랜드 신호를 관찰 자료로 정리한다.
- 최종 출력은 회의실의 '현재 상황' 칸에 넣기 좋은 형태여야 한다.

안건 힌트:
{agenda_hint or '(없음)'}

이미지 파일명:
{', '.join(names)}

출력 형식:
[첨부 이미지 자동 요약]
1. 자료 종류:
2. 이미지에서 확인된 사실/수치:
3. 화면에 보이는 주요 문구/요소:
4. 불확실하거나 추가 확인 필요한 것:
5. 회의실 현재 상황 칸에 붙일 요약 문단:
6. 회의방에 물어볼 핵심 질문 후보 3개:
""".strip()

    content = [{"type": "input_text", "text": prompt}]
    for payload in image_payloads[:6]:
        content.append({"type": "input_image", "image_url": _data_uri_from_image_payload(payload)})

    # 1) Responses API vision path
    try:
        response = client.responses.create(
            model=(os.getenv("OPENAI_VISION_MODEL") or GPT_MODEL),
            input=[{"role": "user", "content": content}],
            max_output_tokens=1800,
        )
        text = getattr(response, "output_text", None)
        if text:
            return text.strip()
        chunks = []
        for item in getattr(response, "output", []) or []:
            for c in getattr(item, "content", []) or []:
                t = getattr(c, "text", None)
                if t:
                    chunks.append(t)
        if chunks:
            return "\n".join(chunks).strip()
        raise RuntimeError("Responses API returned empty image summary")
    except Exception as first_exc:
        # 2) Chat Completions vision fallback
        try:
            cc_content = [{"type": "text", "text": prompt}]
            for payload in image_payloads[:6]:
                cc_content.append({"type": "image_url", "image_url": {"url": _data_uri_from_image_payload(payload)}})
            kwargs = {
                "model": (os.getenv("OPENAI_VISION_MODEL") or GPT_MODEL),
                "messages": [{"role": "user", "content": cc_content}],
            }
            if (os.getenv("OPENAI_VISION_MODEL") or GPT_MODEL).lower().startswith("gpt-5"):
                kwargs["max_completion_tokens"] = 1800
            else:
                kwargs["max_tokens"] = 1800
                kwargs["temperature"] = 0.2
            response = client.chat.completions.create(**kwargs)
            return (response.choices[0].message.content or "").strip()
        except Exception as second_exc:
            raise RuntimeError(f"이미지 요약 실패. Responses 오류: {first_exc} / Chat 폴백 오류: {second_exc}") from second_exc

# ────────────────────────────────────────────
# Routing / Task Lock
# ────────────────────────────────────────────

def is_health_check(agenda: str, situation: str = "", concerns: str = "", output_format: str = "", intervention: str = "") -> bool:
    """API 연결/설정 확인은 War Room 체인을 타지 않는다."""
    text = " ".join([agenda or "", situation or "", concerns or "", output_format or "", intervention or ""]).lower()
    keywords = [
        "api 연결", "연결 테스트", "연결 확인", "api test", "health check",
        "gemini api", "claude api", "openai api", "한 문장으로", "테스트다",
        "실제 api", "호출되는지", "정상 작동", "정상작동"
    ]
    return any(k in text for k in keywords)

def is_technical_boardroom_issue(category: str, agenda: str) -> bool:
    text = f"{category} {agenda}".lower()
    return any(k in text for k in ["ai 회의실", "api", "연결", "테스트", "오류", "버그", "메모리", "memory", "보드룸", "boardroom"])

def run_health_check(progress_cb: StageCallback = None, result_cb: ResultCallback = None) -> dict:
    """각 모델 연결만 확인한다. memory/context/전략 프롬프트를 사용하지 않는다."""
    results: dict[str, str] = {}
    minimal = "너는 API 연결 테스트 중이다. 다른 맥락, memory, 마케팅 전략, MAMA 카피를 절대 사용하지 마라. 요청받은 연결 성공 문장만 답하라."

    _stage(progress_cb, "🔵 Claude API 연결 확인 중...")
    try:
        results["claude_1"] = call_claude([{"role":"user","content":"Claude 연결 테스트다. 정확히 'Claude 연결 성공'이라고만 답해라."}], minimal, 64) or "Claude 연결 성공"
    except Exception as e:
        results["claude_1"] = f"Claude 연결 실패: {e}"
    _emit(result_cb, "claude_1", results["claude_1"])

    _stage(progress_cb, "🟣 Gemini API 연결 확인 중...")
    try:
        results["gemini_1"] = call_gemini("Gemini 연결 테스트다. 정확히 'Gemini 연결 성공'이라고만 답해라.", minimal, 64) or "Gemini 연결 성공"
    except Exception as e:
        results["gemini_1"] = f"Gemini 연결 실패: {e}"
    _emit(result_cb, "gemini_1", results["gemini_1"])

    _stage(progress_cb, "🟢 GPT API 연결 확인 중...")
    try:
        results["gpt_1"] = call_gpt([{"role":"user","content":"GPT 연결 테스트다. 정확히 'GPT 연결 성공'이라고만 답해라."}], minimal, 64) or "GPT 연결 성공"
    except Exception as e:
        results["gpt_1"] = f"GPT 연결 실패: {e}"
    _emit(result_cb, "gpt_1", results["gpt_1"])

    results["final"] = "API Health Check 완료. 위 3개 모델의 성공/실패 문구만 확인하면 된다."
    _emit(result_cb, "final", results["final"])
    return results

# ────────────────────────────────────────────
# Debate Prompt Templates
# ────────────────────────────────────────────

def claude_round1_prompt(opening: str, technical: bool = False) -> str:
    if technical:
        return f"""
{opening}

[Round 1 / Claude 1차 주장 — 기술/시스템 안건]
오늘의 안건을 먼저 재진술하라.
이 안건은 마케팅 카피 회의가 아니다. MAMA 프리오더/광고 카피로 튀지 마라.
시스템/프롬프트/라우팅/메모리/사용성 관점에서만 답하라.
반드시 포함:
1. 현재 문제 정의
2. 원인 후보 3개
3. 즉시 고칠 것 3개
4. 테스트 방법 1개
""".strip()
    return f"""
{opening}

[Round 1 / Claude 발언]
오늘 안건에 대해 브랜드/카피/팬덤 관점으로 말해라.
헤더(#, ##) 쓰지 마. 번호 목록 쓰지 마. 대시(-) 목록 쓰지 마.
그냥 사람처럼 문장으로 말해라. 핵심만, 짧게.
실행 가능한 카피 하나와, 이 전략이 왜 실패할 수 있는지 포함해라.
""".strip()


def gemini_round1_prompt(opening: str, claude_1: str) -> str:
    return f"""
{opening}

[Claude 1차 발언]
{claude_1}

[Round 1 / Gemini 발언]
Claude 말한 거 보고 인스타/틱톡/릴스 관점에서 평가해 주세요.
헤더(#, ##) 쓰지 마세요. 대시(-) 목록 쓰지 마세요.
자연스러운 문장으로, 존댓말로 말씀해 주세요.
Claude 말 중 동의하는 것, 플랫폼에서 안 먹히는 것, 수정안 포함해 주세요.
""".strip()


def gpt_round1_prompt(opening: str, claude_1: str, gemini_1: str) -> str:
    return f"""
{opening}

[Claude 1차]
{claude_1}

[Gemini 1차]
{gemini_1}

[Round 1 / GPT 판정]
Claude와 Gemini 말을 인용하면서 판정해라.
헤더(#, ##) 쓰지 마. 목록 쓰지 마. 문장으로 써라.
동의할 것, 버릴 것, 수정할 것, 실행 리스크를 판정해라.
팬에게 죄책감 주는 문구, 구걸처럼 보이는 문구는 반드시 잡아라.
""".strip()


def red_team_prompt(opening: str, results: dict) -> str:
    return f"""
{opening}

[지금까지 나온 주장]
Claude 1차:
{results.get('claude_1','')}

Gemini 1차:
{results.get('gemini_1','')}

GPT 검증:
{results.get('gpt_1','')}

[Round 2 / Red Team 공격]
지금까지 나온 아이디어가 실제로 망할 수 있는 이유를 공격하라.
반드시 아래 형식:
## 🧨 Red Flag 1 — [구체 아이디어]
왜 위험한가 / 브랜드·전환·팬덤 리스크
## 🧨 Red Flag 2 — [구체 아이디어]
왜 위험한가
## 🧨 Red Flag 3 — [구체 아이디어]
왜 위험한가
## 살아남을 수 있는 조건
그래도 쓰려면 어떻게 수정해야 하는가
""".strip()


def claude_round2_prompt(opening: str, results: dict) -> str:
    return f"""
{opening}

[Gemini 반박]
{results.get('gemini_1','')}

[GPT 검증]
{results.get('gpt_1','')}

[Red Team 공격]
{results.get('red_team','')}

[Round 3 / Claude 재반박]
자존심 버리고 수정하라. 반박에 반박하되, 인정할 건 인정하라.
반드시 아래 형식:
## 👍 인정할 점
GPT/Gemini/Red Team 중 맞는 지적
## ✊ 인정 못 할 점
그래도 브랜드/감성 관점에서 지켜야 하는 핵심
## 🔄 수정된 카피/전략
구걸/죄책감 없이 쓸 수 있는 최종 카피 3개
## 오늘 실제 실행안
30분 안에 가능한 행동 1개
""".strip()


def gemini_round2_prompt(opening: str, results: dict) -> str:
    return f"""
{opening}

[수정된 Claude 전략]
{results.get('claude_2','')}

[GPT 검증]
{results.get('gpt_1','')}

[Red Team]
{results.get('red_team','')}

[Round 3 / Gemini 재평가]
수정된 전략이 실제 인스타/틱톡/일본 팬덤/일반 소비자에게 먹힐지 다시 평가하라.
반드시 아래 형식:
## 멈추게 하는가?
첫 0.5~3초 기준
## 너무 내부자적인가?
처음 보는 사람이 이해하는지
## 대중성 수정안
릴스/스토리/피드 각각 1개씩
## 아직 위험한 부분
폐기해야 할 표현
""".strip()


def gpt_issue_table_prompt(opening: str, results: dict) -> str:
    return f"""
{opening}

[전체 발언]
Claude 1차:
{results.get('claude_1','')}

Gemini 1차:
{results.get('gemini_1','')}

GPT 1차:
{results.get('gpt_1','')}

Red Team:
{results.get('red_team','')}

Claude 2차:
{results.get('claude_2','')}

Gemini 2차:
{results.get('gemini_2','')}

[Round 4 / GPT 쟁점 판정]
반드시 Markdown 표로 작성하라.
열: 쟁점 | Claude 입장 | Gemini 입장 | GPT 최종 판정 | 이유

그 아래 반드시 작성:
## 🧨 폐기할 아이디어
## ✅ 채택할 아이디어
## 🔧 수정해서 쓸 아이디어
## ❓ 아직 모르는 것
""".strip()


def final_prompt(opening: str, results: dict) -> str:
    return f"""
{opening}

[전체 토론]
Claude 1차:
{results.get('claude_1','')}

Gemini 1차:
{results.get('gemini_1','')}

GPT 1차:
{results.get('gpt_1','')}

Red Team:
{results.get('red_team','')}

Claude 2차:
{results.get('claude_2','')}

Gemini 2차:
{results.get('gemini_2','')}

쟁점 테이블:
{results.get('issue_table','')}

[Final Arbiter]
단순 요약 금지. 폐기/채택/수정의 판정을 내려라.
반드시 아래 형식 그대로:

## ✅ 최종 결론
2~4줄. 왜 이 결론인지 명확히.

## 🔥 오늘 할 일 3개
1. [지금 당장 / 30분 이내]
2. [오늘 안]
3. [내일 오전까지]

## 🧨 폐기할 아이디어 3개
1. 아이디어 — 폐기 이유
2. 아이디어 — 폐기 이유
3. 아이디어 — 폐기 이유

## 🔧 수정해서 쓸 아이디어 3개
1. 원안 → 수정안
2. 원안 → 수정안
3. 원안 → 수정안

## ⚠️ 리스크 3개
1. [높음/중간/낮음]
2. [높음/중간/낮음]
3. [높음/중간/낮음]

## 📊 48시간 체크 지표
- 지표: 기준치
- 지표: 기준치
- 지표: 기준치

## 🔁 다음 회의에서 다시 따질 쟁점
1~2개.

## 📤 람보 인수인계용 요약
"람보야, 아래 회의 결과 기억하고 이어가자."로 시작. 1000자 이내.
""".strip()

# ────────────────────────────────────────────
# Runner
# ────────────────────────────────────────────

def _emit(result_cb: ResultCallback, key: str, content: str) -> None:
    if result_cb:
        result_cb(key, content)


def _stage(progress_cb: StageCallback, msg: str) -> None:
    if progress_cb:
        progress_cb(msg)


def run_quick(agenda: str, category: str, situation: str, concerns: str, output_format: str,
              intervention: str = "", progress_cb: StageCallback = None, result_cb: ResultCallback = None) -> dict:
    if is_health_check(agenda, situation, concerns, output_format, intervention):
        return run_health_check(progress_cb, result_cb)
    ctx = load_context()
    opening = build_opening(agenda, category, situation, concerns, output_format, intervention)
    technical = is_technical_boardroom_issue(category, agenda)
    results: dict[str, str] = {}

    _stage(progress_cb, "🔵 Claude가 핵심 서사/카피를 잡는 중...")
    results["claude_1"] = call_claude([{"role": "user", "content": claude_round1_prompt(opening, technical)}], build_system("claude", ctx), 1200)
    _emit(result_cb, "claude_1", results["claude_1"])

    _stage(progress_cb, "🟣 Gemini가 대중성/플랫폼 반응을 검증하는 중...")
    results["gemini_1"] = call_gemini(gemini_round1_prompt(opening, results["claude_1"]), build_system("gemini", ctx), 1200)
    _emit(result_cb, "gemini_1", results["gemini_1"])

    _stage(progress_cb, "📋 GPT가 빠른 최종 결론을 정리하는 중...")
    results["final"] = call_gpt([{"role": "user", "content": final_prompt(opening, results)}], build_system("arbiter", ctx), 1500)
    _emit(result_cb, "final", results["final"])
    return results


def run_standard(agenda: str, category: str, situation: str, concerns: str, output_format: str,
                 intervention: str = "", progress_cb: StageCallback = None, result_cb: ResultCallback = None) -> dict:
    if is_health_check(agenda, situation, concerns, output_format, intervention):
        return run_health_check(progress_cb, result_cb)
    ctx = load_context()
    opening = build_opening(agenda, category, situation, concerns, output_format, intervention)
    technical = is_technical_boardroom_issue(category, agenda)
    results: dict[str, str] = {}

    _stage(progress_cb, "🔵 Round 1: Claude 1차 주장 중...")
    results["claude_1"] = call_claude([{"role": "user", "content": claude_round1_prompt(opening, technical)}], build_system("claude", ctx), 1500)
    _emit(result_cb, "claude_1", results["claude_1"])

    _stage(progress_cb, "🟣 Round 1: Gemini가 Claude를 반박/평가 중...")
    results["gemini_1"] = call_gemini(gemini_round1_prompt(opening, results["claude_1"]), build_system("gemini", ctx), 1500)
    _emit(result_cb, "gemini_1", results["gemini_1"])

    _stage(progress_cb, "🟢 Round 1: GPT가 Claude/Gemini를 검증 중...")
    results["gpt_1"] = call_gpt([{"role": "user", "content": gpt_round1_prompt(opening, results["claude_1"], results["gemini_1"])}], build_system("gpt", ctx), 1800)
    _emit(result_cb, "gpt_1", results["gpt_1"])

    _stage(progress_cb, "📋 Final Arbiter가 폐기/채택/수정 판정 중...")
    results["issue_table"] = call_gpt([{"role": "user", "content": gpt_issue_table_prompt(opening, results)}], build_system("gpt", ctx), 1500)
    _emit(result_cb, "issue_table", results["issue_table"])

    results["final"] = call_gpt([{"role": "user", "content": final_prompt(opening, results)}], build_system("arbiter", ctx), 1800)
    _emit(result_cb, "final", results["final"])
    return results


def run_debate(agenda: str, category: str, situation: str, concerns: str, output_format: str,
               intervention: str = "", crisis: bool = False, progress_cb: StageCallback = None,
               result_cb: ResultCallback = None) -> dict:
    if is_health_check(agenda, situation, concerns, output_format, intervention):
        return run_health_check(progress_cb, result_cb)
    ctx = load_context()
    opening = build_opening(agenda, category, situation, concerns, output_format, intervention)
    technical = is_technical_boardroom_issue(category, agenda)
    results: dict[str, str] = {}

    _stage(progress_cb, "🔵 Round 1: Claude가 브랜드/감정/카피 1차 주장을 세우는 중...")
    results["claude_1"] = call_claude([{"role": "user", "content": claude_round1_prompt(opening, technical)}], build_system("claude", ctx, crisis), 1600)
    _emit(result_cb, "claude_1", results["claude_1"])

    _stage(progress_cb, "🟣 Round 1: Gemini가 Claude 주장을 대중성/트렌드로 까는 중...")
    results["gemini_1"] = call_gemini(gemini_round1_prompt(opening, results["claude_1"]), build_system("gemini", ctx, crisis), 1600)
    _emit(result_cb, "gemini_1", results["gemini_1"])

    _stage(progress_cb, "🟢 Round 1: GPT가 숫자/ROI/브랜드 리스크로 둘 다 검증 중...")
    results["gpt_1"] = call_gpt([{"role": "user", "content": gpt_round1_prompt(opening, results["claude_1"], results["gemini_1"])}], build_system("gpt", ctx, crisis), 2000)
    _emit(result_cb, "gpt_1", results["gpt_1"])

    _stage(progress_cb, "🔴 Round 2: Red Team이 실패 가능성을 공격 중...")
    results["red_team"] = call_claude([{"role": "user", "content": red_team_prompt(opening, results)}], build_system("red_team", ctx, crisis), 1500)
    _emit(result_cb, "red_team", results["red_team"])

    _stage(progress_cb, "🔵 Round 3: Claude가 반박을 인정/재반박하며 전략을 수정 중...")
    results["claude_2"] = call_claude([{"role": "user", "content": claude_round2_prompt(opening, results)}], build_system("claude", ctx, crisis), 1600)
    _emit(result_cb, "claude_2", results["claude_2"])

    _stage(progress_cb, "🟣 Round 3: Gemini가 수정안을 다시 대중성으로 검증 중...")
    results["gemini_2"] = call_gemini(gemini_round2_prompt(opening, results), build_system("gemini", ctx, crisis), 1500)
    _emit(result_cb, "gemini_2", results["gemini_2"])

    _stage(progress_cb, "🟢 Round 4: GPT가 쟁점 테이블을 만들고 판정 중...")
    results["issue_table"] = call_gpt([{"role": "user", "content": gpt_issue_table_prompt(opening, results)}], build_system("gpt", ctx, crisis), 1800)
    _emit(result_cb, "issue_table", results["issue_table"])

    _stage(progress_cb, "📋 Final Arbiter가 최종 작전 명령서 작성 중...")
    results["final"] = call_gpt([{"role": "user", "content": final_prompt(opening, results)}], build_system("arbiter", ctx, crisis), 2200)
    _emit(result_cb, "final", results["final"])
    return results


def run_crisis(agenda: str, category: str, situation: str, concerns: str, output_format: str,
               intervention: str = "", progress_cb: StageCallback = None, result_cb: ResultCallback = None) -> dict:
    return run_debate(agenda, category, situation, concerns, output_format, intervention, True, progress_cb, result_cb)



# ────────────────────────────────────────────
# Endless Debate / 100-Branch Consensus Forge
# ────────────────────────────────────────────

def endless_task_lock_prompt(opening: str) -> str:
    return f"""
{opening}

[Round 0 / Task Lock]
오늘 회의가 엉뚱한 과거 맥락으로 튀지 않도록 안건을 고정하라.
반드시 아래 형식:
## 오늘의 안건
한 문장.
## 이번 회의에서 결정해야 할 것
3개 이하.
## 이번 회의에서 결정하지 않을 것
3개 이하.
## 관련 memory/context만 사용할 기준
무엇은 참고하고, 무엇은 무시할지.
""".strip()


def hundred_branch_prompt(opening: str) -> str:
    return f"""
{opening}

[100-Branch War Game / 사전 가설 폭발]
바로 조언하지 마라. 가능한 가설/경우의 수/실패 경로/역효과/숨은 변수를 최소 100개까지 내부적으로 펼쳐라.
단, 최종 출력에 100개를 전부 장황하게 나열하지 마라.

반드시 아래 형식:
## 1. 100개 후보 생성 완료 선언
- 어떤 범주의 가설을 펼쳤는지.

## 2. 카테고리 클러스터 8~12개
각 카테고리별 대표 가설 3~5개.
예: 노출, 훅, 이해, 신뢰, 욕망, 구매 동선, 사회적 증거, 팬덤 온도, 플랫폼, 메시지 신호, 브랜드 리스크, 기회비용, unknown unknowns.

## 3. 의사결정을 바꾸는 상위 10개 가설
각 가설마다:
- 가설:
- 왜 중요:
- 맞다면 해야 할 일:
- 틀리면 버려야 할 일:
- 검증 방법:

## 4. 끝장토론에 넘길 핵심 쟁점 3~5개
""".strip()


def endless_claude_thesis_prompt(opening: str, task_lock: str, branch_map: str = "") -> str:
    return f"""
{opening}

[Task Lock]
{task_lock}

[100-Branch Map]
{branch_map or '(없음)'}

[Round 1 / Claude Initial Thesis]
브랜드·감정선·팬덤 언어·카피 신호 관점에서 최초 주장을 내라.
절대 무난하게 말하지 마라. 네 주장이 공격받을 지점까지 먼저 밝혀라.

형식:
## 내 주장
## 근거
## 가장 약한 지점
## 상대가 공격할 만한 부분
## 그래도 지켜야 할 브랜드 핵심
""".strip()


def endless_gemini_attack_prompt(opening: str, task_lock: str, claude: str, branch_map: str = "") -> str:
    return f"""
{opening}

[Task Lock]
{task_lock}

[100-Branch Map]
{branch_map or '(없음)'}

[Claude 최초 주장]
{claude}

[Round 2 / Gemini Cross Attack]
Claude의 구체 문장 최소 2개를 인용해 공격하라.
대중성, 플랫폼, 첫 0.5~3초, 일반 소비자, 일본 팬덤 오해 가능성 기준으로만 판단하라.

형식:
## 내가 공격하는 Claude 문장
## 왜 위험한가
## 숨은 가정
## 이 가정이 틀리면 생기는 손해
## 수정 요구
## Gemini의 반대 제안
""".strip()


def endless_gpt_attack_prompt(opening: str, task_lock: str, claude: str, gemini: str, branch_map: str = "") -> str:
    return f"""
{opening}

[Task Lock]
{task_lock}

[100-Branch Map]
{branch_map or '(없음)'}

[Claude]
{claude}

[Gemini]
{gemini}

[Round 2 / GPT Cross Attack]
Claude와 Gemini를 둘 다 공격하라. 감성/대중성보다 돈, 시간, 실행 가능성, 기회비용, 리스크를 기준으로 판정하라.

형식:
## 내가 공격하는 Claude 문장
## 내가 공격하는 Gemini 문장
## 둘 다 놓친 핵심 변수
## 정균이 지금 믿으면 위험한 착각
## 비용/시간 대비 가장 위험한 선택
## GPT의 반대 제안
""".strip()


def endless_cross_attack_synthesis_prompt(opening: str, claude: str, gemini: str, gpt: str) -> str:
    return f"""
{opening}

[Claude]
{claude}

[Gemini]
{gemini}

[GPT]
{gpt}

[Round 2 / Cross Attack Synthesis]
세 모델의 공격을 종합하되 요약하지 말고, 실제 충돌 지점을 뽑아라.

형식:
## 핵심 충돌 1
- Claude:
- Gemini:
- GPT:
- 왜 중요한가:
## 핵심 충돌 2
## 핵심 충돌 3
## 지금 당장 폐기 후보
## 아직 살릴 수 있는 후보
""".strip()


def endless_steelman_prompt(opening: str, claude: str, gemini: str, gpt: str, cross: str) -> str:
    return f"""
{opening}

[현재까지 주장]
Claude:
{claude}

Gemini:
{gemini}

GPT:
{gpt}

[충돌 정리]
{cross}

[Round 3 / Steelman]
각 입장을 약하게 만들지 말고 가장 강한 버전으로 재구성하라.

형식:
## Claude 주장이 가장 강해지는 조건
## Gemini 주장이 가장 강해지는 조건
## GPT 주장이 가장 강해지는 조건
## 각 주장이 맞다면 바뀌어야 할 행동
## 그래도 남는 반론
""".strip()


def endless_revision_prompt(opening: str, claude: str, gemini: str, gpt: str, steelman: str) -> str:
    return f"""
{opening}

[Claude]
{claude}

[Gemini]
{gemini}

[GPT]
{gpt}

[Steelman]
{steelman}

[Round 4 / Revision]
각 진영의 원안을 수정하라. 반드시 버릴 것/유지할 것/수정할 것을 나눠라.

형식:
## 버리는 주장
## 유지하는 주장
## 수정하는 주장
## 살아남은 후보안 3개
## 후보안별 안전장치
""".strip()


def endless_red_team_prompt(opening: str, revision: str, branch_map: str = "") -> str:
    return f"""
{opening}

[100-Branch Map]
{branch_map or '(없음)'}

[수정안]
{revision}

[Round 5 / Red Team]
살아남은 후보안이 왜 실패할 수 있는지 공격하라.

반드시 공격:
- 브랜드 훼손
- 팬덤 역효과
- 구걸/자기연민 리스크
- 전환 실패
- 실행 불가능
- 기회비용
- 2차/3차 역효과
- 잘못된 가정
- 측정 불가능성

형식:
## 즉시 폐기할 후보
## 수정하면 살릴 후보
## 가장 위험한 착각
## 실패 시 가장 큰 손해
## 그래도 실행할 가치가 남는 후보
""".strip()


def endless_scoring_prompt(opening: str, revision: str, red_team: str) -> str:
    return f"""
{opening}

[수정안]
{revision}

[Red Team]
{red_team}

[Round 6 / Convergence Scoring]
살아남은 후보안을 점수화하라.
점수 항목은 1~5점: 전략 적합성, 브랜드 안전성, 전환 가능성, 실행 가능성, 검증 속도, 정보값, 기회비용, 팬덤 리스크.

형식:
## 후보안별 점수표
Markdown 표.
## 1위 후보
## 2위 후보
## 폐기 후보
## 아직 남은 불일치 지점
""".strip()


def endless_final_negotiation_prompt(opening: str, scoring: str, red_team: str) -> str:
    return f"""
{opening}

[점수화]
{scoring}

[Red Team]
{red_team}

[Round 7 / Final Negotiation]
최종 후보에 대해 마지막 조건부 동의/반대를 정리하라.

형식:
## 최종 후보
## 조건부 동의 조건
## 반드시 넣어야 할 안전장치
## 반드시 빼야 할 표현/행동
## 48시간 검증 조건
## 추가 토론보다 실행이 나은 이유 또는 더 토론해야 하는 이유
""".strip()


def endless_final_prompt(opening: str, results: dict, branch100: bool = False) -> str:
    return f"""
{opening}

[전체 끝장토론]
Task Lock:
{results.get('task_lock','')}

100-Branch Map:
{results.get('branch_map','')}

Claude:
{results.get('claude_1','')}

Gemini:
{results.get('gemini_1','')}

GPT:
{results.get('gpt_1','')}

Cross Attack:
{results.get('cross_attack','')}

Steelman:
{results.get('steelman','')}

Revision:
{results.get('revision','')}

Red Team:
{results.get('red_team','')}

Scoring:
{results.get('score_table','')}

Final Negotiation:
{results.get('final_negotiation','')}

Continuation Check:
{results.get('continuation_check','')}

Adaptive Extra Rounds:
{results.get('adaptive_loop','')}

[Round 8 / Final Arbiter]
단순 요약 금지. 합의된 것과 끝까지 남은 쟁점을 분리하라.
반드시 아래 형식 그대로:

## ✅ 최종 판정
채택 / 수정 후 채택 / 보류 / 폐기 중 하나.

## 🤝 합의된 것
모든 모델이 동의한 내용.

## ⚔️ 끝까지 남은 쟁점
의견이 갈린 지점과 왜 갈렸는지.

## 🧨 폐기할 것
최소 1개.

## 🔧 수정할 것
최소 1개.

## 🔥 오늘 할 일 1~3개
정균이 30~60분 안에 실제로 할 수 있는 행동.

## ⚠️ 가장 위험한 착각
지금 믿으면 손해 보는 가정.

## 📊 24~48시간 검증 지표
조회수, 완주율, 프로필 방문, 링크 클릭, DM, 예약/결제, 일본어 반응 등.

## 📤 람보 인수인계용 요약
"람보야, 아래 회의 결과 기억하고 이어가자."로 시작. 1000자 이내.
""".strip()




def continuation_check_prompt(opening: str, results: dict, loop_history: str = "", remaining_rounds: int = 0) -> str:
    return f"""
{opening}

[현재 끝장토론 결과]
Task Lock:
{results.get('task_lock','')}

Branch Map:
{results.get('branch_map','')}

Claude:
{results.get('claude_1','')}

Gemini:
{results.get('gemini_1','')}

GPT:
{results.get('gpt_1','')}

Cross Attack:
{results.get('cross_attack','')}

Steelman:
{results.get('steelman','')}

Revision:
{results.get('revision','')}

Red Team:
{results.get('red_team','')}

Scoring:
{results.get('score_table','')}

Final Negotiation:
{results.get('final_negotiation','')}

[추가 재공방 기록]
{loop_history or '(아직 없음)'}

[Continuation Check]
추가 토론이 필요한지 냉정하게 판단하라. 더 오래 떠드는 것이 목적이 아니다.
남은 추가 재공방 가능 횟수: {remaining_rounds}

아래 중 하나라도 새롭게 강하게 발견되면 CONTINUE:
- 새 실패 가능성이 발견됨
- 후보 점수가 바뀔 수 있음
- 폐기/수정해야 할 아이디어가 새로 생김
- 남은 쟁점이 실행 전 반드시 줄어야 함
- Red Team의 치명 리스크가 충분히 해소되지 않음

아래에 해당하면 STOP:
- 같은 말 반복
- 상위 후보가 명확함
- 남은 쟁점은 토론이 아니라 실험으로만 확인 가능
- 추가 토론보다 실행해서 데이터 얻는 정보값이 큼
- 오늘 실행안이 충분히 압축됨

반드시 아래 형식:
## 판정
CONTINUE 또는 STOP 중 하나만 먼저 쓴다.
## 이유
## 남은 핵심 쟁점 1~3개
## 추가 토론이 필요하다면 다음 라운드에서 공격할 질문
## 멈춘다면 바로 실행해야 하는 이유
""".strip()


def adaptive_extra_round_prompt(opening: str, results: dict, continuation: str, loop_history: str, round_no: int) -> str:
    return f"""
{opening}

[지금까지 끝장토론]
Revision:
{results.get('revision','')}

Red Team:
{results.get('red_team','')}

Scoring:
{results.get('score_table','')}

Final Negotiation:
{results.get('final_negotiation','')}

[Continuation Check]
{continuation}

[이전 추가 재공방]
{loop_history or '(없음)'}

[Adaptive Extra Round {round_no}]
새로운 말이 없으면 억지로 말하지 마라. 기존 말 반복 금지.
이번 라운드는 남은 쟁점만 놓고 재공방한다.

반드시 아래 형식:
## 이번 라운드에서 새로 밝혀진 것
## 기존 후보 중 점수가 바뀌는 것
## 새로 폐기/수정해야 할 것
## 아직 토론으로 해결 안 되고 실험으로 넘겨야 할 것
## 다음 판정 제안
- STOP 또는 CONTINUE
""".strip()

def run_endless_debate(agenda: str, category: str, situation: str, concerns: str, output_format: str,
                        intervention: str = "", branch100: bool = False, adaptive: bool = False, max_extra_rounds: int = 0, progress_cb: StageCallback = None,
                        result_cb: ResultCallback = None) -> dict:
    if is_health_check(agenda, situation, concerns, output_format, intervention):
        return run_health_check(progress_cb, result_cb)
    ctx = load_context()
    opening = build_opening(agenda, category, situation, concerns, output_format, intervention)
    results: dict[str, str] = {}

    _stage(progress_cb, "🔒 Round 0: Task Lock으로 안건 고정 중...")
    results["task_lock"] = call_gpt([{"role":"user","content": endless_task_lock_prompt(opening)}], build_system("gpt", ctx), 1200)
    _emit(result_cb, "task_lock", results["task_lock"])

    if branch100:
        _stage(progress_cb, "💣 Round 0.5: 100개 가설/실패경로를 펼치고 클러스터링 중...")
        results["branch_map"] = call_gpt([{"role":"user","content": hundred_branch_prompt(opening)}], build_system("gpt", ctx), 3500)
        _emit(result_cb, "branch_map", results["branch_map"])

    _stage(progress_cb, "🔵 Round 1: Claude 최초 주장 중...")
    results["claude_1"] = call_claude([{"role":"user","content": endless_claude_thesis_prompt(opening, results.get("task_lock",""), results.get("branch_map",""))}], build_system("claude", ctx), 1800)
    _emit(result_cb, "claude_1", results["claude_1"])

    _stage(progress_cb, "🟣 Round 2: Gemini가 Claude 주장을 공격 중...")
    results["gemini_1"] = call_gemini(endless_gemini_attack_prompt(opening, results.get("task_lock",""), results["claude_1"], results.get("branch_map","")), build_system("gemini", ctx), 1800)
    _emit(result_cb, "gemini_1", results["gemini_1"])

    _stage(progress_cb, "🟢 Round 2: GPT가 Claude/Gemini를 동시에 공격 중...")
    results["gpt_1"] = call_gpt([{"role":"user","content": endless_gpt_attack_prompt(opening, results.get("task_lock",""), results["claude_1"], results["gemini_1"], results.get("branch_map",""))}], build_system("gpt", ctx), 2200)
    _emit(result_cb, "gpt_1", results["gpt_1"])

    _stage(progress_cb, "⚔️ Round 2: 핵심 충돌 지점 압축 중...")
    results["cross_attack"] = call_gpt([{"role":"user","content": endless_cross_attack_synthesis_prompt(opening, results["claude_1"], results["gemini_1"], results["gpt_1"])}], build_system("gpt", ctx), 1800)
    _emit(result_cb, "cross_attack", results["cross_attack"])

    _stage(progress_cb, "🛡 Round 3: Steelman으로 상대 주장 강화 중...")
    results["steelman"] = call_gpt([{"role":"user","content": endless_steelman_prompt(opening, results["claude_1"], results["gemini_1"], results["gpt_1"], results["cross_attack"])}], build_system("gpt", ctx), 2200)
    _emit(result_cb, "steelman", results["steelman"])

    _stage(progress_cb, "🔧 Round 4: 각 주장 수정/폐기/유지 중...")
    results["revision"] = call_claude([{"role":"user","content": endless_revision_prompt(opening, results["claude_1"], results["gemini_1"], results["gpt_1"], results["steelman"])}], build_system("claude", ctx), 2200)
    _emit(result_cb, "revision", results["revision"])

    _stage(progress_cb, "🔴 Round 5: Red Team이 살아남은 후보를 공격 중...")
    results["red_team"] = call_claude([{"role":"user","content": endless_red_team_prompt(opening, results["revision"], results.get("branch_map",""))}], build_system("red_team", ctx), 1800)
    _emit(result_cb, "red_team", results["red_team"])

    _stage(progress_cb, "📊 Round 6: 후보안 점수화/수렴 판단 중...")
    results["score_table"] = call_gpt([{"role":"user","content": endless_scoring_prompt(opening, results["revision"], results["red_team"])}], build_system("gpt", ctx), 2200)
    _emit(result_cb, "score_table", results["score_table"])

    _stage(progress_cb, "🤝 Round 7: 최종 협상 중...")
    results["final_negotiation"] = call_gpt([{"role":"user","content": endless_final_negotiation_prompt(opening, results["score_table"], results["red_team"])}], build_system("gpt", ctx), 1800)
    _emit(result_cb, "final_negotiation", results["final_negotiation"])

    loop_history = ""
    if adaptive or max_extra_rounds > 0:
        _stage(progress_cb, "🧭 Continuation Check: 더 토론할지 판단 중...")
        remaining = int(max_extra_rounds or 0)
        results["continuation_check"] = call_gpt([{"role":"user","content": continuation_check_prompt(opening, results, loop_history, remaining)}], build_system("gpt", ctx), 1400)
        _emit(result_cb, "continuation_check", results["continuation_check"])

        round_no = 1
        while remaining > 0 and "CONTINUE" in results.get("continuation_check", "").upper():
            _stage(progress_cb, f"♻️ Adaptive Extra Round {round_no}: 남은 쟁점 추가 재공방 중...")
            extra = call_gpt([{"role":"user","content": adaptive_extra_round_prompt(opening, results, results.get("continuation_check", ""), loop_history, round_no)}], build_system("gpt", ctx), 2200)
            loop_history += f"\n\n## Adaptive Extra Round {round_no}\n{extra}\n"
            results["adaptive_loop"] = loop_history.strip()
            _emit(result_cb, "adaptive_loop", results["adaptive_loop"])

            remaining -= 1
            if remaining <= 0:
                break
            _stage(progress_cb, f"🧭 Continuation Check {round_no}: 추가 연장 필요 여부 재판정 중...")
            results["continuation_check"] = call_gpt([{"role":"user","content": continuation_check_prompt(opening, results, loop_history, remaining)}], build_system("gpt", ctx), 1400)
            _emit(result_cb, "continuation_check", results["continuation_check"])
            round_no += 1

    _stage(progress_cb, "📋 Round 8: Final Arbiter가 합의/불일치/실행안 정리 중...")
    results["final"] = call_gpt([{"role":"user","content": endless_final_prompt(opening, results, branch100=branch100)}], build_system("arbiter", ctx), 2600)
    _emit(result_cb, "final", results["final"])
    return results

# ────────────────────────────────────────────
# Logs / Handoff
# ────────────────────────────────────────────

LABEL_MAP = {
    "task_lock": "🔒 Task Lock / 안건 고정",
    "branch_map": "💣 100-Branch 가설 지도",
    "claude_1":   "🔵 Claude — 1차 주장",
    "gemini_1":   "🟣 Gemini — 1차 반박/대중성 평가",
    "gpt_1":      "🟢 GPT — 전략/ROI/리스크 검증",
    "cross_attack": "⚔️ Cross Attack / 상호 공격",
    "steelman": "🛡 Steelman / 상대 주장 강화",
    "revision": "🔧 Revision / 수정안 제출",
    "red_team":   "🔴 Red Team — 실패 가능성 공격",
    "score_table": "📊 Convergence Scoring / 수렴 점수화",
    "final_negotiation": "🤝 Final Negotiation / 최종 협상",
    "continuation_check": "🧭 Continuation Check / 추가 토론 판단",
    "adaptive_loop": "♻️ Adaptive Extra Rounds / 조건부 추가 재공방",
    "claude_2":   "🔵 Claude — 재반박/수정 전략",
    "gemini_2":   "🟣 Gemini — 수정안 재평가",
    "issue_table": "⚖️ 쟁점 테이블 / 폐기·채택·수정 판정",
    "final":      "📋 Final Arbiter — 최종 결론",
}


def extract_handoff(final_text: str, agenda: str, mode: str) -> str:
    marker = "## 📤 람보 인수인계용 요약"
    if marker in final_text:
        part = final_text.split(marker, 1)[1].strip()
        # 다음 h2가 있으면 거기까지만
        part = re.split(r"\n##\s+", part, maxsplit=1)[0].strip()
        if part:
            return f"람보야, 아래 회의 결과 기억하고 이어가자.\n\n{part}"
    # fallback
    compact = re.sub(r"\n{3,}", "\n\n", final_text).strip()
    return f"""람보야, 아래 회의 결과 기억하고 이어가자.

[람보 인수인계용 요약]
- 안건: {agenda}
- 모드: {mode}
- 최종 요약: {compact[:900]}
""".strip()


def save_log(agenda: str, mode: str, category: str, situation: str, concerns: str,
             output_format: str, intervention: str, results: dict) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{safe_slug(mode)}.md"

    context_status = get_context_file_status()
    context_lines = "\n".join([f"- {r['file']}: {'OK' if r['exists'] else 'MISSING'} / {r['chars']} chars" for r in context_status])

    lines = [
        "# MADEWELL AI BOARDROOM v0.3 — Live War Room",
        "",
        f"- **일시**: {_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **안건**: {agenda}",
        f"- **종류**: {category}",
        f"- **모드**: {mode.upper()}",
        "",
        "## 입력값",
        f"### 현재 상황\n{situation or '(없음)'}",
        f"### 우려\n{concerns or '(없음)'}",
        f"### 원하는 출력\n{output_format or '(없음)'}",
        f"### 중간 개입/추가 지시\n{intervention or '(없음)'}",
        "",
        "## 불러온 context 파일",
        context_lines,
        "\n---\n",
    ]
    for key, label in LABEL_MAP.items():
        if key in results:
            lines.append(f"## {label}\n\n{results[key]}\n\n---\n")

    handoff = extract_handoff(results.get("final", ""), agenda, mode)
    lines.append(f"## 📤 람보 인수인계용 요약\n\n{handoff}\n")

    filepath = LOGS_DIR / filename
    write_text(filepath, "\n".join(lines))

    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    write_text(HANDOFF_DIR / "latest_for_rambo.md", handoff)
    return filepath


def get_latest_handoff() -> str:
    path = HANDOFF_DIR / "latest_for_rambo.md"
    if path.exists():
        return read_text(path)
    return ""
