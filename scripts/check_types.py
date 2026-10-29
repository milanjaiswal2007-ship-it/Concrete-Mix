import json

with open('data/examples/special/special_concrete_mixes.jsonl', 'r', encoding='utf-8') as f:
    lines = [json.loads(line) for line in f]

seen = set()
for r in lines:
    t = r['concrete_type']
    if t not in seen:
        seen.add(t)
        src = r.get("source", "")
        nts = r.get("notes", "")
        print(f"[{t}]")
        print(f"  Source: {src}")
        print(f"  Notes:  {nts}")
