# save as fix_formatting.py and run once locally
import json
import re

def clean_linkedin(text: str) -> str:
    # Remove bold markdown — **text** → TEXT for emphasis
    text = re.sub(r'\*\*(.+?)\*\*', lambda m: m.group(1).upper(), text)

    # Remove italic markdown — *text* or _text_
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)

    # Replace ```lang\ncode\n``` with clean labeled block
    def format_code(m):
        code = m.group(2).strip()
        return f"\nCommand:\n{code}\n"
    text = re.sub(r'```(\w+)?\n(.*?)```', format_code, text, flags=re.DOTALL)

    # Remove any remaining backticks
    text = re.sub(r'`(.+?)`', r'\1', text)

    # Remove markdown headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Clean up excessive blank lines (max 2)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()

with open('state/pipeline_state.json') as f:
    state = json.load(f)

# Fix tips
fixed_count = 0
for tip in state['tips']:
    original = tip['content']
    tip['content'] = clean_linkedin(original)
    if tip['content'] != original:
        fixed_count += 1

# Fix schedule (tips are duplicated inside schedule entries too)
for item in state['schedule']:
    if 'tip' in item:
        original = item['tip']['content']
        item['tip']['content'] = clean_linkedin(original)

with open('state/pipeline_state.json', 'w') as f:
    json.dump(state, f, indent=2)

print(f"Fixed formatting in {fixed_count} tips")

# Preview Day 4 (next unposted)
day4 = next(t for t in state['tips'] if t['day'] == 4)
print("\n--- Day 4 preview ---")
print(day4['content'][:500])