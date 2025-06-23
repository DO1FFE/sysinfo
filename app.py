from flask import Flask, render_template
import subprocess
import shutil
import re

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
    info['CPU'] = f"{cpu_model}\nCores: {cpu_cores}"
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
    return info

@app.route('/')
def index():
    data = get_sysinfo()
    return render_template('index.html', data=data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8015)
