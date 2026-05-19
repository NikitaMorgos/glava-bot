import sys
sys.stdout.reconfigure(encoding='utf-8')
import re

patterns = [
    r"Каракулин", r"Татьян", r"Валентин", r"Химинститут",
    r"выковырив", r"зарубить", r"зажиточн", r"движуха",
    r"рукаст", r"бабульно", r"Молдави", r"1946 год", r"две недели",
]
combined = re.compile("|".join(patterns), re.IGNORECASE)

filepath = "prompts/03_ghostwriter_v2.24.md"
matches_body = []
matches_header = []

with open(filepath, encoding="utf-8") as f:
    lines = f.readlines()

# Determine where version history header ends
# Body starts at the first top-level rule/system prompt section
header_end = 0
for i, line in enumerate(lines):
    stripped = line.rstrip()
    if stripped in ("## SYSTEM PROMPT", "## Системный промпт") or \
       (stripped.startswith("## ПРАВИЛО") and not stripped.startswith("### ")) or \
       stripped.startswith("## ЗАПРЕТ") or \
       stripped == "---":
        header_end = i
        break

for i, line in enumerate(lines):
    if combined.search(line):
        entry = f"L{i+1}: {line.rstrip()}"
        if i < header_end:
            matches_header.append(entry)
        else:
            matches_body.append(entry)

print(f"Header matches (allowed): {len(matches_header)}")
for m in matches_header:
    print(" ", m)
print(f"Body matches (must be 0): {len(matches_body)}")
for m in matches_body:
    print(" ", m)

if matches_body:
    print("\nFAIL — universality violation in body!")
    sys.exit(1)
else:
    print("\nPASS — 0 body matches. Universality OK.")
