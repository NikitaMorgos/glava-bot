with open('/opt/glava/scripts/test_stage4_karakulina.py', 'rb') as f:
    raw = f.read()

old = b'"content": json.dumps(user_message, ensure_ascii=False),'
new = b'"content": _build_msg_content(user_message),'

count = raw.count(old)
print(f'Found {count} occurrences')

if count > 0:
    # Replace only the one inside the messages=[...] dict (not inside _build_msg_content)
    # The one we want is the one preceded by 'role": "user"' context
    target = b'"role": "user",\n                "content": json.dumps(user_message, ensure_ascii=False),'
    replacement = b'"role": "user",\n                "content": _build_msg_content(user_message),'
    if target in raw:
        raw = raw.replace(target, replacement, 1)
        with open('/opt/glava/scripts/test_stage4_karakulina.py', 'wb') as f:
            f.write(raw)
        print('Replaced via role context OK')
    else:
        # Find all occurrences of old and show context
        idx = 0
        while True:
            idx = raw.find(old, idx)
            if idx == -1:
                break
            ctx = raw[max(0, idx-60):idx+len(old)+20]
            print(f'  at {idx}:', repr(ctx))
            idx += 1
