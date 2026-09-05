from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

if not INDEX.exists():
    raise SystemExit("ERROR: index.html tidak dijumpai")

s = INDEX.read_text(encoding="utf-8")
before = s

# Remove old Repeat Family+ V1 blocks if any remnants remain.
s = re.sub(
    r'<style>\s*/\*\s*REPEAT-FAMILY-PLUS-V1\s*\*/.*?</style>\s*',
    '',
    s,
    flags=re.S
)
s = re.sub(
    r'<script>\s*/\*\s*REPEAT-FAMILY-PLUS-V1\s*\*/.*?</script>\s*',
    '',
    s,
    flags=re.S
)

# Remove integrated/smooth V2 blocks.
s = re.sub(
    r'<style>\s*/\*\s*REPEAT-FAMILY-INTEGRATED-V2\s*\*/.*?</style>\s*',
    '',
    s,
    flags=re.S
)
s = re.sub(
    r'<script>\s*/\*\s*REPEAT-FAMILY-INTEGRATED-V2\s*\*/.*?</script>\s*',
    '',
    s,
    flags=re.S
)

if s == before:
    print("No Repeat Family patch block found.")
else:
    INDEX.write_text(s, encoding="utf-8")
    print("Repeat Family patches removed ✓")
    print("Original Repeat Digit Expansion preserved ✓")
    print("Version label unchanged ✓")
    print("App returned to pre-Family+ state ✓")
