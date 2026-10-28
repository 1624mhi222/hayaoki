# Obsidian → 早起きアプリ

Obsidian の `- [ ] やること` を、15分ごとに早起きアプリのスプレッドシートへ送ります。
ほかのノートでも、最近（3日以内に）書いた「TODOっぽい行」（`- [ ]`、「〜までに」「提出」「連絡する」など）は、アプリに💡提案として出ます。アプリで「追加」を押すとTODOになり、✕を押すと二度と出ません。

いちばんかんたんな入れ方（ターミナルに貼る）:

```
curl -fsSL https://raw.githubusercontent.com/1624mhi222/hayaoki/main/mac/install.sh | bash
```

送るのは `00 Inbox/hayaoki TODO.md` だけです（なければ作ります）。

- `📅 2026-10-29` か `due: 2026-10-29` が付いていれば期限になります（Tasks プラグインの書き方そのまま）。
- 同じノートの同じ文のタスクは二度送りません。Obsidian で `[x]` にすると、アプリでも完了になります。
- アプリで消したものは、Obsidian に残っていても戻ってきません。

## 手で入れるとき

1. `hayaoki_obsidian.py` を `~/hayaoki/` に置く。
2. `~/.hayaoki.json` を作る:
   ```json
   {"url": "https://script.google.com/macros/s/…/exec", "key": "合言葉", "vault": "~/Desktop/Obsidian", "folders": []}
   ```
   `folders` が空なら Vault 全体、`["00 Inbox"]` のように書くとそのフォルダだけ。
3. `python3 ~/hayaoki/hayaoki_obsidian.py sync --dry` で、送られるものを確かめる。
4. `com.hayaoki.obsidian.plist` の `SCRIPT_PATH` を置き換えて `~/Library/LaunchAgents/` に置き、
   `launchctl load ~/Library/LaunchAgents/com.hayaoki.obsidian.plist`。

## Claude から使う

```
python3 ~/hayaoki/hayaoki_obsidian.py add "レポートを出す" --due 2026-10-30
python3 ~/hayaoki/hayaoki_obsidian.py list
```
