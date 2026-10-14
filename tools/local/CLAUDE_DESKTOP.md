# Claude Desktop 일반 채팅 연결

현재 지원 범위는 일반 채팅입니다. Cowork/내장 Code에서 같은 설정을 공유하는 추가 인스턴스는 busy로 종료될 수 있습니다.

```powershell
.\runtime\python.exe -I -B .\tools\local\generate_claude_desktop.py --package . --output .\setup-desktop
```

생성된 claude_desktop_config.proposed.json의 mcpServers 아래 kjdb_local_memory 항목만 기존 %APPDATA%\Claude\claude_desktop_config.json에 병합합니다. 원본 설정을 비공개로 백업하고 다른 서버·설정은 보존하세요.

기존 설정을 읽어 제안 파일을 만들려면 --existing 옵션을 사용할 수 있습니다. 해당 출력에는 기존 앱 설정이 들어갈 수 있으므로 공유하거나 Git에 올리지 마세요.

Microsoft Store 설치판은 앱 데이터 경로가 가상화될 수 있습니다. 앱이 실제로 읽는 설정 파일을 확인하고, 두 경로가 같은 파일인지 확인하지 않은 채 각각 덮어쓰지 마세요.

앱을 완전히 종료한 뒤 다시 열고 일반 채팅의 새 세션에서 저장을 시험합니다. 기본 프로젝트는 claude-desktop-memory입니다. 서버 재시작 후 search/get으로 같은 UUID·원문을 확인합니다. 도구가 표시되는 것만으로 재시작 보존을 검증했다고 판단하지 않습니다.
