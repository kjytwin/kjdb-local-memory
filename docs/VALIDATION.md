# 검증 범위

## 0.1.1 안정판의 범위

Windows x64 로컬 텍스트 메모리이며, Codex CLI / 독립 Claude Code CLI /
Claude Desktop 일반 채팅을 대상으로 한다. [출시 조건](STABLE_RELEASE_PLAN.md),
[업데이트·복원](UPDATE_AND_RECOVERY.md)을 함께 확인한다.

## 자동 검사

- 출시 후보 소스 c221da5b5a48aca5ad69e705caa4ceefb19714e6에서 production/fault DLL을 빌드했다.
- 호스트 Windows x64 / MSVC 19.43 / CPython 3.14: **23/23 통과, SKIP 0**.
- 별도 GitHub Windows runner / MSVC 19.44 / CPython 3.14: **23/23 통과, SKIP 0**.
  [CI 실행과 로그](https://github.com/kjytwin/kjdb-local-memory/actions/runs/38621465457).
- 범위: 저장·재시작·동일 요청 재시도·범위 거부·수정/삭제 충돌, busy·손상·링크 거부,
  생성/기록 중단 경계, UTF-8 stdio, ZIP 추출과 세 설정 생성기의 실제 실행.
- 추가 검사: 1,000개 한도 거부 전후 데이터 보존, 명시적 삭제 후 공간 재사용,
  SHA256 고정 미리보기 데이터의 읽기·수정·이전 패키지 재열기·백업 복원.
- 기준 미리보기 ZIP SHA256:
  `6184f1728cf4a7e0911a01df3d475e336bd83632c714772ceba9bc91b7d206af`.

## 실제 앱 확인과 근거의 한계

실제 앱 검증 ZIP은 [v0.1.1-rc.1](https://github.com/kjytwin/kjdb-local-memory/releases/tag/v0.1.1-rc.1)이며 SHA256은
`5cb83dd71d1e958e621d78ea55b3780707c3cf5a9974529c5dfd5cd4fa8cf59a`이다.

| 앱 | 확인 결과 | 근거 |
|---|---|---|
| Codex CLI 0.144.5 | remember 후 새 프로세스 search/get; 프로젝트·요청·메모리 UUID, 본문 해시 일치 | 실제 모델의 구조화된 MCP 결과를 비공개 검사 코드로 대조 |
| 독립 Claude Code 2.1.296 | 동일한 저장·새 프로세스 재조회 검사 통과 | 실제 모델의 tool_use/tool_result 대조 |
| Claude Desktop 2.37337.1 일반 채팅 | 사용자 제공 search/get 결과의 UUID·본문 일치; 후보 종료·재연결·도구 호출 기록 확인 | 사용자 제공 결과와 Desktop MCP 로그의 교차 확인 |

Desktop 합성 본문은 `KJDB-STABLE-7F3A9C`, 프로젝트는 `claude-desktop-memory`이다.
사용자가 전달한 본문 해시의 앞·뒤 값은 기대 SHA256과 일치했다. 기대 전체 해시는
`9ad3993925c3912e7609a1f06fc37cdf390d324a7eec37a81c38d4861be25346`이다. Desktop 로그는 호출 본문을 생략하므로, 전체 본문·UUID를
로그에서 독립적으로 확인했다고 주장하지 않는다. 사용자 제공 결과가 해당 근거다.

로그에서는 2026-10-15 04:18:39 KST 종료, 04:18:44 후보 재연결,
04:18:55 및 04:19:00 도구 호출/응답을 확인했다. 그 앞의 잘못된 `default` 프로젝트
요청은 범위 거부되었다. 안내를 실제 프로젝트 ID로 정정한 후 저장·조회가 수행되었다.
원본 앱 로그·프로필·사용자 데이터는 공개하지 않는다.

## 최종 ZIP 승격 검증

최종 0.1.1 ZIP은 후보와 동일한 runtime/native/tools 파일 집합과 개별 SHA256을
유지해야 한다. 바뀌는 것은 안내 문서와 버전·출시 상태 메타데이터다. 최종 ZIP의
추출 검사와 이 동일성 검사를 통과한 뒤 게시하며, 결과와 최종 ZIP 해시는 해당
[릴리스](https://github.com/kjytwin/kjdb-local-memory/releases/tag/v0.1.1)에 기록한다.
이는 최종 ZIP에서 Desktop 실사용을 다시 실행했다는 주장이 아니다.

## 지원 제외

Cowork/내장 Code는 추가 서버 시작으로 busy가 발생해 지원하지 않는다. 동일 프로젝트는
서버 하나만 소유한다. 의미 검색·자동 수집·암호화·안전한 물리 삭제도 지원하지 않는다.
Windows 파일 flush는 사용하지만 디렉터리 항목의 물리 전원 차단 내구성, 임의 악성
경로 교체, 장기 무중단 운영은 검증하지 않았다. 짧은 검사와 별도 CI runner는
장기 실사용 또는 일반 사용자 PC의 설치 검증을 대체하지 않는다.
