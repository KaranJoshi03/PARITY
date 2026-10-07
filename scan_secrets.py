import os
import re
from pathlib import Path

patterns = {
    'API Key / Token': r'(?:api[_-]?key|secret|token|password|auth|bearer)[\s:=]+[\'"][A-Za-z0-9_\-]{8,} [\'"]',
    'Email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    'Absolute Path (Windows)': r'[C-Z]:\\[^\s:\'"]+'
}

root = Path('.')
findings = []

for p in root.rglob('*'):
    if p.is_file() and not any(part.startswith('.') or part in ['node_modules', 'venv', 'brain'] for part in p.parts):
        try:
            content = p.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                for label, pat in patterns.items():
                    matches = re.findall(pat, line, re.IGNORECASE)
                    if matches:
                        for m in matches:
                            findings.append((str(p), i, label, m))
        except Exception:
            pass

print(f"Total findings: {len(findings)}")
for f in findings[:30]:
    print(f"{f[0]}:{f[1]} [{f[2]}] -> {f[3]}")
