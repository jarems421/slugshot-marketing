import json, glob, sys
sys.path.insert(0, r"C:\Users\runni\slugshot marketing\scripts")
import research_common as rc
it = json.load(open(glob.glob('data/local/research/creative/tiktok-genre/apify-top*/items.json')[0], encoding='utf-8'))
tok = rc.env_value('APIFY_TOKEN')
for x in it:
    u = (x.get('mediaUrls') or [None])[0]
    if not u: print('none', x.get('url') or x.get('webVideoUrl'), x.get('error')); continue
    b, _ = rc.http(u, headers={'Authorization': 'Bearer ' + tok}, timeout=120)
    open(f"media/research/tiktok-genre/top/{x['id']}.mp4", 'wb').write(b); print('ok', x['authorMeta']['name'])
