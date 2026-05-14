#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MADEWELL AI BOARDROOM v0.1
Claude × GPT 전략 토론 시스템
"""

import os
import sys
import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    import anthropic
    from openai import OpenAI
except ImportError:
    print("\n❌ 필요한 패키지가 없습니다. 아래 명령어를 먼저 실행해주세요:\n")
    print("  pip3 install anthropic openai python-dotenv\n")
    sys.exit(1)

# .env 로드 (BOM 및 인코딩 문제 방지)
load_dotenv(encoding='utf-8-sig')

ANTHROPIC_API_KEY = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()

CLAUDE_MODEL = "claude-sonnet-4-6"
GPT_MODEL = "gpt-4o"

# ────────────────────────────────────────────
# 시스템 프롬프트
# ────────────────────────────────────────────

CLAUDE_SYSTEM = """당신은 MADEWELL AI BOARDROOM의 전략 참모 Claude입니다.

[클라이언트 현황]
- 이름: 정균 (MADEWELL) — K-POP 프로듀서, 아티스트, (주)MADEWELL MUSIC 대표
- 스튜디오: 강남 역삼동, 월 고정비 160만원
- 주요 크레딧: PRODUCE 101 JAPAN, VIVIZ, (여자)아이들 전소연, 마마무 화사, 인피니트 장동우 등 KOMCA 100곡+
- 장비: NEVE 1073, SSL FUSION, Pro Tools HDX, Neumann U87 등
- 현재 진행:
  · 솔로 3집 MAMA 프리오더 (5/8~5/20, 35,000원, 목표 100장, 현재 20장)
  · 메타 광고 집행 중 (스튜디오 캐러셀 + 레슨 부스트)
  · 네이버 블로그 SEO 진행 중
  · 크몽 믹싱/마스터링/레코딩/레슨 서비스 등록 완료
- 목표: 월 1,000만원 수익 (레슨 10명 + 믹싱 20건 + 기타)
- 일본 팬덤 보유, 틱톡 라이브 진행 중

[당신의 역할]
- 브랜딩, 스토리텔링, 감성 마케팅 관점에서 전략 제시
- Philip Kotler, David Ogilvy, Seth Godin, Al Ries, Eugene Schwartz 이론 기반
- 구체적이고 당장 실행 가능한 의견만 제시
- GPT 의견을 보고 반박하거나 보완할 때는 날카롭게
- 항상 한국어로 답변
- 답변은 500자 이내로 핵심만"""

GPT_SYSTEM = """당신은 MADEWELL AI BOARDROOM의 전략 참모 GPT입니다.

[클라이언트 현황]
- 이름: 정균 (MADEWELL) — K-POP 프로듀서, 아티스트, (주)MADEWELL MUSIC 대표
- 스튜디오: 강남 역삼동, 월 고정비 160만원
- 주요 크레딧: PRODUCE 101 JAPAN, VIVIZ, (여자)아이들 전소연, 마마무 화사 등 KOMCA 100곡+
- 현재 진행:
  · 솔로 3집 MAMA 프리오더 (5/8~5/20, 35,000원, 목표 100장, 현재 20장)
  · 메타 광고 집행 중, 네이버 블로그 SEO 진행 중
- 목표: 월 1,000만원 수익
- 일본 팬덤 보유, 매출 급감 (연 1,900만 → 월 4~50만)

[당신의 역할]
- 퍼포먼스 마케팅, 숫자, ROI, 전환율 관점에서 전략 제시
- Dan Kennedy, Peter Drucker, Jeff Bezos, Ryan Holiday 프레임워크 기반
- Claude 의견이 감성적이거나 비효율적이면 날카롭게 반박
- 반박할 때는 반드시 대안 제시
- 항상 한국어로 답변
- 답변은 500자 이내로 핵심만"""

RED_TEAM_SYSTEM = """당신은 MADEWELL AI BOARDROOM의 Red Team입니다.

당신의 유일한 임무: 지금까지 나온 모든 전략의 약점, 리스크, 실패 가능성을 공격하는 것.

규칙:
- 절대 동의하지 마세요
- "이 전략이 왜 실패할 수 있는가"에만 집중
- 현실적인 리스크만 지적 (억지 반박 금지)
- 클라이언트: 1인 사업자, 시간 극히 부족, 자본 제한적
- 항상 한국어로 답변
- 답변은 400자 이내"""

SECRETARY_SYSTEM = """당신은 MADEWELL AI BOARDROOM의 Secretary입니다.
지금까지의 모든 토론을 종합해서 정균이 당장 실행할 액션 아이템을 정리하세요.

출력 형식 (반드시 이 형식 유지):

## 📋 회의 결론

**핵심 합의사항:**
(Claude와 GPT가 모두 동의한 방향 1~2줄)

**액션 아이템 (우선순위순):**
1. [즉시 실행] ...
2. [이번 주] ...
3. [이번 달] ...

