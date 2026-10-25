"""Guard original trading bodies against accidental instrumentation edits."""
import hashlib
import json
import re
from pathlib import Path

here = Path(__file__).resolve().parent
text = (here.parent / 'NYOpenFairPriceStrategy.cs').read_text()
expected = json.loads((here / 'strategy_contract.json').read_text())
for name, digest in expected.items():
    if name == 'OnStateChangeDefaults':
        start = text.index('        protected override void OnStateChange()')
        start = text.index('{', start) + 1
        end = text.index('                DebugVisuals = true;', start) + len('                DebugVisuals = true;')
        assert hashlib.sha256(text[start:end].strip().encode()).hexdigest() == digest, name
        continue
    match = re.search(r'(?:protected override|private) (?:void|double|int) ' + name + r'\([^)]*\)\s*\{', text)
    assert match, name
    start = end = match.end()
    depth = 1
    while depth:
        if text[end] == '{':
            depth += 1
        elif text[end] == '}':
            depth -= 1
        end += 1
    body = text[start:end-1]
    if name == 'OnBarUpdate':
        body = body[body.index('            if (CurrentBar < BarsRequiredToTrade)'):]
    assert hashlib.sha256(body.strip().encode()).hexdigest() == digest, name
print('Original trading body hashes match')
