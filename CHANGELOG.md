# 변경 기록

## 0.1.1 — Windows x64 안정판

- Codex CLI, 독립 Claude Code CLI, Claude Desktop 일반 채팅의 명시적 로컬 메모리 저장·조회.
- 호스트 및 별도 GitHub Windows runner에서 23/23 검사 통과, SKIP 0.
- 1,000개 한도에서 기존 데이터 보존, 미리보기 업그레이드·이전 버전 재열기·백업 복원 검사 추가.
- 업데이트·백업·복원 문서 및 명시적인 패키지 출시 상태.
- 실제 앱 검증은 rc.1에서 수행했다. 최종 ZIP의 runtime/native/tools 파일 집합과 SHA256이
  후보와 같음을 확인한 경우에만 해당 실행 코드의 검증 결과를 승계한다.

Desktop Cowork/내장 Code, 의미 검색, 자동 수집, 암호화, 안전한 물리 삭제,
물리 전원 차단 내구성은 지원 범위에 포함하지 않는다.

## 0.1.1-preview — 공개 준비

- 프로젝트별 로컬 텍스트 저장·키워드 검색·원문 조회·논리 삭제·상태 조회.
- Windows native DLL과 isolated Python을 포함하는 패키지 생성.
- Codex CLI·Claude Desktop 일반 채팅·독립 Claude Code CLI 설정 생성.
- 중복 요청, 범위 거부, 재시작 보존, 손상 거부, 동시 서버 거부 및 생성 중단 검증.
- MIT 라이선스와 파일별 SHA-256 목록.

Cowork/내장 Code, 의미 검색, 자동 수집, 암호화, 보안 삭제, 물리 전원 손실 내구성은 지원 또는 검증 완료 범위에 포함하지 않습니다. 안정판 Release를 발행한 기록이 아닙니다.
