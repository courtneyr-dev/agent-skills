#!/usr/bin/env bash
# Install these skills for any SKILL.md-compatible agent.
#
# This repository is the canonical source for the 34 skills under skills/. Installing links an
# agent's skill directory at them. Nothing here is destructive: an existing real directory, a
# customized copy, or a link pointing somewhere else is reported, never overwritten.
#
#   ./install.sh --dry-run                # default. Classify every destination, change nothing.
#   ./install.sh --apply                  # create only the missing links
#   ./install.sh --apply -a claude -a codex
#   ./install.sh --via-mount              # route through $AGENT_SKILLS_DIR (aggregation topology)
#   ./install.sh --list                   # list the installable skills
#   ./install.sh --external               # upstream install commands for third-party skills
#
# `install` only fills in what is missing. Converting an existing copy, or repointing a link that
# already goes somewhere else, is a migration: this script will tell you what it found and leave
# the decision to you.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOUNT="${AGENT_SKILLS_DIR:-$HOME/.agents/skills}"
APPLY=0
VIA_MOUNT=0
LIST=0
EXTERNAL=0
AGENTS=()

while [ $# -gt 0 ]; do
  case "$1" in
    -a|--agent)  AGENTS+=("$2"); shift 2 ;;
    --apply)     APPLY=1; shift ;;
    --dry-run)   APPLY=0; shift ;;
    --via-mount) VIA_MOUNT=1; shift ;;
    --list)      LIST=1; shift ;;
    --external)  EXTERNAL=1; shift ;;
    -h|--help)   sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

agent_dir() {
  case "$1" in
    claude|claude-code) echo "$HOME/.claude/skills" ;;
    cursor)             echo "$HOME/.cursor/skills" ;;
    codex)              echo "$HOME/.codex/skills" ;;
    openclaw)           echo "$HOME/.openclaw/skills" ;;
    gemini|gemini-cli)  echo "$HOME/.gemini/skills" ;;
    *) return 1 ;;
  esac
}

SKILLS=()
while IFS= read -r s; do SKILLS+=("$s"); done < <(ls -1 "$HERE/skills" | sort)

if [ "$LIST" = 1 ]; then printf '%s\n' "${SKILLS[@]}"; exit 0; fi
if [ "$EXTERNAL" = 1 ]; then
  echo "Third-party skills are owned by their upstreams and are not installed from here."
  echo "See manifest.json (kind: external) for each source repository."
  exit 0
fi

if [ ${#AGENTS[@]} -eq 0 ]; then
  for a in claude cursor codex openclaw gemini; do
    [ -d "$(agent_dir "$a")" ] && AGENTS+=("$a")
  done
fi
[ ${#AGENTS[@]} -eq 0 ] && { echo "no agent skill directories found; pass -a <agent>" >&2; exit 1; }

# classify <dest> <wanted-target> -> STATE
classify() {
  local dest="$1" want="$2"
  if [ -L "$dest" ]; then
    local cur; cur="$(readlink "$dest")"
    [ ! -e "$dest" ] && { echo "DANGLING"; return; }
    [ "$cur" = "$want" ] && { echo "CORRECT"; return; }
    echo "OTHER_LINK"; return
  fi
  if [ -d "$dest" ]; then
    if [ -f "$dest/SKILL.md" ] && [ -f "$want/SKILL.md" ] \
       && cmp -s "$dest/SKILL.md" "$want/SKILL.md"; then
      echo "SAME_COPY"; return
    fi
    echo "LOCAL_COPY"; return
  fi
  [ -e "$dest" ] && { echo "UNKNOWN"; return; }
  echo "MISSING"
}

created=0; skipped=0; conflicts=0
report() { printf '  %-9s %-34s %s\n' "$1" "$2" "$3"; }

link_one() {  # <dest> <target> <label>
  local dest="$1" want="$2" label="$3" state
  state="$(classify "$dest" "$want")"
  case "$state" in
    MISSING)
      report "LINK" "$label" "-> $want"
      if [ "$APPLY" = 1 ]; then mkdir -p "$(dirname "$dest")"; ln -s "$want" "$dest"; fi
      created=$((created + 1)) ;;
    CORRECT)    report "SKIP" "$label" "already correct"; skipped=$((skipped + 1)) ;;
    SAME_COPY)  report "SKIP" "$label" "identical real copy — migration, not install"; skipped=$((skipped + 1)) ;;
    LOCAL_COPY) report "CONFLICT" "$label" "local copy differs — not overwriting"; conflicts=$((conflicts + 1)) ;;
    OTHER_LINK) report "CONFLICT" "$label" "links elsewhere: $(readlink "$dest")"; conflicts=$((conflicts + 1)) ;;
    DANGLING)   report "CONFLICT" "$label" "dangling link -> $(readlink "$dest")"; conflicts=$((conflicts + 1)) ;;
    UNKNOWN)    report "CONFLICT" "$label" "unrecognized file at destination"; conflicts=$((conflicts + 1)) ;;
  esac
}

[ "$APPLY" = 1 ] || echo "DRY RUN — nothing will be written. Re-run with --apply to create links."
echo

if [ "$VIA_MOUNT" = 1 ]; then
  echo "mount: $MOUNT"
  for s in "${SKILLS[@]}"; do link_one "$MOUNT/$s" "$HERE/skills/$s" "mount/$s"; done
  echo
fi

for a in "${AGENTS[@]}"; do
  d="$(agent_dir "$a")" || { echo "unknown agent: $a" >&2; continue; }
  echo "$a: $d"
  for s in "${SKILLS[@]}"; do
    if [ "$VIA_MOUNT" = 1 ]; then link_one "$d/$s" "$MOUNT/$s" "$a/$s"
    else                          link_one "$d/$s" "$HERE/skills/$s" "$a/$s"; fi
  done
  echo
done

echo "links created: $created   skipped: $skipped   conflicts: $conflicts"
if [ "$conflicts" -gt 0 ]; then
  echo
  echo "Conflicts are left alone. Each one is an existing skill this installer did not put there;"
  echo "converting it is a migration you should make deliberately."
fi
[ "$APPLY" = 1 ] && echo && echo "Restart your agent to pick up new skills."
exit 0
