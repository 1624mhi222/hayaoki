#!/usr/bin/env python3
"""Obsidian の「- [ ] やること」を早起きアプリのスプレッドシートに送る。Claude からも使える。

  python3 hayaoki_obsidian.py sync [--dry]     Vault のタスクを送る(--dry は送らずに一覧だけ出す)
  python3 hayaoki_obsidian.py add "やること" [--due 2026-10-29]
  python3 hayaoki_obsidian.py list             今の TODO・日課・早起きの記録を JSON で出す

設定は ~/.hayaoki.json:
  {"url": "https://script.google.com/macros/s/…/exec", "key": "合言葉",
   "vault": "/Users/…/Desktop/Obsidian", "folders": []}
folders を空にすると Vault 全体、["00 Inbox"] のように書くとそのフォルダだけを見る。
"""
import json, os, re, sys, urllib.request

CONF = os.path.expanduser('~/.hayaoki.json')
TASK = re.compile(r'^\s*[-*+]\s+\[([ xX])\]\s+(.+?)\s*$')
DUE = re.compile(r'(?:📅\s*|due::?\s*)(\d{4}-\d{2}-\d{2})')
SKIP_DIRS = {'.obsidian', '.trash', '.git'}


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


def tasks(vault, folders):
    roots = [os.path.join(vault, f) for f in folders] if folders else [vault]
    for root in roots:
        for d, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith('.')]
            for name in files:
                if not name.endswith('.md'):
                    continue
                path = os.path.join(d, name)
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


def main(argv):
    cmd = argv[1] if len(argv) > 1 else 'sync'
    c = conf()
    if cmd == 'sync':
        items = list(tasks(os.path.expanduser(c['vault']), c.get('folders') or []))
        if '--dry' in argv:
            for it in items:
                print(('✓ ' if it['done'] else '・ ') + it['text'] + (f"（{it['due']}まで）" if it['due'] else '') + '   ← ' + it['src'].split('::')[0])
            print(f"\n{sum(not i['done'] for i in items)}件のやること、{sum(i['done'] for i in items)}件の終わったもの（送っていません）")
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
