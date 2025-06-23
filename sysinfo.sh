#!/bin/bash
# Print comprehensive system information

print_section() {
  echo "=============================="
  echo "$1"
  echo "=============================="
}

print_section "System"
uname -a

print_section "Distribution"
if command -v lsb_release >/dev/null 2>&1; then
  lsb_release -a
else
  echo "lsb_release not available"
fi

print_section "CPU"
grep -m1 "model name" /proc/cpuinfo
nproc --all

print_section "Memory"
free -h

print_section "Disk"
df -h

print_section "Network"
if command -v ip >/dev/null 2>&1; then
  ip -o -4 addr show | awk '{print $2, $4}'
else
  echo "ip command not available"
fi

print_section "Speedtest"
if command -v speedtest-cli >/dev/null 2>&1; then
  # Try several German servers in case one fails
  SERVERS=(68177 60421 59653 64665 68164)
  SUCCESS=false
  for SID in "${SERVERS[@]}"; do
    echo "Testing with server $SID..."
    if speedtest-cli --simple --server "$SID"; then
      SUCCESS=true
      break
    fi
    echo "Server $SID failed, trying next..." >&2
  done
  if [ "$SUCCESS" = false ]; then
    echo "All preset servers failed, trying automatic selection..." >&2
    if speedtest-cli --simple; then
      SUCCESS=true
    fi
  fi
  if [ "$SUCCESS" = false ]; then
    echo "Speedtest failed. Running ping as fallback." >&2
    ping -c 4 google.com
  fi
else
  echo "speedtest-cli not available"
fi

