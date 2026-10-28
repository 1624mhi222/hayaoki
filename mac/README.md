# Obsidian → 早起きアプリ

Obsidian の `- [ ] やること` を、15分ごとに早起きアプリのスプレッドシートへ送ります。

- `📅 2026-10-29` か `due: 2026-10-29` が付いていれば期限になります（Tasks プラグインの書き方そのまま）。
- 同じノートの同じ文のタスクは二度送りません。Obsidian で `[x]` にすると、アプリでも完了になります。
- アプリで消したものは、Obsidian に残っていても戻ってきません。

## 入れ方

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
