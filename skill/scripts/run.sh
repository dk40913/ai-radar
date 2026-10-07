#!/bin/bash
# launchd 進入點：無人值守執行 AI 知識雷達週報。
# 手動測試：~/.claude/skills/ai-radar/scripts/run.sh [since=YYYY-MM-DD]
set -uo pipefail

export HOME="${HOME:?}"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export LANG="en_US.UTF-8"
export LC_ALL="en_US.UTF-8"
[ -x /opt/homebrew/bin/brew ] && eval "$(/opt/homebrew/bin/brew shellenv)"

LOG="$HOME/Library/Logs/ai-radar.log"
LOCK="$HOME/.local/state/ai-radar/run.lock"
SKILL_DIR="$HOME/.claude/skills/ai-radar"
TODAY="$(date +%F)"
RUN_DIR="$HOME/.local/state/ai-radar/runs/$TODAY"
mkdir -p "$RUN_DIR" "$(dirname "$LOG")"

log() { printf '[%s] %s\n' "$(date '+%F %T')" "$*" >> "$LOG"; }

# 防止上一次還沒跑完又被觸發
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  log "another run is in progress (pid $(cat "$LOCK")), skip"
  exit 0
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

log "=== ai-radar start (args: $*) ==="

STATE="$HOME/.local/state/ai-radar/last_run.json"
STATE_BEFORE="$(cat "$STATE" 2>/dev/null || true)"

fail() {
  log "$1"
  printf '%s\n' "步驟：$2" "錯誤：$1" "log：$LOG" "run dir：$RUN_DIR" > "$RUN_DIR/failure.txt"
  "$SKILL_DIR/scripts/send_mail.sh" "AI知識雷達 執行失敗 $TODAY" "$RUN_DIR/failure.txt" >> "$LOG" 2>&1 || log "failure mail also failed"
}

# 從 config.json 讀 vault 與 model（install.sh 產生）
read_config() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get(sys.argv[2],""))' "$SKILL_DIR/config.json" "$1" 2>/dev/null; }
VAULT="$(read_config vault)"
MODEL="$(read_config model)"
if [ -z "$VAULT" ]; then
  fail "config.json 缺少 vault，請重跑 install.sh" "前置檢查"
  log "=== ai-radar end (code 1) ==="
  exit 1
fi

# build_html.py 只能靠 uv 跑（SKILL.md 禁止安裝套件），uv 不在 PATH 上就沒有退路，先擋下來
if ! command -v uv >/dev/null 2>&1; then
  fail "uv 不在 PATH 上（PATH=${PATH}），build_html.py 無法執行" "前置檢查"
  log "=== ai-radar end (code 1) ==="
  exit 1
fi
log "uv: $(command -v uv) $(uv --version 2>&1)"

# 額外參數（例如 since=2026-09-01）原樣傳給 skill
PROMPT="執行 /ai-radar 週報流程。$*"

# 權限靠 settings.json 的白名單，沒有人可以按同意，白名單外的動作會被拒絕而不是卡住
# --max-turns 是防失控的上限（正常一次遠低於此），不是預算
run_claude() {
  claude -p "$PROMPT" \
    ${MODEL:+--model "$MODEL"} \
    --max-turns 200 \
    --permission-mode acceptEdits \
    --settings "$SKILL_DIR/settings.json" \
    --add-dir "$VAULT" \
    --add-dir "$HOME/.local/state/ai-radar" \
    --output-format text \
    >> "$LOG" 2>&1
}

# 狀態檔只在寄信成功後才會被改寫，所以它沒前進就等於這次沒寄出信，
# 即使 claude 自己 exit 0 也算失敗
for ATTEMPT in 1 2; do
  rm -f "$RUN_DIR/failure.txt"
  run_claude
  CODE=$?
  STATE_AFTER="$(cat "$STATE" 2>/dev/null || true)"
  # 狀態前進代表信已寄出，就算 exit code 非 0 也不能重跑（會重寄）
  if [ "$STATE_AFTER" != "$STATE_BEFORE" ]; then
    break
  fi
  log "attempt $ATTEMPT failed (claude exit $CODE, state not advanced)"
  # 第一次失敗多半是 API 中斷或額度，等一小時再整個重跑一次；skill 內部失敗時可能已先寄過一封失敗通知
  if [ $ATTEMPT -eq 1 ]; then
    log "retry in 60 minutes"
    sleep 3600
  fi
done

if [ $CODE -ne 0 ]; then
  [ -f "$RUN_DIR/failure.txt" ] || fail "exit code $CODE（已重試一次）" "claude -p 執行"
elif [ "$STATE_AFTER" = "$STATE_BEFORE" ]; then
  CODE=1
  [ -f "$RUN_DIR/failure.txt" ] || fail "claude 正常結束但 last_run.json 沒有更新，代表信沒有寄出（已重試一次）" "寄信／寫狀態"
fi

log "=== ai-radar end (code $CODE) ==="
exit $CODE
