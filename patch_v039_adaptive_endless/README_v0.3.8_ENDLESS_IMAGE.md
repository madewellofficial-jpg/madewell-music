# MADEWELL AI BOARDROOM v0.3.8

포함 기능:
- v0.3.6 Safe Health Check / Task Lock
- v0.3.7 이미지 업로드 + GPT Vision 요약
- v0.3.8 Endless Debate / 100-Branch Debate

## 실행

```bash
cd "/Users/madewell/Documents/Claude/patch_v038_endless_image"
cp ~/.env .env
python3 -m streamlit run app.py
```

또는 폴더 안 `00_START_MADEWELL_BOARDROOM.command` 더블클릭.

## 새 회의 모드

- ♾ Endless Debate — 끝장토론
  - Task Lock → 최초 주장 → 상호공격 → Steelman → 수정안 → Red Team → 점수화 → 최종협상 → Final

- 💣 100-Branch Debate — 100가설 끝장토론
  - 100개 가설/실패경로를 먼저 펼친 뒤 카테고리로 묶고 상위 10개를 놓고 끝장토론

## 사용 팁

가벼운 안건에는 Standard/Debate.
중요한 광고/프리오더/브랜드 판단에는 Endless Debate.
진짜 큰 의사결정에는 100-Branch Debate.

## 주의

100-Branch Debate는 API 호출과 토큰을 많이 사용합니다. 중요한 안건에만 사용하세요.
