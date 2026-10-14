# 독립 Claude Code CLI 연결

이 안내는 독립 Claude Code CLI용이며 Desktop 내장 Code 지원을 뜻하지 않습니다.

```powershell
.\runtime\python.exe -I -B .\tools\local\generate_claude_code.py --package . --output .\setup-claude-code
```

생성된 claude-code-mcp.json과 register-claude-code.ps1의 명령을 검토합니다. 기존 사용자 설정을 비공개 백업한 뒤 등록 스크립트의 claude mcp add 명령을 실행합니다. 기존 동명 항목이 있으면 먼저 내용을 확인하세요.

새 Claude Code 세션에서 /mcp 또는 claude mcp list로 연결을 확인합니다. 기본 프로젝트는 claude-code-memory입니다. remember 저장 후 별도 세션에서 search/get으로 같은 UUID·원문을 확인합니다.

같은 프로젝트를 다른 앱과 동시에 열지 마세요. 앱마다 별도 기본 프로젝트를 사용하면 저장소도 분리됩니다. 계정 로그인·구독·지원 모델은 해당 앱의 조건을 따릅니다.
