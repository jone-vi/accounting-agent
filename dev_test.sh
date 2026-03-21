#!/bin/bash
# dev_test.sh — Run a single test against the local server and show a clean log summary.
# Usage:   bash dev_test.sh <test_name>
# Example: bash dev_test.sh voucher_supplier

PORT=8000
SERVER_LOG="/tmp/agent_server.log"
SERVER_PID_FILE="/tmp/agent_server.pid"
LOG_MARKER_FILE="/tmp/agent_log_marker"

# ── Start server if not already running ────────────────────────────────────────

start_server_if_needed() {
  if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
    echo "✓ Server running on :$PORT"
    return 0
  fi
  echo "Starting server on :$PORT ..."
  ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY .env | cut -d= -f2-) \
    PORT=$PORT python3 main.py >> "$SERVER_LOG" 2>&1 &
  echo $! > "$SERVER_PID_FILE"
  for i in $(seq 1 20); do
    sleep 1
    if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
      echo "✓ Server ready"
      return 0
    fi
  done
  echo "✗ Server failed to start — check $SERVER_LOG"
  exit 1
}

# ── Main ───────────────────────────────────────────────────────────────────────

if [[ -z "$1" ]]; then
  echo "Usage: bash dev_test.sh <test_name>"
  echo "Run 'bash test_prompts.sh' for available test names."
  exit 1
fi

start_server_if_needed

# Record log position before the test
LOG_LINES_BEFORE=$(wc -l < "$SERVER_LOG" 2>/dev/null || echo 0)
echo "$LOG_LINES_BEFORE" > "$LOG_MARKER_FILE"

echo ""
echo "▶ TEST: $1"
echo "────────────────────────────────────────────────────────────────"

# Run test and show raw response
bash test_prompts.sh "$1"

# Wait for final log entries
sleep 2

# ── Parse and print log summary ────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  SERVER LOG SUMMARY"
echo "════════════════════════════════════════════════════════════════"

python3 - "$LOG_LINES_BEFORE" << 'PYEOF'
import sys, re

log_file = "/tmp/agent_server.log"
lines_before = int(sys.argv[1]) if len(sys.argv) > 1 else 0

try:
    with open(log_file) as f:
        all_lines = f.readlines()
except FileNotFoundError:
    print("No log file found.")
    sys.exit(0)

lines = all_lines[lines_before:]

tool_calls = []      # list of (name, status)  status = "ok" | "err" | "pending"
api_calls_ok = 0
api_errors = 0
error_details = []
iterations = 0
rate_limits = 0
prompt_line = ""
current_tool = None

for line in lines:
    stripped = line.strip()

    if "Prompt:" in line and not prompt_line:
        m = re.search(r"Prompt: (.+)", stripped)
        if m:
            prompt_line = m.group(1)[:120]

    if "Iteration " in line:
        m = re.search(r"Iteration (\d+)", stripped)
        if m:
            iterations = max(iterations, int(m.group(1)))

    if "Calling tool:" in line:
        m = re.search(r"Calling tool: (\w+)\(", stripped)
        if m:
            current_tool = m.group(1)
            tool_calls.append([current_tool, "?"])

    if re.search(r"✓ \d+", stripped):
        api_calls_ok += 1
        if tool_calls and tool_calls[-1][1] == "?":
            tool_calls[-1][1] = "ok"

    if re.search(r"✗ \d+", stripped):
        api_errors += 1
        if tool_calls and tool_calls[-1][1] == "?":
            tool_calls[-1][1] = "err"
        m = re.search(r"✗ (\d+) (.+)", stripped)
        if m:
            error_details.append(f"  HTTP {m.group(1)} {m.group(2)}")

    if "error body:" in line:
        # Extract validation messages
        m = re.search(r'"message":"([^"]+)"', stripped)
        vm = re.findall(r'"message":"([^"]+)"', stripped)
        if vm:
            error_details.append("    → " + " | ".join(dict.fromkeys(vm)))

    if "429" in line and "Retrying" in line:
        rate_limits += 1

    if "Giving up" in line:
        error_details.append("  ⚠ " + stripped[-120:])

# ── Print ───────────────────────────────────────────────────────────────────

if prompt_line:
    print(f"Prompt:      {prompt_line}")

print(f"Iterations:  {iterations + 1}")
print(f"Tool calls:  {len(tool_calls)}  (ok: {api_calls_ok}, err: {api_errors})"
      + (f"  ⚠ {rate_limits}x rate-limited" if rate_limits else ""))
print()

print("Tool call sequence:")
for i, (name, status) in enumerate(tool_calls, 1):
    icon = "✓" if status == "ok" else ("✗" if status == "err" else "·")
    print(f"  {i:2}. {icon} {name}")

if error_details:
    print()
    print("Errors:")
    seen = set()
    for e in error_details:
        key = e[:80]
        if key not in seen:
            seen.add(key)
            print(e)

# Efficiency hint
unnecessary = [n for n, s in tool_calls if n.startswith("list_") or n.startswith("get_")]
if len(unnecessary) > 3:
    print()
    print(f"⚠ {len(unnecessary)} read/list calls — check for unnecessary lookups")

PYEOF

echo "════════════════════════════════════════════════════════════════"
