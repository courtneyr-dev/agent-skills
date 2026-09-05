#!/usr/bin/env bash
# Install these skills for any SKILL.md-compatible agent.
#
# Skills are installed once into a canonical directory (~/.agents/skills by default) and symlinked
# into each agent's own skills directory. One copy on disk, every agent sees the same version, and
# `git pull` updates all of them at once.
#
#   ./install.sh                          # everything, into auto-detected agents
#   ./install.sh --guided                 # pick what you want, one question at a time
#   ./install.sh --paths                  # show the available paths
#   ./install.sh -p wordpress -p pkm      # install only these paths
#   ./install.sh -a claude -a cursor      # specific agents
#   ./install.sh --list                   # show what would be installed, change nothing
#   ./install.sh --copy                   # copy instead of symlink (for agents that refuse links)
#   ./install.sh --external               # print install commands for third-party skills
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANON="${AGENT_SKILLS_DIR:-$HOME/.agents/skills}"
MODE=link
AGENTS=()
LIST=0
EXTERNAL=0
GUIDED=0
SHOW_PATHS=0
PATHS=()

while [ $# -gt 0 ]; do
  case "$1" in
    -a|--agent) AGENTS+=("$2"); shift 2 ;;
    --copy)     MODE=copy; shift ;;
    --list)     LIST=1; shift ;;
    --external) EXTERNAL=1; shift ;;
    --guided)   GUIDED=1; shift ;;
    --paths)    SHOW_PATHS=1; shift ;;
    -p|--path)  PATHS+=("$2"); shift 2 ;;
    -h|--help)  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
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

# With no -a flags, install for every agent whose directory already exists.
if [ ${#AGENTS[@]} -eq 0 ]; then
  for a in claude cursor codex openclaw gemini; do
    d="$(agent_dir "$a")"
    [ -d "$d" ] && AGENTS+=("$a")
  done
fi

if [ "$EXTERNAL" = 1 ]; then
  echo "Third-party skills are installed from their own upstreams, not from this repo."
  echo "Their licenses are recorded in manifest.json. Redistributable=false means the upstream"
  echo "ships no license or a custom one: install it from source, do not copy it around."
  echo
  python3 - "$HERE/manifest.json" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
for s in m['skills']:
    if s['kind'] == 'external':
        src = s['source']; p = f" --path {src['path']}" if src.get('path') else ""
        flag = "" if s['redistributable'] else "   # no redistribution — install from source"
        print(f"  # {s['name']}  [{s['license']}]{flag}")
        print(f"  npx skills@latest add {src['repo']}{p} -s {s['name']}")
    elif s['kind'] == 'external-suite':
        print(f"\n  # {s['name']} — {len(s['members'])} skills, {s['license']}")
        print(f"  # install via its own installer: https://github.com/{s['source']['repo']}")
PY
  exit 0
fi

path_info() { python3 - "$HERE/manifest.json" "$1" <<'PY'
import json, sys
m = json.load(open(sys.argv[1])); what = sys.argv[2]
paths = m.get('paths', {})
if what == 'list':
    for k, v in paths.items():
        print(f"  {k:<11} {len(v['skills']):>2} skills  {v['title']} — {v['description']}")
elif what == 'keys':
    print(' '.join(paths))
else:
    print('\n'.join(paths.get(what, {}).get('skills', [])))
PY
}

if [ "$SHOW_PATHS" = 1 ]; then
  echo "Paths — install a slice instead of everything:"; echo
  path_info list
  echo
  echo "  ./install.sh -p wordpress -p pkm     # install these"
  echo "  ./install.sh --guided                # choose interactively"
  exit 0
fi

if [ "$GUIDED" = 1 ]; then
  if [ ! -t 0 ] && [ -e /dev/tty ] && [ -z "${GUIDED_STDIN:-}" ]; then exec </dev/tty; fi
  echo "Which of these do you want? Answer y or n; anything else is treated as no."
  echo
  for k in $(path_info keys); do
    title=$(path_info list | grep "^  $k " | sed 's/^ *[a-z-]* *[0-9]* skills  //')
    n=$(path_info "$k" | grep -c .)
    printf "  %s (%s skills)\n     %s\n  install? [y/N] " "$k" "$n" "$title"
    read -r ans || ans=n
    case "$ans" in y|Y|yes|YES) PATHS+=("$k");; esac
    echo
  done
  if [ ${#PATHS[@]} -eq 0 ]; then echo "Nothing selected. Re-run with --paths to see the options."; exit 0; fi
fi

SKILLS=()
if [ ${#PATHS[@]} -gt 0 ]; then
  for pth in "${PATHS[@]}"; do
    got=$(path_info "$pth")
    [ -z "$got" ] && { echo "unknown path: $pth (see --paths)" >&2; exit 2; }
    while IFS= read -r s; do
      [ -n "$s" ] && [ -f "$HERE/skills/$s/SKILL.md" ] && SKILLS+=("$s")
    done <<< "$got"
  done
  # de-duplicate: a skill can belong to more than one path
  SKILLS=($(printf '%s\n' "${SKILLS[@]}" | sort -u))
  echo "Selected paths: ${PATHS[*]}  (${#SKILLS[@]} skills)"
else
  for d in "$HERE"/skills/*/; do
    [ -f "$d/SKILL.md" ] && SKILLS+=("$(basename "$d")")
  done
fi

if [ "$LIST" = 1 ]; then
  echo "Would install ${#SKILLS[@]} skills into $CANON"
  echo "Would link into: ${AGENTS[*]:-<none detected>}"
  printf '  %s\n' "${SKILLS[@]}"
  exit 0
fi

mkdir -p "$CANON"
installed=0
for s in "${SKILLS[@]}"; do
  if [ "$MODE" = copy ]; then
    rm -rf "${CANON:?}/$s"; cp -R "$HERE/skills/$s" "$CANON/$s"
  else
    ln -sfn "$HERE/skills/$s" "$CANON/$s"
  fi
  installed=$((installed + 1))
done
echo "installed $installed skills into $CANON ($MODE)"

for a in "${AGENTS[@]}"; do
  d="$(agent_dir "$a")" || { echo "unknown agent: $a" >&2; continue; }
  mkdir -p "$d"
  n=0
  for s in "${SKILLS[@]}"; do
    if [ -e "$d/$s" ] && [ ! -L "$d/$s" ]; then
      echo "  skip $a/$s — a real directory already exists there, not overwriting" >&2
      continue
    fi
    ln -sfn "$CANON/$s" "$d/$s"; n=$((n + 1))
  done
  echo "linked $n skills into $a ($d)"
done

echo
echo "Restart your agent to pick up new skills."
echo "Third-party skills are not included here — run ./install.sh --external for those."
