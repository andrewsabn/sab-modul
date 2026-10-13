"""Verify that this project has not changed its frozen Mono inputs or release."""
from pathlib import Path
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]
baseline = json.loads((ROOT / 'checks/mono-before.json').read_text())
original = Path(baseline['root'])
failures = []
for relative, expected in baseline['files'].items():
    path = original / relative
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    if actual != expected:
        failures.append({'file': relative, 'expected': expected, 'actual': actual})
result = {'checked': len(baseline['files']), 'unchanged': len(baseline['files']) - len(failures),
          'failures': failures, 'pass': not failures}
(ROOT / 'checks/mono-regression.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
raise SystemExit(bool(failures))
