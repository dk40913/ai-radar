#!/bin/bash
# 用 Mail.app 寄純文字信。
# 用法: send_mail.sh "<主旨>" <內文檔案路徑> [收件者] [附件路徑]
set -euo pipefail

SUBJECT="${1:?subject required}"
BODY_FILE="${2:?body file required}"
CONFIG="$(dirname "$0")/../config.json"
CFG_TO="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("mail_to",""))' "$CONFIG" 2>/dev/null || true)"
TO="${3:-$CFG_TO}"
ATTACH="${4:-}"

if [ -z "$TO" ]; then
  echo "mail disabled (config mail_to empty): $SUBJECT"
  exit 0
fi

[ -f "$BODY_FILE" ] || { echo "body file not found: $BODY_FILE" >&2; exit 1; }
if [ -n "$ATTACH" ] && [ ! -f "$ATTACH" ]; then echo "attachment not found: $ATTACH" >&2; exit 1; fi

# 內文從檔案讀進 AppleScript，避免引號跳脫問題
osascript - "$SUBJECT" "$BODY_FILE" "$TO" "$ATTACH" <<'EOF'
on run argv
  set theSubject to item 1 of argv
  set bodyPath to item 2 of argv
  set theTo to item 3 of argv
  set attachPath to item 4 of argv
  set theBody to read POSIX file bodyPath as «class utf8»
  tell application "Mail"
    set m to make new outgoing message with properties {subject:theSubject, content:theBody, visible:false}
    tell m
      make new to recipient at end of to recipients with properties {address:theTo}
      if attachPath is not "" then
        make new attachment with properties {file name:(POSIX file attachPath)} at after the last paragraph
      end if
    end tell
    if attachPath is not "" then delay 3 -- 附件載入需要一點時間，太快 send 會掉附件
    send m
  end tell
end run
EOF
echo "sent: $SUBJECT -> $TO${ATTACH:+ (+attachment)}"
