#!/usr/bin/env python3
"""Parse the tool-index.md markdown table and output tool-index.json."""
import json, re, sys, os
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

def main():
    md_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'tool-index.md')
    json_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), '..', 'tool-index.json')

    with open(md_path, encoding='utf-8') as f:
        content = f.read()

    # Extract generated_at from markdown header
    gen_match = re.search(r'Generated at:\s*(.+)', content)
    generated_at = gen_match.group(1).strip() if gen_match else datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S %z')

    # Extract platform info
    plat_match = re.search(r'Platform:\s*(\w+)\s*\((.+)\)', content)
    platform = plat_match.group(1) if plat_match else 'unknown'
    uname = plat_match.group(2) if plat_match else 'unknown'

    # Parse markdown table
    tools = []
    in_table = False
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('| Tool |'):
            in_table = True
            continue
        if in_table and line.startswith('|---'):
            continue
        if in_table and line.startswith('| ') and '|' in line[2:]:
            # Split by pipe, strip each cell
            cells = [c.strip() for c in line.split('|')[1:-1]]  # Remove first and last empty
            if len(cells) >= 7:
                name, skill, purpose, available, path, version, hint = cells[0], cells[1], cells[2], cells[3], cells[4], cells[5], cells[6]
                tools.append({
                    'name': name,
                    'skill': skill,
                    'purpose': purpose,
                    'available': available.lower() == 'yes',
                    'path': None if path in ('—', '-', '') else path,
                    'version': None if version in ('—', '-', '') else version,
                    'install_hint': hint,
                })
        elif in_table and not line.startswith('|'):
            # End of table
            if line and not line.startswith('#'):
                break

    output = {
        'generated_at': generated_at,
        'platform': platform,
        'uname': uname,
        'script': 'skills/scripts/md-to-json.py',
        'tools': tools,
    }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ JSON written to {json_path} ({len(tools)} tools)")

if __name__ == '__main__':
    main()
