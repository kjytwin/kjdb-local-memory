# 개발용 빌드·패키지 검증

Windows x64에서 Visual Studio C++ 빌드 도구·Windows SDK·CMake·Python 3.14를 준비합니다. PowerShell의 저장소 루트에서 실행합니다.

```powershell
cmake -S tools/local -B build-local/native -A x64
cmake --build build-local/native --config Release
cmake -S tools/local -B build-local/fault -A x64 -DKJM_TESTING=ON
cmake --build build-local/fault --config Release
$kjdbPythonRoot = python -c "import sys; print(sys.prefix)"
python -B tools/local/package_windows.py --destination dist/KJDB-Windows-x64-preview --library build-local/native/Release/kjdb_memory.dll --python-root $kjdbPythonRoot
$env:KJDB_TEST_LIBRARY = Join-Path $PWD 'build-local/native/Release/kjdb_memory.dll'
$env:KJDB_TEST_FAULT_LIBRARY = Join-Path $PWD 'build-local/fault/Release/kjdb_memory.dll'
$env:KJDB_TEST_PACKAGE = Join-Path $PWD 'dist/KJDB-Windows-x64-preview'
python -B tools/local/run_validation.py dist/KJDB-Windows-x64-preview.zip
```

패키지 생성 전에 tracked 소스가 커밋돼 있어야 합니다. 기존 ZIP·출력 폴더는 덮어쓰지 않습니다. 재빌드에는 새 destination을 사용하세요.

검증은 실제 native DLL, fault-injection DLL, ZIP을 새 한글·공백 경로에 풀어 포함 Python으로 실행하는 과정과 세 앱 설정 생성기를 확인합니다. 실제 로그인한 AI 모델의 도구 호출과는 별도입니다.

DLL은 이 소스 스냅샷에서 새로 빌드하세요. 다른 커밋의 fault DLL을 재사용하면 단계별 중단·경쟁 생성 테스트를 올바르게 검사할 수 없습니다. fault DLL은 테스트 전용이며 사용자 실행 ZIP에는 포함되지 않습니다.
