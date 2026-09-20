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
#   ./install.sh --grades                 # show each agent's runtime support grade
#   ./install.sh --apply --include-unverified   # also write for agents below L3
#
# Support grades come from manifest.json and describe RUNTIME evidence, not whether a path exists.
# L3 agents are runtime-proven and are written by --apply. Agents below L3 are reported as PLAN and
# are skipped unless you pass --include-unverified: their paths are right, but nothing here proves
# the agent loads what gets written there.
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
GRADES=0
INCLUDE_UNVERIFIED=0
AGENTS=()

while [ $# -gt 0 ]; do
  case "$1" in
    -a|--agent)  AGENTS+=("$2"); shift 2 ;;
    --apply)     APPLY=1; shift ;;
    --dry-run)   APPLY=0; shift ;;
    --via-mount) VIA_MOUNT=1; shift ;;
    --list)      LIST=1; shift ;;
    --external)  EXTERNAL=1; shift ;;
    --grades)    GRADES=1; shift ;;
    --include-unverified) INCLUDE_UNVERIFIED=1; shift ;;
    -h|--help)   sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
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

# Support grades live in manifest.json so they are declared once. If python3 is unavailable the
# installer still works; it just cannot annotate grades, and says so rather than guessing.
GRADE_TABLE=""
if command -v python3 >/dev/null 2>&1; then
  GRADE_TABLE="$(python3 - "$HERE/manifest.json" <<'PYEOF'
import json, sys
roots = json.load(open(sys.argv[1]))["skill_roots"]
for a, v in roots.items():
    if isinstance(v, dict) and "grade" in v:
        print(f"{a}\t{v['grade']}")
PYEOF
)" || GRADE_TABLE=""
fi

agent_grade() {  # <agent> -> L3|L2|L1|L0|UNKNOWN
  local a="$1" g
  case "$a" in claude-code) a=claude ;; gemini-cli) a=gemini ;; esac
  [ -z "$GRADE_TABLE" ] && { echo "UNKNOWN"; return; }
  g="$(printf '%s\n' "$GRADE_TABLE" | awk -F'\t' -v a="$a" '$1==a{print $2}')"
  echo "${g:-L0}"
}

grade_label() {  # <grade> -> short honest phrase
  case "$1" in
    L3) echo "L3 runtime-proven" ;;
    L2) echo "L2 runtime-unverified" ;;
    L1) echo "L1 topology-observed" ;;
    L0) echo "L0 unverified" ;;
    *)  echo "grade unknown" ;;
  esac
}

SKILLS=()
while IFS= read -r s; do SKILLS+=("$s"); done < <(ls -1 "$HERE/skills" | sort)

if [ "$GRADES" = 1 ]; then
  if [ -z "$GRADE_TABLE" ]; then
    echo "python3 not available — cannot read support grades from manifest.json" >&2; exit 1
  fi
  echo "Runtime support grades (manifest.json). A grade describes runtime evidence, not path validity."
  echo
  for a in claude codex cursor openclaw gemini; do
    printf '  %-10s %s\n' "$a" "$(grade_label "$(agent_grade "$a")")"
  done
  echo
  echo "Only L3 agents are written by --apply. Use --include-unverified to write for the rest."
  exit 0
fi

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

created=0; planned=0; skipped=0; conflicts=0
report() { printf '  %-9s %-34s %s\n' "$1" "$2" "$3"; }

link_one() {  # <dest> <target> <label> [grade]
  local dest="$1" want="$2" label="$3" grade="${4:-MOUNT}" state suffix
  state="$(classify "$dest" "$want")"
  if [ "$grade" = "MOUNT" ]; then suffix=""; else suffix="  [$(grade_label "$grade")]"; fi
  case "$state" in
    MISSING)
      if [ "$grade" = "MOUNT" ] || [ "$grade" = "L3" ]; then
        report "LINK" "$label" "-> $want$suffix"
        if [ "$APPLY" = 1 ]; then mkdir -p "$(dirname "$dest")"; ln -s "$want" "$dest"; fi
        created=$((created + 1))
      elif [ "$APPLY" = 1 ] && [ "$INCLUDE_UNVERIFIED" = 1 ]; then
        report "LINK" "$label" "-> $want$suffix (opted in)"
        mkdir -p "$(dirname "$dest")"; ln -s "$want" "$dest"
        created=$((created + 1))
      else
        report "PLAN" "$label" "-> $want$suffix"
        planned=$((planned + 1))
      fi ;;
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
  g="$(agent_grade "$a")"
  echo "$a: $d  [$(grade_label "$g")]"
  for s in "${SKILLS[@]}"; do
    if [ "$VIA_MOUNT" = 1 ]; then link_one "$d/$s" "$MOUNT/$s" "$a/$s" "$g"
    else                          link_one "$d/$s" "$HERE/skills/$s" "$a/$s" "$g"; fi
  done
  echo
done

if [ "$APPLY" = 1 ]; then verb="links created"; else verb="links to create"; fi
echo "$verb: $created   planned: $planned   skipped: $skipped   conflicts: $conflicts"
if [ "$planned" -gt 0 ]; then
  echo
  echo "PLAN entries are for agents below L3: the path is right, but no runtime probe here proves"
  echo "the agent loads what would be written. They are filesystem-compatible and available, not"
  echo "verified. Pass --include-unverified with --apply to write them anyway."
fi
if [ "$conflicts" -gt 0 ]; then
  echo
  echo "Conflicts are left alone. Each one is an existing skill this installer did not put there;"
  echo "converting it is a migration you should make deliberately."
fi
[ "$APPLY" = 1 ] && echo && echo "Restart your agent to pick up new skills."
exit 0
