from flask import Flask, render_template
import subprocess
import shutil

app = Flask(__name__)

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except subprocess.CalledProcessError as e:
        return e.output.strip() if e.output else str(e)

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
    info['Memory'] = run_cmd('free -h')
    info['Disk'] = run_cmd('df -h')
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
    app.run(host='0.0.0.0', port=5000)
