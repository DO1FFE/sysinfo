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
ip -o -4 addr show | awk '{print $2, $4}'

print_section "Speedtest"
if command -v speedtest-cli >/dev/null 2>&1; then
  speedtest-cli --simple
else
  echo "speedtest-cli not available"
fi

