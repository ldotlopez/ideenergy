import json
import re

def process_dump():
    dump_file = '/config/.openclaw/workspace/globalomnium/dump todas las vocales.txt'
    existing_json_path = '/config/.openclaw/workspace/globalomnium/localities_dump.json'
    base_urls_json_path = '/config/.openclaw/workspace/globalomnium/base_urls.json'

    # 1. Load existing data
    try:
        with open(existing_json_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            if isinstance(existing_data, list):
                localities = {item['id']: item for item in existing_data}
            elif isinstance(existing_data, dict) and 'items' in existing_data:
                localities = {item['id']: item for item in existing_data['items']}
            else:
                localities = {}
    except (FileNotFoundError, json.JSONDecodeError):
        localities = {}

    # 2. Parse the dump file
    # The dump file contains URLs followed by JSON strings
    with open(dump_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by the known URL pattern to isolate the JSON blocks
    # Pattern: https://www.globalomnium.com/Direcciones/DameMunicipiosWebs?filtro=...
    blocks = re.split(r'https://www\.globalomnium\.com/Direcciones/DameMunicipiosWebs\?filtro=[a-zA-Z]', content)
    
    # The first block is likely empty if the file starts with a URL
    for block in blocks[1:]:
        # Try to find the start of the JSON array/object in the block
        # The block starts after the 'filtro=X' part, so we need to skip that character
        # and find the first '{'
        start_idx = block.find('{')
        if start_idx == -1:
            continue
        
        # We need to find the matching closing brace for the JSON object
        # Since blocks can contain multiple JSON objects or be fragmented, 
        # we'll try to extract the {"items": [...]} part.
        # Let's find the last '}' in the block
        end_idx = block.rfind('}')
        if end_idx == -1:
            continue
            
        json_str = block[start_idx:end_idx+1]
        
        # In the dump, sometimes the first block is actually missing the opening '{' 
        # because the regex split removed it or the file is messy.
        # Let's check if it starts with 'items' and wrap it.
        if json_str.startswith('"items"'):
            json_str = '{' + json_str + '}'

        try:
            data = json.loads(json_str)
            items = data.get('items', []) if isinstance(data, dict) else []
            for item in items:
                # Unify by ID, removing duplicates
                localities[item['id']] = item
        except json.JSONDecodeError:
            # Sometimes blocks are fragmented. Try to find the actual JSON items array.
            # Search for [ { ... }, { ... } ]
            match = re.search(r'\[\s*\{.*\}\s*\]', json_str, re.DOTALL)
            if match:
                try:
                    items = json.loads(match.group(0))
                    for item in items:
                        localities[item['id']] = item
                except json.JSONDecodeError:
                    pass

    # 3. Save unified localities
    final_localities_list = list(localities.values())
    with open(existing_json_path, 'w', encoding='utf-8') as f:
        json.dump({"items": final_localities_list}, f, ensure_ascii=False, indent=2)

    # 4. Generate base URLs list
    base_urls = set()
    for item in final_localities_list:
        url = item.get('url', '')
        if url:
            # Extract base URL (everything before /VirtualOffice)
            base = url.split('/VirtualOffice')[0]
            if base:
                base_urls.add(base)

    with open(base_urls_json_path, 'w', encoding='utf-8') as f:
        json.dump(sorted(list(base_urls)), f, ensure_ascii=False, indent=2)

    print(f"Total localities: {len(final_localities_list)}")
    print(f"Total unique base URLs: {len(base_urls)}")

if __name__ == '__main__':
    process_dump()
