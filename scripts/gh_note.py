"""Print a GitHub Actions annotation with proper escaping: python -m scripts.gh_note notice|error TITLE FILE_OR_TEXT [MAXCHARS]."""
import sys
from pathlib import Path
kind, title, src = sys.argv[1], sys.argv[2], sys.argv[3]
limit = int(sys.argv[4]) if len(sys.argv) > 4 else 3500
text = Path(src).read_text(errors='replace') if Path(src).is_file() else src
lines = [l for l in text.replace('\r', '\n').split('\n') if l.strip() and 'it/s' not in l]
msg = ' | '.join(lines)[-limit:] or '(empty)'
esc = lambda s: s.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
print(f"::{kind} title={esc(title).replace(':', '%3A').replace(',', '%2C')}::{esc(msg)}")
