# Project instructions

- This repository contains the standalone KJDB local text-memory product. Keep token-engine experiments, private archives, host settings and raw personal logs out of it.
- Use existing code and standard-library tools. Plan changes before implementation; record two self reviews, up to three clearly labeled fictional-manager findings, and fix actual defects.
- Test through real native storage and isolated bundled Python. Generated settings and direct protocol tests do not establish actual AI-app model calls.
- Preserve one-server-per-project ownership, existing user settings, corruption refusal and explicit write intent. Never weaken locking or overwrite data to make a test pass.
- Preserve standard MIT and third-party notices. Public visibility does not imply a stable release.
- A preview may be published only with explicit scope and remaining limitations. Keep Cowork/embedded Code excluded until separately qualified.
- Keep source commits/runtime versions in package metadata. Test the extracted archive, not just the source tree. Record unavailable platform privileges as skips.
- No credentials, user DBs, private profile copies or private repository history may be committed. Scan staged content and check an explicit file allowlist before publication.
- Fail fast when a required PowerShell command is unavailable; do not let a stale or undefined LASTEXITCODE turn command-not-found into a successful build. Use installed tool paths without changing execution/security policies.
- Append .zip to a package directory name; do not replace its suffix because semantic versions contain dots. The CI destination must contain a dotted version and verify the expected full ZIP name.
- Windows storage tests must respect native file locks: take native backups while open and compare raw log bytes only after closing. Never relax locks for test inspection.
- Pin an upgrade baseline by release asset SHA256. Missing baseline or missing actual app evidence cannot be counted as a stable-release pass.
- For candidate promotion, compare the exact set and SHA256 of every runtime/native/tools file in the final ZIP with the app-qualified candidate. Document user-reported app results separately from logs that omit tool payloads.
- Every user-facing memory test prompt must state the configured project_id; never suggest default unless that is the configured project.
