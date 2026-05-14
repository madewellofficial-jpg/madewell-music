# MADEWELL AI BOARDROOM v0.3 — Live War Room

터미널 발표회가 아니라 브라우저에서 라운드별로 진행되는 AI 전략 회의실입니다.

## 실행

```bash
cd MADEWELL-AI-BOARDROOM
pip3 install -r requirements.txt
streamlit run app.py
```

브라우저가 열리면 `http://localhost:8501`에서 사용합니다.

## API 키

`.env.example`을 복사해서 `.env`로 만들고 키를 넣습니다.

```bash
cp .env.example .env
nano .env
```

`.env`는 절대 업로드/공유/GitHub 커밋 금지입니다.

## v0.3 핵심 변경

- Claude → Gemini → GPT → Red Team → Claude 재반박 → Gemini 재평가 → GPT 쟁점판정 → Final Arbiter 구조
- 각 모델은 이전 발언을 인용/반박/수정하도록 강제
- Red Flag: 구걸/죄책감/스팸 DM/브랜드 훼손/실행 불가능 제안 차단
- 회의 과정이 카드별로 실시간 표시
- 회의록은 `logs/`에 저장
- 람보 인수인계용 요약은 `handoff/latest_for_rambo.md`에 저장

## 주의

- Gemini 호출은 `requests` 기반 REST API를 사용합니다.
- API 키가 있어도 실제 API 네트워크/권한/모델명 오류가 있으면 화면에 상세 오류가 표시됩니다.


## v0.3.1 hotfix
- 기본 Claude 모델을 claude-sonnet-4-6으로 변경
- 기본 GPT 모델을 gpt-5.5로 변경
- 기본 Gemini 모델을 gemini-3.1-pro-preview로 변경
- 더블클릭 실행용 Start_MADEWELL_Boardroom.command 추가

실행:
1. .env.example을 .env로 복사하고 API 키 입력
2. pip3 install -r requirements.txt
3. Start_MADEWELL_Boardroom.command 더블클릭 또는 python3 -m streamlit run app.py


## v0.3.2 Gemini quota hotfix
- 기본 Gemini 모델을 `gemini-2.5-flash`로 낮췄습니다.
- `gemini-3.1-pro-preview`는 무료 티어 quota가 0일 수 있어 429가 날 수 있습니다.
- Gemini 호출 실패 시 기본적으로 GPT가 Gemini 역할(시장/트렌드/대중성)을 임시 대체합니다.
- 실제 Gemini 에러를 그대로 보고 싶으면 `.env`에 `GEMINI_STRICT=1`을 넣으세요.


## v0.3.3 Hotfix
- OpenAI GPT-5 계열에서 `max_tokens`가 거부되는 문제를 수정했습니다.
- OpenAI 호출은 우선 Responses API(`max_output_tokens`)를 사용하고, 실패 시 Chat Completions(`max_completion_tokens`)로 폴백합니다.


## v0.3.7 Image Upload
- Streamlit 화면에서 캡쳐/이미지 업로드 가능
- OpenAI Vision으로 이미지 사실/수치/문구를 회의실 입력용 텍스트로 자동 요약
- 요약 결과는 현재 상황 칸에 자동 삽입
- 주의: API 키/개인정보가 보이는 캡쳐는 업로드 전 가리기
