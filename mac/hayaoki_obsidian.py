#!/usr/bin/env python3
"""Obsidian の「- [ ] やること」を早起きアプリのスプレッドシートに送る。Claude からも使える。

  python3 hayaoki_obsidian.py sync [--dry]     Vault のタスクを送る(--dry は送らずに一覧だけ出す)
  python3 hayaoki_obsidian.py add "やること" [--due 2026-10-29]
  python3 hayaoki_obsidian.py list             今の TODO・日課・早起きの記録を JSON で出す

設定は ~/.hayaoki.json:
  {"url": "https://script.google.com/macros/s/…/exec", "key": "合言葉",
   "vault": "/Users/…/Desktop/Obsidian", "folders": []}
folders を空にすると Vault 全体、["00 Inbox"] のように書くとそのフォルダだけ、["00 Inbox/hayaoki TODO.md"] ならそのノートだけを見る。
folders の外でも、最近(suggest_days 日以内に)書いたノートの「TODOっぽい行」はアプリに「提案」として送る。
アプリで「追加」を押すと TODO になり、✕ を押すと二度と提案しない。suggest_days を 0 にすると提案しない。
"""
import json, os, re, sys, urllib.request

CONF = os.path.expanduser('~/.hayaoki.json')
TASK = re.compile(r'^\s*[-*+]\s+\[([ xX])\]\s+(.+?)\s*$')
DUE = re.compile(r'(?:📅\s*|due::?\s*)(\d{4}-\d{2}-\d{2})')
SKIP_DIRS = {'.obsidian', '.trash', '.git'}
# TODOっぽい言い方。- [ ] のチェックボックスも提案に入れる
LIKE = re.compile(r'TODO|やる|やらな|しなきゃ|しないと|忘れずに|忘れない|締め?切|しめきり|〆切|提出|までに|連絡する|予約|申し?込|買う|払う|返す|返信')
SUGGEST_SKIP = ('99 Templates', 'wiki', 'log.md', 'index.md')
SUGGEST_MAX = 15


def conf():
    with open(CONF, encoding='utf-8') as f:
        return json.load(f)


def call(c, fn, args):
    body = json.dumps({'key': c['key'], 'fn': fn, 'args': args}).encode('utf-8')
    req = urllib.request.Request(c['url'], data=body, headers={'Content-Type': 'text/plain;charset=utf-8'})
    with urllib.request.urlopen(req, timeout=60) as r:   # Apps Script は別のURLに転送して結果を返す。urllib が追いかける
        out = json.loads(r.read().decode('utf-8'))
    if not out.get('ok'):
        raise SystemExit('エラー: ' + str(out.get('error')))
    return out['result']


def files(vault, folders):
    for root in ([os.path.join(vault, f) for f in folders] if folders else [vault]):
        if os.path.isfile(root):          # ノートを1つだけ指定したとき
            yield root
            continue
        for d, dirs, names in os.walk(root):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith('.')]
            yield from (os.path.join(d, n) for n in names if n.endswith('.md'))


def tasks(vault, folders):
    for path in files(vault, folders):
        rel = os.path.relpath(path, vault)
        try:
            lines = open(path, encoding='utf-8').read().splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line in lines:
            m = TASK.match(line)
            if not m:
                continue
            text = m.group(2)
            due = DUE.search(text)
            clean = DUE.sub('', text).strip()
            if not clean:
                continue
            yield {'text': clean, 'due': due.group(1) if due else '', 'src': rel + '::' + clean, 'done': m.group(1) != ' '}


def suggestions(vault, exclude, days, skip):
    """最近さわったノートから、TODOっぽい行を拾う。新しいノートの順に最大 SUGGEST_MAX 件"""
    import time
    since = time.time() - days * 86400
    picked = []
    for path in files(vault, []):
        rel = os.path.relpath(path, vault)
        if os.path.abspath(path) in exclude or rel.split(os.sep)[0] in skip:
            continue
        try:
            mtime = os.path.getmtime(path)
            if mtime < since:
                continue
            lines = open(path, encoding='utf-8').read().splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        fence = front = False
        for i, line in enumerate(lines):
            if i == 0 and line.strip() == '---':
                front = True
                continue
            if front:
                front = line.strip() != '---'
                continue
            if line.lstrip().startswith('```'):
                fence = not fence
            if fence or line.lstrip().startswith(('#', '>', '|', '![')):
                continue
            m = TASK.match(line)
            if m:
                if m.group(1) != ' ':
                    continue
                text = m.group(2)
            else:
                text = re.sub(r'^\s*(?:[-*+・•]|\d+[.)])\s*', '', line).strip()
                if not LIKE.search(text):
                    continue
            due = DUE.search(text)
            clean = re.sub(r'\[\[([^\]|]*\|)?([^\]]*)\]\]', r'\2', DUE.sub('', text)).strip()
            if not (3 <= len(clean) <= 60):
                continue
            picked.append((mtime, {'text': clean, 'due': due.group(1) if due else '', 'src': '提案:' + rel + '::' + clean, 'done': False}))
    picked.sort(key=lambda x: -x[0])
    return [p for _, p in picked[:SUGGEST_MAX]]


def main(argv):
    cmd = argv[1] if len(argv) > 1 else 'sync'
    c = conf()
    if cmd == 'sync':
        vault = os.path.expanduser(c['vault'])
        folders = c.get('folders') or []
        items = list(tasks(vault, folders))
        days = c.get('suggest_days', 3)
        if days and folders:
            exclude = {os.path.abspath(p) for p in files(vault, folders)}
            have = {i['text'] for i in items}
            items += [x for x in suggestions(vault, exclude, days, c.get('suggest_skip', SUGGEST_SKIP)) if x['text'] not in have]
        if '--dry' in argv:
            for it in items:
                print(('💡 ' if it['src'].startswith('提案:') else '✓ ' if it['done'] else '・ ') + it['text'] + (f"（{it['due']}まで）" if it['due'] else '') + '   ← ' + it['src'].split('::')[0])
            sug = sum(i['src'].startswith('提案:') for i in items)
            print(f"\n{sum(not i['done'] for i in items) - sug}件のやること、{sum(i['done'] for i in items)}件の終わったもの、{sug}件の提案（送っていません）")
            return
        r = call(c, 'add', [items])
        print(f"送りました: 新しく{r['added']}件、完了にしたもの{r['done']}件")
    elif cmd == 'add':
        if len(argv) < 3:
            raise SystemExit('使い方: add "やること" [--due YYYY-MM-DD]')
        due = argv[argv.index('--due') + 1] if '--due' in argv else ''
        r = call(c, 'add', [[{'text': argv[2], 'due': due}]])
        print(f"足しました（{r['added']}件）")
    elif cmd == 'list':
        print(json.dumps(call(c, 'list', []), ensure_ascii=False, indent=2))
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main(sys.argv)
