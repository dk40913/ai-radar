#!/bin/bash
# Install the ai-radar skill into ~/.claude/skills/ai-radar and schedule it with launchd.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_NAME="${USER:-$(id -un)}"

VAULT=""; PARALLEL=""; MAIL_TO=""; MODEL=""; SUBAGENT_MODEL="opus"
NO_LAUNCHD=0; SKIP_CHECKS=0

die() { echo "error: $*" >&2; exit 1; }
usage() {
  echo "usage: install.sh --vault PATH --parallel yes|no [--mail-to EMAIL] [--model ID]" >&2
  echo "                  [--subagent-model opus|sonnet|haiku] [--no-launchd] [--skip-checks]" >&2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --vault) [ $# -ge 2 ] || die "--vault needs a value"; VAULT="$2"; shift 2 ;;
    --parallel) [ $# -ge 2 ] || die "--parallel needs a value"; PARALLEL="$2"; shift 2 ;;
    --mail-to) [ $# -ge 2 ] || die "--mail-to needs a value"; MAIL_TO="$2"; shift 2 ;;
    --model) [ $# -ge 2 ] || die "--model needs a value"; MODEL="$2"; shift 2 ;;
    --subagent-model) [ $# -ge 2 ] || die "--subagent-model needs a value"; SUBAGENT_MODEL="$2"; shift 2 ;;
    --no-launchd) NO_LAUNCHD=1; shift ;;
    --skip-checks) SKIP_CHECKS=1; shift ;;
    *) usage; die "unknown argument: $1" ;;
  esac
done

[ -n "$VAULT" ] || { usage; die "--vault is required"; }
case "$PARALLEL" in
  yes|no) ;;
  *) usage; die "--parallel must be yes or no" ;;
esac
case "$SUBAGENT_MODEL" in
  opus|sonnet|haiku) ;;
  *) die "--subagent-model must be opus, sonnet or haiku" ;;
esac

VAULT="${VAULT/#\~/$HOME}"
[ -d "$VAULT" ] || die "vault directory does not exist: $VAULT"
VAULT="$(cd "$VAULT" && pwd)"

if [ "$SKIP_CHECKS" -eq 0 ]; then
  missing=()
  command -v claude >/dev/null || missing+=("claude     -> https://docs.claude.com/en/docs/claude-code/setup")
  command -v python3 >/dev/null || missing+=("python3    -> brew install python")
  command -v uv >/dev/null || missing+=("uv         -> brew install uv")
  command -v defuddle >/dev/null || missing+=("defuddle   -> npm install -g defuddle")
  command -v osascript >/dev/null || missing+=("osascript  -> macOS only (ships with the OS)")
  if [ ${#missing[@]} -gt 0 ]; then
    echo "Missing dependencies:" >&2
    printf '  %s\n' "${missing[@]}" >&2
    exit 1
  fi
fi

DEST="$HOME/.claude/skills/ai-radar"
mkdir -p "$DEST"
rsync -a --exclude='__pycache__' --exclude='/config.json' --exclude='/harness_profile.md' \
  --exclude='/settings.template.json' "$REPO/skill/" "$DEST/"

# launchd starts run.sh with a bare PATH; record where this shell found the tools so run.sh can find them too.
TOOL_DIRS=""
for tool in claude defuddle uv python3; do
  if tool_path="$(command -v "$tool")"; then
    TOOL_DIRS="$TOOL_DIRS$(dirname "$tool_path")"$'\n'
  fi
done

AIR_PARALLEL="$PARALLEL" AIR_VAULT="$VAULT" AIR_MAIL_TO="$MAIL_TO" AIR_MODEL="$MODEL" \
AIR_SUBAGENT="$SUBAGENT_MODEL" AIR_TOOL_DIRS="$TOOL_DIRS" python3 - "$DEST/config.json" <<'PY'
import json, os, sys
dirs = list(dict.fromkeys(d for d in os.environ["AIR_TOOL_DIRS"].splitlines() if d))
cfg = {"parallel": os.environ["AIR_PARALLEL"] == "yes", "vault": os.environ["AIR_VAULT"],
       "mail_to": os.environ["AIR_MAIL_TO"], "model": os.environ["AIR_MODEL"],
       "subagent_model": os.environ["AIR_SUBAGENT"], "path_prepend": dirs}
with open(sys.argv[1], "w") as f:
    json.dump(cfg, f, ensure_ascii=False)
PY

if [ ! -e "$DEST/harness_profile.md" ] && [ -f "$REPO/skill/harness_profile.example.md" ]; then
  cp "$REPO/skill/harness_profile.example.md" "$DEST/harness_profile.md"
fi

# Claude Code permission paths: ~/rel inside $HOME, //abs outside.
case "$VAULT" in
  "$HOME") VAULT_RULE="~" ;;
  "$HOME"/*) VAULT_RULE="~/${VAULT#"$HOME"/}" ;;
  *) VAULT_RULE="/$VAULT" ;;
esac

# render TEMPLATE OUT json|xml — values are escaped for the output format.
render() {
  AIR_HOME="$HOME" AIR_VAULT_RULE="$VAULT_RULE" AIR_USER="$USER_NAME" python3 -c '
import json, os, sys
from xml.sax.saxutils import escape
quote = {"json": lambda v: json.dumps(v, ensure_ascii=False)[1:-1], "xml": escape}[sys.argv[3]]
t = open(sys.argv[1], encoding="utf-8").read()
for k, v in (("__HOME__", "AIR_HOME"), ("__VAULT_RULE__", "AIR_VAULT_RULE"), ("__USER__", "AIR_USER")):
    t = t.replace(k, quote(os.environ[v]))
open(sys.argv[2], "w", encoding="utf-8").write(t)
' "$1" "$2" "$3"
}

render "$REPO/skill/settings.template.json" "$DEST/settings.json" json

mkdir -p "$VAULT/AI知識雷達/attachments"
if [ ! -e "$VAULT/AI知識雷達/CLAUDE.md" ]; then
  cp "$REPO/vault-template/AI知識雷達/CLAUDE.md" "$VAULT/AI知識雷達/CLAUDE.md"
fi

LABEL="com.$USER_NAME.ai-radar"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
render "$REPO/launchd/ai-radar.plist.template" "$PLIST" xml
if [ "$NO_LAUNCHD" -eq 0 ]; then
  DOMAIN="gui/$(id -u)"
  launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
  # bootout returns before the old job is gone; bootstrapping while it still exists fails.
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1 || break
    sleep 0.5
  done
  if ! launchctl bootstrap "$DOMAIN" "$PLIST"; then
    sleep 2
    launchctl bootstrap "$DOMAIN" "$PLIST" \
      || die "launchctl bootstrap failed for $PLIST; run install.sh again, or log out and back in and retry"
  fi
fi

mkdir -p "$HOME/.local/state/ai-radar"

echo "ai-radar installed"
echo "  skill:     $DEST"
echo "  vault:     $VAULT"
echo "  mail:      ${MAIL_TO:-(disabled)}"
echo "  parallel:  $PARALLEL"
echo "  model:     ${MODEL:-(default)}  subagent: $SUBAGENT_MODEL"
if [ "$NO_LAUNCHD" -eq 0 ]; then echo "  schedule:  Saturday 09:00 ($LABEL)"; else echo "  schedule:  not loaded (--no-launchd)"; fi
