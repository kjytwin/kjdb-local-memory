# KJDB Local Memory

**내 컴퓨터에 기억을 저장하고 다시 조회하는 AI용 로컬 MCP 서버.**

Windows x64 미리보기입니다. Codex CLI, Claude Desktop 일반 채팅, 독립 Claude Code CLI용 설정을 생성합니다. 저장소와 MCP 서버는 사용자 PC에서 실행되며, KJDB 자체에는 별도의 API 키·클라우드 서버·터널이 필요하지 않습니다. AI 앱의 설치·로그인·이용 조건은 별도입니다.

## 먼저 알아둘 점

- 현재는 **개발 미리보기**입니다. 최신 공개 스냅샷의 테스트와 이전 앱 실사용 검증은 [검증 범위](docs/VALIDATION.md)에서 구분합니다.
- **Claude Desktop Cowork/내장 Code 세션은 지원하지 않습니다.** 한 프로젝트 저장소에는 서버 하나만 열 수 있습니다.
- 자동 대화 수집·의미 검색은 없습니다. 사용자가 요청한 텍스트를 명시적으로 저장합니다.
- MIT 라이선스입니다. 상업적 이용과 판매도 허용하며, 저작권·라이선스 고지를 유지해야 합니다.

## 사용 순서

1. [Releases](https://github.com/kjytwin/kjdb-local-memory/releases)에 실행 ZIP이 있으면 다운로드하고 압축을 풉니다. 아직 Release가 없다면 아래 소스 빌드 절차를 사용하세요. CI의 테스트 ZIP은 GitHub Actions artifact로 제공될 수 있으며, 안정판을 뜻하지 않습니다.
2. 원하는 앱의 설정을 생성합니다.
3. 생성된 명령 또는 JSON을 검토하고, 기존 앱 설정을 백업한 뒤 KJDB 항목을 등록합니다.
4. 앱의 새 세션에서 저장하고, 재시작 후 같은 원문이 조회되는지 확인합니다.

압축을 푼 폴더의 PowerShell에서:

```powershell
.\runtime\python.exe -I -B .\tools\local\kjdb_local.py --project my-project --diagnose
.\runtime\python.exe -I -B .\tools\local\generate_codex.py --package . --output .\setup-codex
```

[설치 안내](docs/INSTALL.md) · [Codex](tools/local/CODEX.md) · [Claude Desktop](tools/local/CLAUDE_DESKTOP.md) · [Claude Code](tools/local/CLAUDE_CODE.md)

## 제공 도구

| 도구 | 기능 |
|---|---|
| remember | 텍스트 저장·버전 갱신. 동일 request_id와 동일 입력의 재요청은 중복 처리 |
| search | 키워드·부분 문자열 검색 |
| get | 기억 UUID로 원문 조회 |
| forget | 버전을 확인한 논리 삭제. 보안 삭제는 아님 |
| memory_status | 프로젝트 저장소의 상태 조회 |

기본 데이터 위치는 %LOCALAPPDATA%\KJDB\stores\프로젝트이름입니다. 프로젝트 이름별로 데이터가 분리됩니다. 앱마다 기본 프로젝트가 다르며, 같은 프로젝트를 동시에 열면 두 번째 서버는 busy로 거부됩니다. [개인정보·보존 안내](docs/PRIVACY.md)를 확인하세요.

## 소스 빌드

개발자에게는 Windows x64, Visual Studio의 C++ 빌드 도구·Windows SDK, CMake, Python 3.14가 필요합니다.

```powershell
cmake -S tools/local -B build-local/native -A x64
cmake --build build-local/native --config Release
cmake -S tools/local -B build-local/fault -A x64 -DKJM_TESTING=ON
cmake --build build-local/fault --config Release
```

패키지 제작과 테스트 절차는 [BUILDING.md](BUILDING.md)에 있습니다. 완성된 실행 ZIP을 사용하는 사용자는 Python이나 C 컴파일러를 별도로 설치할 필요가 없습니다.

## 범위와 한계

이 저장소는 KJDB의 **텍스트 메모리 구성요소**와 클라이언트 연결 도구를 배포합니다. 전체 토큰 DB 엔진·LQL·JIT·원격 대화 아카이브 제품을 포함하지 않습니다.

로그 최대 32 MiB, 기록 최대 8,192회, 활성 기억 최대 1,000개입니다. 자동 확장·압축·암호화·안전한 완전 삭제는 지원하지 않습니다. Windows 파일 flush는 제공하지만 디렉터리 항목의 물리 전원 손실 내구성은 미검증입니다.

[검증 범위](docs/VALIDATION.md) · [변경 기록](CHANGELOG.md) · [기여 안내](CONTRIBUTING.md) · [MIT LICENSE](LICENSE)
