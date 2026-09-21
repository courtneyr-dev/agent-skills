#!/bin/zsh
# lmk-notify.sh — send a Pushover notification for the lmk skill.
# Credentials come from the macOS Keychain (service pushover-lmk); never pass them as arguments.
set -euo pipefail

PRIORITY=0
while getopts "p:" opt; do
  case $opt in
    p) PRIORITY=$OPTARG ;;
    *) exit 64 ;;
  esac
done
shift $((OPTIND - 1))

if (( $# != 2 )); then
  echo 'usage: lmk-notify.sh [-p -2..2] "Title" "Message"' >&2
  exit 64
fi
TITLE=$1
MESSAGE=$2

USER_KEY=$(security find-generic-password -s pushover-lmk -a user_key -w 2>/dev/null) \
  || { echo "lmk: user_key not found in Keychain (service pushover-lmk)" >&2; exit 2; }
APP_TOKEN=$(security find-generic-password -s pushover-lmk -a app_token -w 2>/dev/null) \
  || { echo "lmk: app_token not found in Keychain (service pushover-lmk)" >&2; exit 2; }

EXTRA=()
if [[ $PRIORITY == 2 ]]; then
  # Pushover requires retry/expire for emergency priority; only used on explicit request.
  EXTRA=(--form-string "retry=60" --form-string "expire=600")
fi

RESPONSE=$(curl -sS --max-time 15 \
  --form-string "token=$APP_TOKEN" \
  --form-string "user=$USER_KEY" \
  --form-string "title=$TITLE" \
  --form-string "message=$MESSAGE" \
  --form-string "priority=$PRIORITY" \
  "${EXTRA[@]}" \
  https://api.pushover.net/1/messages.json)

echo "$RESPONSE"
[[ $RESPONSE == *'"status":1'* ]]
