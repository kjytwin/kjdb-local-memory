"""Record native/protocol/package checks without claiming AI-app acceptance."""
import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

def main(archive):
    directory = Path(__file__).absolute().parent
    suite = unittest.defaultTestLoader.discover(str(directory), pattern='test_*.py')
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    print(output.getvalue(), end='')
    package = subprocess.run([sys.executable, '-B', str(directory / 'verify_package.py'), str(archive)],
                             input=b'', capture_output=True, timeout=90)
    payload = None
    if package.returncode == 0:
        payload = json.loads(package.stdout.decode('utf-8').splitlines()[-1])
    else:
        print(package.stderr.decode('utf-8', errors='replace')[-2000:])
    report = {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'tests_run': result.testsRun,
        'passed': result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
        'failures': len(result.failures), 'errors': len(result.errors),
        'skipped': [{'test': str(test), 'reason': reason} for test, reason in result.skipped],
        'package_verification': payload, 'package_verification_exit': package.returncode,
        'actual_ai_app_calls_for_this_snapshot': 'not established by this test run',
        'stable_release_approved': False}
    (directory / 'VALIDATION.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    (directory / 'VALIDATION.log').write_text(output.getvalue(), encoding='utf-8')
    print(json.dumps(report))
    return 0 if result.wasSuccessful() and package.returncode == 0 else 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    raise SystemExit(main(parser.parse_args().archive))
