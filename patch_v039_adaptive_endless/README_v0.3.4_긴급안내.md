# MADEWELL AI BOARDROOM v0.3.4

## 핵심 변경
- 실제 Gemini API 호출 기본 OFF (`USE_GEMINI_API=0`)
- Gemini 키 만료/쿼터 오류 때문에 회의가 죽지 않음
- GPT가 Gemini 역할(시장/트렌드/대중성)을 안전하게 대체

## 실행
1. `.env.example`을 `.env`로 복사
2. `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`만 정확히 넣어도 실행 가능
3. Gemini 키는 비워도 됨
4. `00_START_MADEWELL_BOARDROOM.command` 더블클릭

## 실제 Gemini를 꼭 쓰고 싶을 때만
`.env`에서 `USE_GEMINI_API=1`로 변경. 단, Google API 키 만료/쿼터/빌링 오류가 나면 다시 앱이 멈출 수 있음.
