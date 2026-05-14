# MADEWELL AI BOARDROOM v0.3.9

포함 기능:
- v0.3.6 Safe Health Check / Task Lock
- v0.3.7 Image Upload / GPT Vision 요약
- v0.3.8 Endless Debate / 100-Branch Debate
- v0.3.9 Adaptive Endless: 최대 추가 재공방 횟수 + Continuation Check

핵심 변경:
- 끝장토론 후 곧바로 Final로 가지 않고, 추가 토론이 필요한지 판단합니다.
- CONTINUE이면 남은 쟁점에 대해 추가 재공방을 수행합니다.
- STOP이면 더 토론하지 않고 Final로 압축합니다.

실행:
```bash
cd "/Users/madewell/Documents/Claude/patch_v039_adaptive_endless" && cp ~/.env .env && python3 -m streamlit run app.py
```
