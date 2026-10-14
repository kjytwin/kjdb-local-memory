# Codex CLI 연결

압축을 푼 패키지 폴더의 PowerShell에서:

```powershell
.\runtime\python.exe -I -B .\tools\local\generate_codex.py --package . --output .\setup-codex
```

생성된 setup-codex/codex-config.toml과 register-codex.ps1을 확인합니다. 등록 스크립트에 적힌 codex mcp add 명령을 실행하거나, TOML의 kjdb_local_memory 항목을 기존 Codex 설정에 병합합니다. 다른 설정을 보존하고 먼저 백업하세요.

새 Codex 세션에서 /mcp로 연결을 확인합니다. 기본 프로젝트는 codex-memory입니다. 합성 문구를 remember로 저장하고, 별도 세션에서 search/get으로 같은 UUID와 원문을 확인합니다.

설정 생성은 실제 모델 호출 검증과 다릅니다. 사용 중인 Codex 로그인과 모델 지원 여부는 Codex에서 확인하세요. 저장소가 busy라면 동일 프로젝트를 여는 다른 서버를 먼저 종료합니다.
