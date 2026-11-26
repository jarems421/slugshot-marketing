import json, csv, statistics as st
rows = list(csv.DictReader(open('exports/share/research/tiktok-in-my-world-2026-11-26/ALL-POSTS.csv', encoding='utf-8-sig')))
pool = {r['id']: r for r in csv.DictReader(open('data/local/research/creative/tiktok-genre/pool.csv', encoding='utf-8'))}
for t in ('TOP', 'MID', 'FLOP'):
    wpm, top10 = [], []
    for r in rows:
        if r['tier'] != t: continue
        L = json.loads(pool[r['id']]['transcript'])
        if len(L) < 4: continue
        words = sum(len(x[1].split()) for x in L[:-1]); span = L[-1][0] - L[0][0]
        if span >= 10: wpm.append(words / span * 60)
        if r['tier'] == 'TOP' and int(r['views']) >= 2_000_000: top10.append(words / max(span, 1) * 60)
    q = st.quantiles(wpm, n=4)
    print(t, len(wpm), 'speech WPM median %.0f, middle half %.0f-%.0f, min %.0f max %.0f' % (st.median(wpm), q[0], q[2], min(wpm), max(wpm)))
    if top10: print('   TOP posts >=2M views:', len(top10), 'median %.0f' % st.median(top10))
