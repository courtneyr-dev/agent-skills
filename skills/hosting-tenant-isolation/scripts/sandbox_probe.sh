# The harness probe: run by sandbox-build in its own container after the build. It tries each boundary and prints one JSON object. No network traffic is sent.
read_other=false
if [ -d /other ] && [ -n "$(ls /other 2>/dev/null)" ]; then read_other=true; fi
src_readable=false
if [ -n "$(ls /src 2>/dev/null)" ]; then src_readable=true; fi
src_writable=false
if touch /src/.probe 2>/dev/null; then src_writable=true; fi
tmp_writable=false
if touch /tmp/.probe 2>/dev/null; then tmp_writable=true; fi
secret_names=""
for name in $(awk 'BEGIN { for (n in ENVIRON) print n }'); do
  case "$name" in
    *SECRET*|*PASSWORD*|*TOKEN*|*KEY*|*CREDENTIAL*) secret_names="$secret_names\"$name\"," ;;
  esac
done
ifaces=""
for path in /sys/class/net/*; do
  name=${path##*/}
  [ "$name" = "lo" ] || [ "$name" = "*" ] || ifaces="$ifaces\"$name\","
done
printf '{"read_other":%s,"src_readable":%s,"src_writable":%s,"tmp_writable":%s,"secret_env_names":[%s],"extra_interfaces":[%s]}\n' \
  "$read_other" "$src_readable" "$src_writable" "$tmp_writable" "${secret_names%,}" "${ifaces%,}"
