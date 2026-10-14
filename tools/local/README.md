# KJDB Local Memory — Windows x64 0.1.1

이 폴더는 AI 앱에 연결하는 로컬 텍스트 메모리 실행 패키지입니다. KJDB 자체에는 API 키·클라우드 서버·터널이 필요하지 않으며, AI 앱은 별도로 설치·로그인해야 합니다.

PowerShell에서:

```powershell
.\runtime\python.exe -I -B .\tools\local\kjdb_local.py --project my-project --diagnose
.\runtime\python.exe -I -B .\tools\local\generate_codex.py --package . --output .\setup-codex
.\runtime\python.exe -I -B .\tools\local\generate_claude_desktop.py --package . --output .\setup-desktop
.\runtime\python.exe -I -B .\tools\local\generate_claude_code.py --package . --output .\setup-claude-code
```

사용할 앱의 생성기만 실행해도 됩니다. 생성된 명령·설정 조각을 검토하고 기존 앱 설정을 백업한 뒤 KJDB 항목만 병합하세요. 설정 생성기는 앱 프로필을 자동 변경하지 않습니다. 출력 폴더를 덮어쓰지 않으므로 재생성할 때는 새 경로를 사용합니다.

앱별 안내는 패키지 guides 폴더에 있습니다. 일반 Claude Desktop 채팅만 지원하며 Cowork/내장 Code는 제외합니다. 기본 프로젝트는 codex-memory, claude-desktop-memory, claude-code-memory입니다.

기본 데이터는 %LOCALAPPDATA%\KJDB\stores에 저장됩니다. 프로젝트당 한 서버만 열 수 있으며 두 번째는 busy로 거부됩니다. 저장된 기억은 평문이고 forget은 논리 삭제입니다. AI 앱이 읽은 텍스트를 어떻게 처리하는지는 해당 앱의 정책을 따릅니다.

로그 32 MiB, 기록 8,192회, 활성 기억 1,000개 한계가 있습니다. 자동 수집·의미 검색·압축·암호화·보안 삭제는 제공하지 않습니다. Windows 디렉터리 항목의 물리 전원 손실 내구성은 미검증입니다.

Windows x64 로컬 텍스트 메모리 안정판입니다. 검증 범위는 docs/VALIDATION.md, 업데이트·복원은 docs/UPDATE_AND_RECOVERY.md를 확인하세요. MIT 고지는 LICENSE, Python 및 제삼자 고지는 runtime/LICENSE.txt에 있습니다.
