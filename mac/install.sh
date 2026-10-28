#!/bin/bash
# Obsidian → 早起きアプリの連携を、この Mac に入れる(何度実行しても大丈夫)
#   curl -fsSL https://raw.githubusercontent.com/1624mhi222/hayaoki/main/mac/install.sh | bash
set -euo pipefail
RAW=https://raw.githubusercontent.com/1624mhi222/hayaoki/main/mac
DIR="$HOME/hayaoki"
CONF="$HOME/.hayaoki.json"
NOTE_REL="00 Inbox/hayaoki TODO.md"
PLIST="$HOME/Library/LaunchAgents/com.hayaoki.obsidian.plist"

mkdir -p "$DIR" "$HOME/Library/LaunchAgents"
curl -fsSL "$RAW/hayaoki_obsidian.py" -o "$DIR/hayaoki_obsidian.py"
curl -fsSL "$RAW/com.hayaoki.obsidian.plist" -o "$DIR/com.hayaoki.obsidian.plist"

# 設定: URL と合言葉はすでにあればそのまま。送るのは専用ノートだけにし、ほかの最近のノートからは提案する
if [ ! -f "$CONF" ]; then
  read -r -p "Apps Script の URL: " URL </dev/tty
  read -r -p "合言葉: " KEY </dev/tty
  python3 - "$CONF" "$URL" "$KEY" <<'PY'
import json, os, sys
json.dump({'url': sys.argv[2], 'key': sys.argv[3], 'vault': os.path.expanduser('~/Desktop/Obsidian')}, open(sys.argv[1], 'w'), ensure_ascii=False)
PY
fi
python3 - "$CONF" "$NOTE_REL" <<'PY'
import json, sys
p, note = sys.argv[1], sys.argv[2]
c = json.load(open(p, encoding='utf-8'))
c['folders'] = [note]
c.setdefault('suggest_days', 3)
json.dump(c, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Vault:', c['vault'])
PY
chmod 600 "$CONF"

VAULT=$(python3 -c "import json,os;print(os.path.expanduser(json.load(open('$CONF'))['vault']))")
NOTE="$VAULT/$NOTE_REL"
if [ ! -f "$NOTE" ]; then
  mkdir -p "$(dirname "$NOTE")"
  cat > "$NOTE" <<'MD'
# hayaoki TODO

ここに `- [ ]` で書いたものが、15分ごとに早起きアプリのTODOに入ります。
期限は `📅 2026-10-29` のように書きます。`[x]` にするとアプリでも完了になります。

- [ ] 
MD
  echo "ノートを作りました: $NOTE_REL"
fi

echo; echo "--- 送るもの・提案するもの ---"
python3 "$DIR/hayaoki_obsidian.py" sync --dry
python3 "$DIR/hayaoki_obsidian.py" sync

sed "s|SCRIPT_PATH|$DIR/hayaoki_obsidian.py|" "$DIR/com.hayaoki.obsidian.plist" > "$PLIST"
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo; echo "完了: 15分ごとに自動で送ります（ログ: /tmp/hayaoki-obsidian.log）"
