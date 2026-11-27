#!/usr/bin/env python3
import sys, os, json, re, shutil, subprocess
prompt = sys.stdin.read()
with open(os.environ["FAKE_LOG"], "a") as fh:
    fh.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd(), "head": prompt[:120]}) + "\n")
m = re.search(r"task_id: (\S+)", prompt)
if not m:  # scheduler session: behave like the rig's schedule stub (real ones take seconds)
    import time; time.sleep(float(os.environ.get("FAKE_SCHEDULE_DELAY", "1.2")))
    os.makedirs(".noodle", exist_ok=True)
    open(".noodle/orders-next.json", "w").write('{"orders": []}')
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}}), flush=True)
    sys.exit(0)
if os.environ.get("FAKE_MODE") == "fail":
    print(json.dumps({"type": "turn.failed", "error": {"message": "fake worker failure"}}), flush=True)
    sys.exit(1)
tid = m.group(1); att = re.search(r"attempt_id: (\S+)", prompt).group(1)
impl = os.environ.get("FAKE_IMPL") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_impl")
for f in ("calc.py", "test_calc.py"):
    shutil.copy(os.path.join(impl, f), f)
subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "commit", "-q", "-m", "Implement multiply (fake provider)"], check=True)
head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
print(json.dumps({"type": "thread.started", "thread_id": "fake"}), flush=True)
print(json.dumps({"type": "item.completed", "item": {"id": "i1", "type": "agent_message", "text": "FACTORY-EXECUTE-PROOF frig-factory-execute-v1 %s %s %s\nfake provider" % (tid, att, head)}}), flush=True)
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}}), flush=True)
