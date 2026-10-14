# Windows 설치·연결

기존 사용자는 [업데이트·백업·복원](UPDATE_AND_RECOVERY.md) 절차를 먼저 확인하세요.

## 실행 패키지

ZIP을 새 폴더에 풀고 runtime, native, tools 폴더가 함께 있는지 확인합니다. 패키지를 옮기면 앱에 등록한 실행 경로도 다시 생성해야 합니다. 업데이트할 때 이전 폴더를 먼저 삭제하지 마세요. 데이터는 패키지 폴더와 별도로 보관됩니다.

PowerShell에서 압축을 푼 폴더로 이동한 뒤 실행합니다.

```powershell
.\runtime\python.exe -I -B .\tools\local\kjdb_local.py --project my-project --diagnose
```

성공하면 해당 프로젝트의 로컬 저장소 상태를 보여줍니다. 진단 실행도 새 프로젝트 저장소를 만들 수 있습니다. 기존 DB가 손상됐다면 삭제·초기화하지 말고 원본부터 보존하세요.

## 앱 선택

- [Codex CLI](../tools/local/CODEX.md)
- [Claude Desktop 일반 채팅](../tools/local/CLAUDE_DESKTOP.md)
- [독립 Claude Code CLI](../tools/local/CLAUDE_CODE.md)

설정 생성기는 검토용 파일만 만들며 앱 설정을 자동으로 변경하지 않습니다. 같은 이름의 서버가 이미 등록돼 있으면 내용을 확인하고 기존 설정을 백업하세요. 다른 서버 항목을 덮어쓰지 마세요.

## 저장·재시작·조회 확인

앱에 등록한 뒤 새 세션에서 프로젝트 ID를 지정해 합성 문구를 저장하도록 요청합니다. Codex 기본 프로젝트는 codex-memory, Desktop은 claude-desktop-memory, Claude Code는 claude-code-memory입니다.

예: “KJDB remember 도구로 project_id가 codex-memory인 저장소에 ‘로컬 연결 시험’이라는 기억을 저장해줘. 새 UUID request_id를 사용해줘.”

저장 성공 후 앱 또는 서버를 재시작하고 새 세션에서 search와 get으로 같은 UUID·원문을 확인합니다. 설정이 보이는 것만으로 이 과정이 성공했다고 판단하지 마세요.

## 자주 만나는 문제

| 현상 | 확인할 점 |
|---|---|
| store busy | 같은 프로젝트를 사용하는 다른 서버를 종료하거나 앱별 프로젝트를 분리 |
| 도구 없음 | 등록된 절대 경로, 앱 재시작·새 세션, 실제 서버 로그 확인 |
| Cowork/내장 Code에서 연결 실패 | 현재 지원 범위 밖. 일반 채팅 또는 독립 Claude Code 사용 |
| 손상·복구 필요 오류 | 데이터 원본 보존. 임의 삭제·반복 쓰기 금지 |
| 새 출력 폴더가 필요하다는 오류 | 설정 생성기는 덮어쓰지 않음. 새 --output 경로 지정 |

KJDB는 모델을 선택하거나 앱 로그인 문제를 해결하지 않습니다. CLI에서 지원하는 모델과 로그인 상태는 해당 앱 안내를 따릅니다.