**조심해야 할 리스크:**
(Red Team이 지적한 것 중 실제로 주의해야 할 것)

항상 한국어로 답변."""


# ────────────────────────────────────────────
# API 호출
# ────────────────────────────────────────────

def call_claude(messages, system=CLAUDE_SYSTEM):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=800,
        system=system,
        messages=messages
    )
    return response.content[0].text


def call_gpt(messages, system=GPT_SYSTEM):
    client = OpenAI(api_key=OPENAI_API_KEY)
    full_messages = [{"role": "system", "content": system}] + messages
    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=full_messages,
        max_tokens=800
    )
    return response.choices[0].message.content


# ────────────────────────────────────────────
# 로그 저장
# ────────────────────────────────────────────

def save_log(agenda, mode, log_lines):
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    safe_agenda = agenda[:20].replace(" ", "_").replace("/", "-")
    filename = f"{timestamp}_{safe_agenda}.md"

    content = "# MADEWELL AI BOARDROOM v0.1\n\n"
    content += f"- **일시**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    content += f"- **안건**: {agenda}\n"
    content += f"- **모드**: {mode}\n\n"
    content += "---\n\n"
    content += "\n\n---\n\n".join(log_lines)

    filepath = logs_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return filepath


# ────────────────────────────────────────────
# 출력 유틸
# ────────────────────────────────────────────

COLORS = {
    "blue":   "\033[94m",
    "green":  "\033[92m",
    "red":    "\033[91m",
    "yellow": "\033[93m",
    "reset":  "\033[0m",
    "bold":   "\033[1m",
    "dim":    "\033[2m",
}

def print_block(label, text, color="blue"):
    c = COLORS.get(color, "")
    r = COLORS["reset"]
    print(f"\n{c}{'─'*60}{r}")
    print(f"{c}{COLORS['bold']}{label}{r}")
    print(f"{c}{'─'*60}{r}")
    print(text)


def spinner_print(msg):
    print(f"\n{COLORS['dim']}⏳ {msg}...{COLORS['reset']}", end="", flush=True)


def done_print():
    print(f" {COLORS['dim']}완료{COLORS['reset']}")


# ────────────────────────────────────────────
# 메인 토론 로직
# ────────────────────────────────────────────

def run_boardroom(agenda, mode):
    log_lines = []
    claude_messages = []
    gpt_messages = []

    opening = f"안건: {agenda}\n\n이 안건에 대해 MADEWELL의 현재 상황을 고려해서 핵심 전략을 제시해주세요."

    # ── Claude 1차 ──────────────────────────
    spinner_print("Claude 분석 중")
    claude_messages.append({"role": "user", "content": opening})
    claude_1 = call_claude(claude_messages)
    claude_messages.append({"role": "assistant", "content": claude_1})
    done_print()

    print_block("🔵 Claude — 1차 전략 제시", claude_1, "blue")
    log_lines.append(f"## 🔵 Claude — 1차 전략 제시\n\n{claude_1}")

    # ── QUICK 모드 ───────────────────────────
    if mode == "quick":
        spinner_print("GPT 정리 중")
        gpt_messages.append({"role": "user", "content": f"Claude의 의견:\n\n{claude_1}\n\n이를 바탕으로 최종 액션 아이템 3가지를 정리해주세요."})
        gpt_final = call_gpt(gpt_messages, system=SECRETARY_SYSTEM)
        done_print()

        print_block("📋 최종 결론", gpt_final, "yellow")
        log_lines.append(f"## 📋 최종 결론\n\n{gpt_final}")

    # ── STANDARD / DEEP 모드 ────────────────
    elif mode in ("standard", "deep"):

        # GPT 반박
        spinner_print("GPT 반박/보완 중")
        gpt_messages.append({"role": "user", "content": f"Claude가 다음과 같이 말했습니다:\n\n{claude_1}\n\n반박하거나 보완할 점을 제시해주세요."})
        gpt_1 = call_gpt(gpt_messages)
        gpt_messages.append({"role": "assistant", "content": gpt_1})
        done_print()

        print_block("🟢 GPT — 반박/보완", gpt_1, "green")
        log_lines.append(f"## 🟢 GPT — 반박/보완\n\n{gpt_1}")

        # Claude 재반응
        spinner_print("Claude 재반응 중")
        claude_messages.append({"role": "user", "content": f"GPT가 다음과 같이 말했습니다:\n\n{gpt_1}\n\n이에 대한 재반응을 주세요."})
        claude_2 = call_claude(claude_messages)
        claude_messages.append({"role": "assistant", "content": claude_2})
        done_print()

        print_block("🔵 Claude — 재반응", claude_2, "blue")
        log_lines.append(f"## 🔵 Claude — 재반응\n\n{claude_2}")

        # ── STANDARD: GPT 최종 정리 ──────────
        if mode == "standard":
            spinner_print("최종 정리 중")
            gpt_messages.append({"role": "user", "content": f"Claude 재반응:\n\n{claude_2}\n\n전체 토론을 종합해서 최종 결론을 정리해주세요."})
            gpt_final = call_gpt(gpt_messages, system=SECRETARY_SYSTEM)
            done_print()

            print_block("📋 최종 결론", gpt_final, "yellow")
            log_lines.append(f"## 📋 최종 결론\n\n{gpt_final}")

        # ── DEEP: GPT 심화 → Red Team → Secretary ──
        elif mode == "deep":

            # GPT 심화 반박
            spinner_print("GPT 심화 분석 중")
            gpt_messages.append({"role": "user", "content": f"Claude 재반응:\n\n{claude_2}\n\n더 날카롭게 반박하거나 놓친 각도의 전략을 추가해주세요."})
            gpt_2 = call_gpt(gpt_messages)
            gpt_messages.append({"role": "assistant", "content": gpt_2})
            done_print()

            print_block("🟢 GPT — 심화 반박", gpt_2, "green")
            log_lines.append(f"## 🟢 GPT — 심화 반박\n\n{gpt_2}")

            # Red Team
            spinner_print("Red Team 리스크 공격 중")
            full_discussion = (
                f"Claude 1차:\n{claude_1}\n\n"
                f"GPT 반박:\n{gpt_1}\n\n"
                f"Claude 재반응:\n{claude_2}\n\n"
                f"GPT 심화:\n{gpt_2}"
            )
            red_prompt = f"지금까지의 전략 토론:\n\n{full_discussion}\n\n이 모든 전략의 약점과 실패 가능성을 공격해주세요."
            red_response = call_claude([{"role": "user", "content": red_prompt}], system=RED_TEAM_SYSTEM)
            done_print()

            print_block("🔴 Red Team — 리스크 공격", red_response, "red")
            log_lines.append(f"## 🔴 Red Team — 리스크 공격\n\n{red_response}")

            # Secretary 최종
            spinner_print("Secretary 최종 결론 작성 중")
            secretary_prompt = (
                f"전체 토론:\n\n{full_discussion}\n\n"
                f"Red Team 공격:\n{red_response}\n\n"
                f"이를 종합해서 최종 결론을 정리해주세요."
            )
            secretary_response = call_gpt(
                [{"role": "user", "content": secretary_prompt}],
                system=SECRETARY_SYSTEM
            )
            done_print()

            print_block("📋 Secretary — 최종 결론", secretary_response, "yellow")
            log_lines.append(f"## 📋 Secretary — 최종 결론\n\n{secretary_response}")

    # 로그 저장
    filepath = save_log(agenda, mode, log_lines)
    print(f"\n{COLORS['dim']}💾 회의록 저장됨: {filepath}{COLORS['reset']}\n")


# ────────────────────────────────────────────
# 실행 진입점
# ────────────────────────────────────────────

def main():
    # API 키 체크
    if not ANTHROPIC_API_KEY:
        print("\n❌ ANTHROPIC_API_KEY가 .env에 없습니다.\n")
        sys.exit(1)
    if not OPENAI_API_KEY:
        print("\n❌ OPENAI_API_KEY가 .env에 없습니다.\n")
        sys.exit(1)

    print(f"\n{COLORS['bold']}{'='*60}")
    print("  MADEWELL AI BOARDROOM v0.1")
    print("  Claude × GPT 전략 토론 시스템")
    print(f"{'='*60}{COLORS['reset']}")

    agenda = input("\n📌 안건을 입력하세요: ").strip()
    if not agenda:
        print("안건을 입력해주세요.")
        sys.exit(1)

    print(f"\n{COLORS['dim']}모드를 선택하세요:")
    print("  1. quick    — Claude → GPT 정리           (~20초, 간단한 안건용)")
    print("  2. standard — Claude ↔ GPT × 2 + 정리    (~45초, 기본 회의)")
    print(f"  3. deep     — 4라운드 + Red Team + 결론  (~90초, 중요 결정){COLORS['reset']}")

    mode_input = input("\n모드 선택 (1/2/3, 기본값 2): ").strip()
    mode_map = {"1": "quick", "2": "standard", "3": "deep", "": "standard"}
    mode = mode_map.get(mode_input, "standard")

    print(f"\n{COLORS['bold']}🎙 [{mode.upper()} 모드] 회의를 시작합니다{COLORS['reset']}")

    try:
        run_boardroom(agenda, mode)
    except KeyboardInterrupt:
        print(f"\n\n{COLORS['dim']}회의가 중단되었습니다.{COLORS['reset']}\n")
        sys.exit(0)

    input(f"\n{COLORS['dim']}Enter를 누르면 종료합니다...{COLORS['reset']}")


if __name__ == "__main__":
    main()
