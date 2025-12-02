from flask import Flask, jsonify, render_template
import subprocess
import shutil
import re
import time

from typing import Dict

app = Flask(__name__)

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except subprocess.CalledProcessError as e:
        return e.output.strip() if e.output else str(e)


def run_cmd_full(cmd):
    """Run a command and return its output and exit code."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    out = result.stdout.strip()
    if result.returncode != 0:
        err = result.stderr.strip()
        if err:
            out = f"{out}\n{err}" if out else err
    return out, result.returncode


def _parse_size_to_mib(value: str) -> float:
    """Convert human-readable size like '9.9Gi' to MiB as float."""
    try:
        if value.lower().endswith('gi'):
            return float(value[:-2]) * 1024
        if value.lower().endswith('g'):
            return float(value[:-1]) * 1024
        if value.lower().endswith('mi'):
            return float(value[:-2])
        if value.lower().endswith('m'):
            return float(value[:-1])
        if value.lower().endswith('ti'):
            return float(value[:-2]) * 1024 * 1024
        if value.lower().endswith('t'):
            return float(value[:-1]) * 1024 * 1024
        return float(value)
    except ValueError:
        return 0.0


def parse_memory(output: str) -> dict:
    """Parse output of `free -h` and return size metrics."""
    lines = output.splitlines()
    if len(lines) < 2:
        return {"raw": output}
    header = lines[0].split()
    values = lines[1].split()
    if values and values[0].lower().startswith('mem'):
        values = values[1:]
    mem = dict(zip(header, values))
    total = _parse_size_to_mib(mem.get('total', mem.get('Mem:', '0')))
    used = _parse_size_to_mib(mem.get('used', '0'))
    percent = round(used / total * 100) if total else 0
    return {
        "raw": output,
        "total": total,
        "used": used,
        "percent": percent,
    }


def parse_disk(output: str) -> dict:
    """Parse `df -h` output into a list of entries."""
    lines = output.splitlines()
    entries = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 6:
            filesystem, size, used, avail, pct, mount = parts[:6]
            try:
                pct_val = int(re.sub(r'[^0-9]', '', pct))
            except ValueError:
                pct_val = 0
            entries.append({
                "filesystem": filesystem,
                "size": size,
                "used": used,
                "avail": avail,
                "percent": pct_val,
                "mount": mount,
            })
    return {"raw": output, "entries": entries}


def parse_cpu_usage(delay: float = 0.1) -> Dict[str, float]:
    """Calculate CPU usage by sampling /proc/stat twice."""

    def read_cpu_line() -> list[int]:
        with open("/proc/stat", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("cpu "):
                    return [int(val) for val in line.split()[1:11]]
        return []

    first = read_cpu_line()
    time.sleep(delay)
    second = read_cpu_line()
    if not first or not second:
        return {"usage": 0.0, "idle": 0.0}

    deltas = [b - a for a, b in zip(first, second)]
    user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice = deltas
    idle_all = idle + iowait
    non_idle = user + nice + system + irq + softirq + steal
    total = idle_all + non_idle
    usage_pct = (non_idle / total * 100) if total else 0.0

    return {
        "usage": round(usage_pct, 2),
        "idle": round(idle_all / total * 100, 2) if total else 0.0,
        "user": round(user / total * 100, 2) if total else 0.0,
        "system": round(system / total * 100, 2) if total else 0.0,
        "iowait": round(iowait / total * 100, 2) if total else 0.0,
    }


def parse_network_counters() -> Dict[str, object]:
    """Parse /proc/net/dev and aggregate RX/TX counters."""

    interfaces = []
    total_rx = total_tx = 0
    try:
        with open("/proc/net/dev", "r", encoding="utf-8") as handle:
            lines = handle.readlines()[2:]
    except OSError:
        return {"rx_bytes": 0, "tx_bytes": 0, "interfaces": []}

    for line in lines:
        if ":" not in line:
            continue
        name, metrics = line.split(":", 1)
        parts = metrics.split()
        if len(parts) < 16:
            continue
        rx_bytes, tx_bytes = int(parts[0]), int(parts[8])
        iface = name.strip()
        interfaces.append({
            "name": iface,
            "rx_bytes": rx_bytes,
            "tx_bytes": tx_bytes,
        })
        if iface != "lo":
            total_rx += rx_bytes
            total_tx += tx_bytes

    return {"rx_bytes": total_rx, "tx_bytes": total_tx, "interfaces": interfaces}


def parse_speedtest(output: str) -> Dict[str, str]:
    """Parse `speedtest-cli --simple` output and return metrics."""
    ping = download = upload = ''
    for line in output.splitlines():
        if line.lower().startswith('ping:'):
            ping = line.split(':', 1)[1].strip()
        elif line.lower().startswith('download:'):
            download = line.split(':', 1)[1].strip()
        elif line.lower().startswith('upload:'):
            upload = line.split(':', 1)[1].strip()
    return {
        'raw': output,
        'ping': ping,
        'download': download,
        'upload': upload,
    }

def get_sysinfo():
    info = {}
    info['System'] = run_cmd('uname -a')
    if shutil.which('lsb_release'):
        info['Distribution'] = run_cmd('lsb_release -a')
    else:
        info['Distribution'] = 'lsb_release not available'
    cpu_model = run_cmd("grep -m1 'model name' /proc/cpuinfo")
    cpu_cores = run_cmd('nproc --all')
    info['CPU'] = {
        "model": cpu_model,
        "cores": cpu_cores,
        "usage": parse_cpu_usage(),
    }
    mem_output = run_cmd('free -h')
    disk_output = run_cmd('df -h')
    info['Memory'] = parse_memory(mem_output)
    info['Disk'] = parse_disk(disk_output)
    if shutil.which('speedtest-cli'):
        servers = ['68177', '60421', '59653', '64665', '68164']
        speed_data = None
        for sid in servers:
            out, rc = run_cmd_full(f'speedtest-cli --simple --server {sid}')
            if rc == 0 and 'Cannot retrieve speedtest configuration' not in out and 'ERROR' not in out:
                speed_data = parse_speedtest(out)
                break
        if not speed_data:
            auto_out, rc = run_cmd_full('speedtest-cli --simple')
            if rc == 0 and 'Cannot retrieve speedtest configuration' not in auto_out and 'ERROR' not in auto_out:
                speed_data = parse_speedtest(auto_out)
        if speed_data:
            info['Speedtest'] = speed_data
        else:
            fallback = run_cmd('ping -c 4 google.com')
            info['Speedtest'] = {'raw': fallback}
    else:
        info['Speedtest'] = 'speedtest-cli not available'
    if shutil.which('ip'):
        info['Network'] = run_cmd("ip -o -4 addr show | awk '{print $2, $4}'")
    else:
        info['Network'] = run_cmd('hostname -I')
    info['NetworkStats'] = parse_network_counters()
    return info

@app.route('/')
def index():
    data = get_sysinfo()
    return render_template('index.html', data=data)


@app.route('/api/sysinfo')
def api_sysinfo():
    data = get_sysinfo()
    response = jsonify(data)
    response.headers['Cache-Control'] = 'no-store, max-age=0, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8015)
