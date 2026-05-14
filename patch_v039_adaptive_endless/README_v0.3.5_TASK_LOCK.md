# MADEWELL AI BOARDROOM v0.3.5 Task Lock Hotfix

수정 사항:
- memory/*.md 자동 로딩 추가
- API 연결 테스트는 War Room 체인을 타지 않고 Health Check Mode로 처리
- 오늘의 안건을 최우선으로 고정하는 Task Lock 추가
- AI 회의실/API/오류/메모리 관련 안건에서 Claude가 MAMA 카피로 튀지 않도록 기술 안건 라우팅 추가
- strategy_kernel.md / always_on_boardroom_rules.md 기본 포함

사용:
- .env는 기존 파일을 복사해서 사용
- Gemini 사용 시 USE_GEMINI_API=1 / GEMINI_STRICT=0
