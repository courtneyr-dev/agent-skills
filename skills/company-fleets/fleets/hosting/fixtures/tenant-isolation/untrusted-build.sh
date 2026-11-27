SYNTHETIC FIXTURE: untrusted customer build for Fixture Co tenant-a. The first line is a label, not code; sandbox-build drops it.
# Stand-in for a customer build: lists its source and writes to /tmp. Its output is never read as a probe result.
ls /src > /tmp/sources.txt
echo "built $(wc -l < /tmp/sources.txt) source entries"
