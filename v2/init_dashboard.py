#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import re
import shutil
import threading
import time
from pathlib import Path

SCRIPT_VERSION = "2.0.1"
GITHUB_REPO = "eero-drew/minirackdash"
GITHUB_RAW = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
SCRIPT_URL_V1 = f"{GITHUB_RAW}/init_dashboard.py"
SCRIPT_URL_V2 = f"{GITHUB_RAW}/v2/init_dashboard.py"
INSTALL_DIR = "/home/eero/dashboard"
NETWORK_ID = "18073602"
USER = "eero"

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    NC = '\033[0m'

def print_color(color, message):
    print(f"{color}{message}{Colors.NC}")

def print_header(message):
    print("\n" + "=" * 60)
    print_color(Colors.BLUE, message.center(60))
    print("=" * 60 + "\n")

def print_success(message):
    print_color(Colors.GREEN, f"✓ {message}")

def print_error(message):
    print_color(Colors.RED, f"✗ {message}")

def print_warning(message):
    print_color(Colors.YELLOW, f"⚠ {message}")

def print_info(message):
    print_color(Colors.CYAN, f"ℹ {message}")

def extract_version_from_script(script_content):
    match = re.search(r'SCRIPT_VERSION\s*=\s*["\']([^"\']+)["\']', script_content)
    if match:
        return match.group(1)
    return None

def compare_versions(v1, v2):
    parts1 = [int(x) for x in v1.split('.')]
    parts2 = [int(x) for x in v2.split('.')]
    for i in range(max(len(parts1), len(parts2))):
        p1 = parts1[i] if i < len(parts1) else 0
        p2 = parts2[i] if i < len(parts2) else 0
        if p1 > p2:
            return 1
        elif p1 < p2:
            return -1
    return 0

def get_major_version(version):
    return int(version.split('.')[0])

def input_with_timeout(prompt, timeout):
    result = [None]
    
    def get_input():
        try:
            result[0] = input(prompt).strip().lower()
        except:
            pass
    
    print_color(Colors.MAGENTA, prompt)
    thread = threading.Thread(target=get_input)
    thread.daemon = True
    thread.start()
    
    for i in range(timeout, 0, -1):
        if not thread.is_alive():
            break
        print_color(Colors.YELLOW, f"  Defaulting to 'No' in {i} seconds...", end='\r')
        time.sleep(1)
    
    if thread.is_alive():
        print_color(Colors.YELLOW, "\n  Timeout reached. Staying on current version.        ")
        return None
    
    print()
    return result[0]

def check_for_updates():
    print_header("Version Check")
    current_major = get_major_version(SCRIPT_VERSION)
    print_info(f"Current Version: v{SCRIPT_VERSION} (v{current_major}.x)")
    print_info("Checking for updates from GitHub...")
    
    try:
        if current_major == 1:
            print_info("You are running v1.x")
            print_info("Checking for v1 updates...")
            
            try:
                with urllib.request.urlopen(SCRIPT_URL_V1, timeout=10) as response:
                    latest_v1_script = response.read().decode('utf-8')
                latest_v1_version = extract_version_from_script(latest_v1_script)
            except:
                latest_v1_version = None
                latest_v1_script = None
            
            try:
                with urllib.request.urlopen(SCRIPT_URL_V2, timeout=10) as response:
                    latest_v2_script = response.read().decode('utf-8')
                latest_v2_version = extract_version_from_script(latest_v2_script)
            except:
                latest_v2_version = None
                latest_v2_script = None
            
            if latest_v1_version:
                print_info(f"Latest v1 Version: v{latest_v1_version}")
                v1_comparison = compare_versions(latest_v1_version, SCRIPT_VERSION)
                
                if v1_comparison > 0:
                    print_warning(f"New v1 version available: v{latest_v1_version}")
            
            if latest_v2_version:
                print_color(Colors.MAGENTA, f"🚀 v2 Available: v{latest_v2_version}")
                print_color(Colors.CYAN, "\nNew features in v2:")
                print_color(Colors.GREEN, "  • Header with logo and action buttons")
                print_color(Colors.GREEN, "  • Device details panel (names, IPs, signal strength)")
                print_color(Colors.GREEN, "  • Integrated speed test functionality")
                print_color(Colors.GREEN, "  • Enhanced UI with modals and animations")
                print_color(Colors.GREEN, "  • Optimized for 1280x400 resolution")
                print()
                
                response = input_with_timeout("Do you want to upgrade to v2? (yes/no) [Default: no]: ", 5)
                
                if response and response in ['yes', 'y']:
                    print_success("Upgrading to v2...")
                    current_script = os.path.abspath(__file__)
                    backup_script = f"{current_script}.v1.backup"
                    shutil.copy2(current_script, backup_script)
                    print_success(f"v1 backed up to: {backup_script}")
                    
                    with open(current_script, 'w') as f:
                        f.write(latest_v2_script)
                    os.chmod(current_script, 0o755)
                    print_success("Upgraded to v2 successfully!")
                    print_info("Restarting with v2...")
                    time.sleep(1)
                    os.execv(sys.executable, [sys.executable, current_script] + sys.argv[1:])
                else:
                    print_info("Staying on v1...")
                    if latest_v1_version and v1_comparison > 0:
                        print_info(f"Updating to latest v1 version: v{latest_v1_version}")
                        current_script = os.path.abspath(__file__)
                        backup_script = f"{current_script}.backup"
                        shutil.copy2(current_script, backup_script)
                        
                        with open(current_script, 'w') as f:
                            f.write(latest_v1_script)
                        os.chmod(current_script, 0o755)
                        print_success("Updated to latest v1!")
                        print_info("Restarting...")
                        time.sleep(1)
                        os.execv(sys.executable, [sys.executable, current_script] + sys.argv[1:])
                    else:
                        print_success("Already on latest v1 version!")
                    return False
            else:
                print_warning("Could not check for v2 updates")
                if latest_v1_version and v1_comparison > 0:
                    print_info(f"Updating to latest v1: v{latest_v1_version}")
                    current_script = os.path.abspath(__file__)
                    backup_script = f"{current_script}.backup"
                    shutil.copy2(current_script, backup_script)
                    
                    with open(current_script, 'w') as f:
                        f.write(latest_v1_script)
                    os.chmod(current_script, 0o755)
                    print_success("Updated to latest v1!")
                    print_info("Restarting...")
                    time.sleep(1)
                    os.execv(sys.executable, [sys.executable, current_script] + sys.argv[1:])
        
        elif current_major == 2:
            print_info("You are running v2.x")
            print_info("Checking for v2 updates...")
            
            with urllib.request.urlopen(SCRIPT_URL_V2, timeout=10) as response:
                latest_v2_script = response.read().decode('utf-8')
            
            latest_v2_version = extract_version_from_script(latest_v2_script)
            
            if not latest_v2_version:
                print_warning("Could not determine latest v2 version. Continuing...")
                return False
            
            print_info(f"Latest v2 Version: v{latest_v2_version}")
            comparison = compare_versions(latest_v2_version, SCRIPT_VERSION)
            
            if comparison == 0:
                print_success("You are running the latest v2 version!")
                return False
            elif comparison > 0:
                print_warning(f"New v2 version available: v{latest_v2_version}")
                print_info("Downloading and installing update...")
                current_script = os.path.abspath(__file__)
                backup_script = f"{current_script}.backup"
                shutil.copy2(current_script, backup_script)
                
                with open(current_script, 'w') as f:
                    f.write(latest_v2_script)
                os.chmod(current_script, 0o755)
                print_success("Script updated successfully!")
                print_info("Restarting with new version...")
                time.sleep(1)
                os.execv(sys.executable, [sys.executable, current_script] + sys.argv[1:])
            else:
                print_warning("You are running a newer version than available online")
                return False
        
        else:
            print_warning("Unknown version format. Continuing...")
            return False
            
    except Exception as e:
        print_warning(f"Could not check for updates: {e}")
        print_info("Continuing with current version...")
        return False

def check_root():
    if os.geteuid() != 0:
        print_error("This script must be run as root (use sudo)")
        sys.exit(1)

def run_command(command, shell=True, check=True, timeout=300, show_output=False):
    try:
        if show_output:
            result = subprocess.run(command, shell=shell, check=check, timeout=timeout)
            return result.returncode == 0
        else:
            result = subprocess.run(command, shell=shell, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
            return result.returncode == 0
    except subprocess.TimeoutExpired:
        print_error(f"Command timed out after {timeout}s")
        return False
    except subprocess.CalledProcessError as e:
        if show_output:
            return False
        print_error(f"Command failed with exit code {e.returncode}")
        if e.stderr:
            print_error(f"Error output: {e.stderr[:200]}")
        return False

def create_user():
    print_info("Setting up user account...")
    result = subprocess.run(['id', USER], capture_output=True, text=True)
    if result.returncode != 0:
        if run_command(f'useradd -m -s /bin/bash {USER}'):
            print_success(f"Created user: {USER}")
    else:
        print_success(f"User already exists: {USER}")

def update_system():
    print_header("Updating System Packages")
    print_info("Updating package lists...")
    if run_command('apt-get update', timeout=120, show_output=True):
        print_success("Package lists updated")
    else:
        print_warning("Package list update had issues, continuing...")
    
    print_info("Upgrading packages (this may take several minutes)...")
    upgrade_cmd = 'DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"'
    if run_command(upgrade_cmd, timeout=600, show_output=True):
        print_success("System packages upgraded")
    else:
        print_warning("Package upgrade had issues, continuing with installation...")

def install_dependencies():
    print_header("Installing Dependencies")
    
    required_packages = [
        'python3',
        'python3-pip',
        'python3-venv',
        'nginx',
        'git',
        'curl',
        'speedtest-cli'
    ]
    
    optional_packages = [
        ('chromium-browser', 'chromium'),
        ('unclutter', None),
        ('x11-xserver-utils', None),
        ('xdotool', None)
    ]
    
    print_info(f"Installing {len(required_packages)} required packages...")
    cmd = f"DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' {' '.join(required_packages)}"
    if not run_command(cmd, timeout=600, show_output=True):
        print_error("Failed to install required dependencies")
        sys.exit(1)
    print_success("Required packages installed")
    
    print_info("Installing optional packages for kiosk mode...")
    for primary, alternative in optional_packages:
        if run_command(f"DEBIAN_FRONTEND=noninteractive apt-get install -y {primary}", timeout=300):
            print_success(f"Installed {primary}")
        elif alternative:
            print_warning(f"{primary} not available, trying {alternative}...")
            if run_command(f"DEBIAN_FRONTEND=noninteractive apt-get install -y {alternative}", timeout=300):
                print_success(f"Installed {alternative}")
            else:
                print_warning(f"Could not install {primary} or {alternative}")
        else:
            print_warning(f"Could not install {primary} (optional)")
    
    print_success("All dependencies processed")

def create_directory_structure():
    print_info("Creating directory structure...")
    for directory in [f"{INSTALL_DIR}/backend", f"{INSTALL_DIR}/frontend", f"{INSTALL_DIR}/frontend/assets", f"{INSTALL_DIR}/logs"]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    run_command(f'chown -R {USER}:{USER} /home/eero')
    print_success("Directory structure created")

def setup_python_environment():
    print_info("Setting up Python virtual environment...")
    venv_path = f"{INSTALL_DIR}/venv"
    if not run_command(f'sudo -u {USER} python3 -m venv {venv_path}', timeout=120):
        print_error("Failed to create virtual environment")
        sys.exit(1)
    print_success("Virtual environment created")
    print_info("Installing Python packages (this may take a few minutes)...")
    run_command(f'sudo -u {USER} {venv_path}/bin/pip install --quiet --upgrade pip', timeout=120)
    if run_command(f'sudo -u {USER} {venv_path}/bin/pip install --quiet flask flask-cors requests gunicorn speedtest-cli', timeout=300):
        print_success("Python packages installed")
    else:
        print_error("Failed to install Python packages")
        sys.exit(1)

def create_backend_api():
    print_info("Creating backend API...")
    content = f"""#!/usr/bin/env python3
import os
import requests
import speedtest
import threading
from datetime import datetime, timedelta
from flask import Flask, jsonify
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(filename='/home/eero/dashboard/logs/backend.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

NETWORK_ID = "{NETWORK_ID}"
EERO_API_BASE = "https://api-user.e2ro.com/2.2"
API_TOKEN_FILE = "/home/eero/dashboard/.eero_token"

class EeroAPI:
    def __init__(self):
        self.session = requests.Session()
        self.api_token = self.load_token()
    
    def load_token(self):
        try:
            if os.path.exists(API_TOKEN_FILE):
                with open(API_TOKEN_FILE, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            logging.error(f"Error loading API token: {{e}}")
        return None
    
    def get_headers(self):
        headers = {{
            'Content-Type': 'application/json',
            'User-Agent': 'Eero-Dashboard/2.0'
        }}
        if self.api_token:
            headers['X-User-Token'] = self.api_token
        return headers
    
    def get_devices(self):
        try:
            url = f"{{EERO_API_BASE}}/networks/{{NETWORK_ID}}/devices"
            response = self.session.get(url, headers=self.get_headers(), timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error fetching devices: {{e}}")
            return None
    
    def get_bandwidth_usage(self):
        try:
            url = f"{{EERO_API_BASE}}/networks/{{NETWORK_ID}}/insights/usage"
            response = self.session.get(url, headers=self.get_headers(), timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error fetching bandwidth: {{e}}")
            return None

eero_api = EeroAPI()
data_cache = {{
    'connected_users': [],
    'wifi_versions': {{}},
    'bandwidth': [],
    'devices': [],
    'last_update': None,
    'speedtest_running': False,
    'speedtest_result': None
}}

def update_cache():
    global data_cache
    try:
        devices_data = eero_api.get_devices()
        if devices_data:
            connected = [d for d in devices_data.get('data', []) if d.get('connected')]
            current_time = datetime.now()
            
            data_cache['connected_users'].append({{'timestamp': current_time.isoformat(), 'count': len(connected)}})
            two_hours_ago = current_time - timedelta(hours=2)
            data_cache['connected_users'] = [entry for entry in data_cache['connected_users'] if datetime.fromisoformat(entry['timestamp']) > two_hours_ago]
            
            wifi_versions = {{}}
            for device in connected:
                wifi_std = device.get('connection', {{}}).get('wifi_standard', 'Unknown')
                wifi_label = f"WiFi {{wifi_std[-1]}}" if wifi_std != 'Unknown' else 'Unknown'
                wifi_versions[wifi_label] = wifi_versions.get(wifi_label, 0) + 1
            data_cache['wifi_versions'] = wifi_versions
            
            device_list = []
            for device in connected:
                connection = device.get('connection', {{}})
                device_info = {{
                    'name': device.get('nickname') or device.get('hostname', 'Unknown Device'),
                    'ip': connection.get('ip', 'N/A'),
                    'mac': device.get('mac', 'N/A'),
                    'manufacturer': device.get('manufacturer', 'Unknown'),
                    'signal_strength': connection.get('signal_strength', 0),
                    'wifi_standard': connection.get('wifi_standard', 'Unknown'),
                    'connected_at': device.get('connected', {{}}).get('last_changed', 'Unknown')
                }}
                device_list.append(device_info)
            data_cache['devices'] = sorted(device_list, key=lambda x: x['name'].lower())
        
        bandwidth_data = eero_api.get_bandwidth_usage()
        if bandwidth_data:
            current_time = datetime.now()
            usage = bandwidth_data.get('data', {{}})
            data_cache['bandwidth'].append({{
                'timestamp': current_time.isoformat(),
                'download': usage.get('download', 0) / 1024 / 1024,
                'upload': usage.get('upload', 0) / 1024 / 1024
            }})
            two_hours_ago = current_time - timedelta(hours=2)
            data_cache['bandwidth'] = [entry for entry in data_cache['bandwidth'] if datetime.fromisoformat(entry['timestamp']) > two_hours_ago]
        
        data_cache['last_update'] = datetime.now().isoformat()
        logging.info("Cache updated successfully")
    except Exception as e:
        logging.error(f"Error updating cache: {{e}}")

def run_speedtest():
    global data_cache
    try:
        data_cache['speedtest_running'] = True
        logging.info("Starting speed test...")
        st = speedtest.Speedtest()
        st.get_best_server()
        download_speed = st.download() / 1_000_000
        upload_speed = st.upload() / 1_000_000
        ping = st.results.ping
        
        data_cache['speedtest_result'] = {{
            'download': round(download_speed, 2),
            'upload': round(upload_speed, 2),
            'ping': round(ping, 2),
            'timestamp': datetime.now().isoformat()
        }}
        logging.info(f"Speed test complete: {{data_cache['speedtest_result']}}")
    except Exception as e:
        logging.error(f"Speed test failed: {{e}}")
        data_cache['speedtest_result'] = {{'error': str(e)}}
    finally:
        data_cache['speedtest_running'] = False

@app.route('/api/dashboard')
def get_dashboard_data():
    update_cache()
    return jsonify(data_cache)

@app.route('/api/devices')
def get_devices():
    return jsonify({{'devices': data_cache.get('devices', []), 'count': len(data_cache.get('devices', []))}})

@app.route('/api/speedtest/start', methods=['POST'])
def start_speedtest():
    if data_cache['speedtest_running']:
        return jsonify({{'status': 'running', 'message': 'Speed test already in progress'}}), 409
    
    thread = threading.Thread(target=run_speedtest)
    thread.daemon = True
    thread.start()
    return jsonify({{'status': 'started', 'message': 'Speed test initiated'}})

@app.route('/api/speedtest/status')
def get_speedtest_status():
    return jsonify({{
        'running': data_cache['speedtest_running'],
        'result': data_cache['speedtest_result']
    }})

@app.route('/api/health')
def health_check():
    return jsonify({{'status': 'ok', 'timestamp': datetime.now().isoformat()}})

@app.route('/api/version')
def get_version():
    return jsonify({{'version': '{SCRIPT_VERSION}', 'name': 'Eero Dashboard', 'repository': 'https://github.com/{GITHUB_REPO}'}})

if __name__ == '__main__':
    update_cache()
    app.run(host='127.0.0.1', port=5000, debug=False)
"""
    with open(f"{INSTALL_DIR}/backend/eero_api.py", 'w') as f:
        f.write(content)
    os.chmod(f"{INSTALL_DIR}/backend/eero_api.py", 0o755)
    run_command(f'chown {USER}:{USER} {INSTALL_DIR}/backend/eero_api.py')
    print_success("Backend API created")

def create_frontend():
    print_info("Creating frontend dashboard...")
    content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Eero Network Dashboard v2</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            background: linear-gradient(135deg, #001a33 0%, #003366 100%); 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            color: #ffffff; 
            overflow: hidden;
            height: 100vh;
        }
        
        .header {
            background: rgba(0, 20, 40, 0.9);
            padding: 8px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid rgba(77, 166, 255, 0.3);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        
        .logo-container {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .logo {
            height: 30px;
            width: auto;
        }
        
        .header-title {
            font-size: 18px;
            font-weight: 600;
            color: #4da6ff;
        }
        
        .header-actions {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .header-btn {
            padding: 6px 12px;
            background: rgba(77, 166, 255, 0.2);
            border: 2px solid #4da6ff;
            border-radius: 6px;
            color: #ffffff;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            transition: all 0.3s ease;
        }
        
        .header-btn:hover {
            background: rgba(77, 166, 255, 0.4);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(77, 166, 255, 0.3);
        }
        
        .header-btn:active {
            transform: translateY(0);
        }
        
        .header-btn.running {
            background: rgba(255, 193, 7, 0.3);
            border-color: #ffc107;
            cursor: not-allowed;
        }
        
        .header-btn i {
            font-size: 14px;
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 15px;
            font-size: 11px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #4CAF50;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .dashboard-container {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1fr;
            grid-template-rows: 1fr;
            gap: 10px;
            padding: 10px;
            height: calc(100vh - 60px);
        }
        
        .chart-card {
            background: rgba(0, 40, 80, 0.7);
            border-radius: 10px;
            padding: 10px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            flex-direction: column;
        }
        
        .chart-title {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 8px;
            text-align: center;
            color: #4da6ff;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .chart-container {
            flex: 1;
            position: relative;
            min-height: 0;
        }
        
        canvas {
            max-width: 100%;
            max-height: 100%;
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        
        .modal.active {
            display: flex;
        }
        
        .modal-content {
            background: linear-gradient(135deg, #001a33 0%, #003366 100%);
            border-radius: 15px;
            padding: 30px;
            max-width: 900px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            border: 2px solid rgba(77, 166, 255, 0.3);
            box-shadow: 0 10px 50px rgba(0, 0, 0, 0.5);
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(77, 166, 255, 0.3);
        }
        
        .modal-title {
            font-size: 24px;
            color: #4da6ff;
        }
        
        .close-btn {
            background: none;
            border: none;
            color: #ffffff;
            font-size: 28px;
            cursor: pointer;
            transition: color 0.3s ease;
        }
        
        .close-btn:hover {
            color: #ff6b6b;
        }
        
        .device-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        
        .device-table th {
            background: rgba(77, 166, 255, 0.2);
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #4da6ff;
            border-bottom: 2px solid rgba(77, 166, 255, 0.3);
        }
        
        .device-table td {
            padding: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .device-table tr:hover {
            background: rgba(77, 166, 255, 0.1);
        }
        
        .signal-bar {
            width: 100px;
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
        }
        
        .signal-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        
        .signal-excellent { background: #4CAF50; }
        .signal-good { background: #8BC34A; }
        .signal-fair { background: #FFC107; }
        .signal-poor { background: #FF9800; }
        .signal-weak { background: #F44336; }
        
        .speedtest-container {
            text-align: center;
            padding: 20px;
        }
        
        .speedtest-results {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-top: 30px;
        }
        
        .speedtest-metric {
            background: rgba(0, 40, 80, 0.5);
            padding: 25px;
            border-radius: 10px;
            border: 1px solid rgba(77, 166, 255, 0.3);
        }
        
        .speedtest-metric-label {
            font-size: 14px;
            color: #4da6ff;
            margin-bottom: 10px;
        }
        
        .speedtest-metric-value {
            font-size: 36px;
            font-weight: 600;
            color: #ffffff;
        }
        
        .speedtest-metric-unit {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.7);
        }
        
        .spinner {
            border: 4px solid rgba(77, 166, 255, 0.3);
            border-top: 4px solid #4da6ff;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .device-count {
            font-size: 16px;
            color: rgba(255, 255, 255, 0.8);
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-container">
            <img src="/assets/eero-logo.png" alt="Eero" class="logo" onerror="this.style.display='none'">
            <div class="header-title">Network Dashboard</div>
        </div>
        <div class="header-actions">
            <div class="status-indicator">
                <div class="status-dot"></div>
                <span id="lastUpdate">Loading...</span>
            </div>
            <button class="header-btn" id="deviceDetailsBtn">
                <i class="fas fa-list"></i>
                <span>Devices</span>
            </button>
            <button class="header-btn" id="speedTestBtn">
                <i class="fas fa-gauge-high"></i>
                <span>Speed Test</span>
            </button>
        </div>
    </div>

    <div class="dashboard-container">
        <div class="chart-card">
            <div class="chart-title">Connected Users</div>
            <div class="chart-container">
                <canvas id="usersChart"></canvas>
            </div>
        </div>
        <div class="chart-card">
            <div class="chart-title">WiFi Distribution</div>
            <div class="chart-container">
                <canvas id="wifiChart"></canvas>
            </div>
        </div>
        <div class="chart-card">
            <div class="chart-title">Download Bandwidth</div>
            <div class="chart-container">
                <canvas id="downloadChart"></canvas>
            </div>
        </div>
        <div class="chart-card">
            <div class="chart-title">Upload Bandwidth</div>
            <div class="chart-container">
                <canvas id="uploadChart"></canvas>
            </div>
        </div>
    </div>

    <div class="modal" id="deviceModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">Connected Devices</h2>
                <button class="close-btn" id="closeDeviceModal">&times;</button>
            </div>
            <div class="device-count" id="deviceCount">Loading...</div>
            <table class="device-table">
                <thead>
                    <tr>
                        <th>Device Name</th>
                        <th>IP Address</th>
                        <th>Manufacturer</th>
                        <th>WiFi</th>
                        <th>Signal</th>
                    </tr>
                </thead>
                <tbody id="deviceTableBody">
                    <tr><td colspan="5" style="text-align: center;">Loading devices...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <div class="modal" id="speedTestModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">Internet Speed Test</h2>
                <button class="close-btn" id="closeSpeedTestModal">&times;</button>
            </div>
            <div class="speedtest-container" id="speedTestContainer">
                <p>Click "Run Test" to measure your internet speed</p>
                <button class="header-btn" id="runSpeedTest" style="margin: 20px auto;">
                    <i class="fas fa-play"></i>
                    <span>Run Test</span>
                </button>
            </div>
        </div>
    </div>

    <script>
        let charts = { users: null, wifi: null, download: null, upload: null };
        const chartColors = {
            primary: '#4da6ff',
            secondary: '#ff6b6b',
            success: '#51cf66',
            warning: '#ffd43b',
            info: '#74c0fc'
        };
        
        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#ffffff',
                        font: { size: 10 }
                    }
                }
            },
            scales: {
                y: {
                    ticks: { color: '#ffffff', font: { size: 9 } },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                x: {
                    ticks: { color: '#ffffff', font: { size: 9 } },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                }
            }
        };

        function initCharts() {
            const usersCtx = document.getElementById('usersChart').getContext('2d');
            charts.users = new Chart(usersCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Connected Users',
                        data: [],
                        borderColor: chartColors.primary,
                        backgroundColor: 'rgba(77, 166, 255, 0.1)',
                        tension: 0.4,
                        fill: true,
                        borderWidth: 2
                    }]
                },
                options: commonOptions
            });

            const wifiCtx = document.getElementById('wifiChart').getContext('2d');
            charts.wifi = new Chart(wifiCtx, {
                type: 'doughnut',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        backgroundColor: [
                            chartColors.primary,
                            chartColors.success,
                            chartColors.warning,
                            chartColors.secondary,
                            chartColors.info
                        ],
                        borderWidth: 2,
                        borderColor: '#001a33'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: '#ffffff',
                                font: { size: 10 },
                                padding: 8
                            }
                        }
                    }
                }
            });

            const downloadCtx = document.getElementById('downloadChart').getContext('2d');
            charts.download = new Chart(downloadCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Download (Mbps)',
                        data: [],
                        borderColor: chartColors.success,
                        backgroundColor: 'rgba(81, 207, 102, 0.1)',
                        tension: 0.4,
                        fill: true,
                        borderWidth: 2
                    }]
                },
                options: commonOptions
            });

            const uploadCtx = document.getElementById('uploadChart').getContext('2d');
            charts.upload = new Chart(uploadCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Upload (Mbps)',
                        data: [],
                        borderColor: chartColors.secondary,
                        backgroundColor: 'rgba(255, 107, 107, 0.1)',
                        tension: 0.4,
                        fill: true,
                        borderWidth: 2
                    }]
                },
                options: commonOptions
            });
        }

        async function updateDashboard() {
            try {
                const response = await fetch('/api/dashboard');
                const data = await response.json();

                const userLabels = data.connected_users.map(entry => {
                    const date = new Date(entry.timestamp);
                    return date.toLocaleTimeString();
                });
                const userCounts = data.connected_users.map(entry => entry.count);
                charts.users.data.labels = userLabels;
                charts.users.data.datasets[0].data = userCounts;
                charts.users.update();

                const wifiLabels = Object.keys(data.wifi_versions);
                const wifiData = Object.values(data.wifi_versions);
                charts.wifi.data.labels = wifiLabels;
                charts.wifi.data.datasets[0].data = wifiData;
                charts.wifi.update();

                const bandwidthLabels = data.bandwidth.map(entry => {
                    const date = new Date(entry.timestamp);
                    return date.toLocaleTimeString();
                });
                const downloadData = data.bandwidth.map(entry => entry.download);
                const uploadData = data.bandwidth.map(entry => entry.upload);
                
                charts.download.data.labels = bandwidthLabels;
                charts.download.data.datasets[0].data = downloadData;
                charts.download.update();

                charts.upload.data.labels = bandwidthLabels;
                charts.upload.data.datasets[0].data = uploadData;
                charts.upload.update();

                const lastUpdate = new Date(data.last_update);
                document.getElementById('lastUpdate').textContent = `Updated: ${lastUpdate.toLocaleTimeString()}`;
            } catch (error) {
                console.error('Error updating dashboard:', error);
            }
        }

        function getSignalClass(strength) {
            if (strength >= 80) return 'signal-excellent';
            if (strength >= 60) return 'signal-good';
            if (strength >= 40) return 'signal-fair';
            if (strength >= 20) return 'signal-poor';
            return 'signal-weak';
        }

        async function loadDevices() {
            try {
                const response = await fetch('/api/devices');
                const data = await response.json();
                
                document.getElementById('deviceCount').textContent = `Total Connected: ${data.count} devices`;
                
                const tbody = document.getElementById('deviceTableBody');
                if (data.devices.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No devices connected</td></tr>';
                    return;
                }
                
                tbody.innerHTML = data.devices.map(device => `
                    <tr>
                        <td><strong>${device.name}</strong></td>
                        <td>${device.ip}</td>
                        <td>${device.manufacturer}</td>
                        <td>${device.wifi_standard}</td>
                        <td>
                            <div class="signal-bar">
                                <div class="signal-fill ${getSignalClass(device.signal_strength)}" 
                                     style="width: ${device.signal_strength}%"></div>
                            </div>
                        </td>
                    </tr>
                `).join('');
            } catch (error) {
                console.error('Error loading devices:', error);
            }
        }

        async function runSpeedTest() {
            const btn = document.getElementById('runSpeedTest');
            const container = document.getElementById('speedTestContainer');
            
            btn.classList.add('running');
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Running...</span>';
            btn.disabled = true;
            
            container.innerHTML = '<div class="spinner"></div><p>Testing your internet speed...</p><p style="font-size: 12px; color: rgba(255,255,255,0.6);">This may take 30-60 seconds</p>';
            
            try {
                await fetch('/api/speedtest/start', { method: 'POST' });
                
                const checkStatus = setInterval(async () => {
                    const response = await fetch('/api/speedtest/status');
                    const data = await response.json();
                    
                    if (!data.running && data.result) {
                        clearInterval(checkStatus);
                        
                        if (data.result.error) {
                            container.innerHTML = `<p style="color: #ff6b6b;">Error: ${data.result.error}</p>`;
                        } else {
                            container.innerHTML = `
                                <div class="speedtest-results">
                                    <div class="speedtest-metric">
                                        <div class="speedtest-metric-label">Download</div>
                                        <div class="speedtest-metric-value">${data.result.download}</div>
                                        <div class="speedtest-metric-unit">Mbps</div>
                                    </div>
                                    <div class="speedtest-metric">
                                        <div class="speedtest-metric-label">Upload</div>
                                        <div class="speedtest-metric-value">${data.result.upload}</div>
                                        <div class="speedtest-metric-unit">Mbps</div>
                                    </div>
                                    <div class="speedtest-metric">
                                        <div class="speedtest-metric-label">Ping</div>
                                        <div class="speedtest-metric-value">${data.result.ping}</div>
                                        <div class="speedtest-metric-unit">ms</div>
                                    </div>
                                </div>
                                <button class="header-btn" onclick="runSpeedTest()" style="margin: 20px auto;">
                                    <i class="fas fa-redo"></i><span>Test Again</span>
                                </button>
                            `;
                        }
                        
                        btn.classList.remove('running');
                        btn.innerHTML = '<i class="fas fa-play"></i><span>Run Test</span>';
                        btn.disabled = false;
                    }
                }, 2000);
            } catch (error) {
                console.error('Speed test error:', error);
                container.innerHTML = `<p style="color: #ff6b6b;">Error: ${error.message}</p>`;
                btn.classList.remove('running');
                btn.innerHTML = '<i class="fas fa-play"></i><span>Run Test</span>';
                btn.disabled = false;
            }
        }

        document.getElementById('deviceDetailsBtn').addEventListener('click', () => {
            document.getElementById('deviceModal').classList.add('active');
            loadDevices();
        });

        document.getElementById('closeDeviceModal').addEventListener('click', () => {
            document.getElementById('deviceModal').classList.remove('active');
        });

        document.getElementById('speedTestBtn').addEventListener('click', () => {
            document.getElementById('speedTestModal').classList.add('active');
        });

        document.getElementById('closeSpeedTestModal').addEventListener('click', () => {
            document.getElementById('speedTestModal').classList.remove('active');
        });

        document.getElementById('runSpeedTest').addEventListener('click', runSpeedTest);

        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.classList.remove('active');
                }
            });
        });

        window.addEventListener('load', () => {
            initCharts();
            updateDashboard();
            setInterval(updateDashboard, 60000);
        });
    </script>
</body>
</html>"""
    with open(f"{INSTALL_DIR}/frontend/index.html", 'w') as f:
        f.write(content)
    run_command(f'chown {USER}:{USER} {INSTALL_DIR}/frontend/index.html')
    print_success("Frontend dashboard created")
    print_info("📝 Place your eero logo at: /home/eero/dashboard/frontend/assets/eero-logo.png")

def configure_nginx():
    print_info("Configuring NGINX...")
    content = """server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    root /home/eero/dashboard/frontend;
    index index.html;
    
    location / { 
        try_files $uri $uri/ =404; 
    }
    
    location /assets/ {
        alias /home/eero/dashboard/frontend/assets/;
        expires 30d;
    }
    
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
    
    access_log /home/eero/dashboard/logs/nginx_access.log;
    error_log /home/eero/dashboard/logs/nginx_error.log;
}"""
    with open('/etc/nginx/sites-available/eero-dashboard', 'w') as f:
        f.write(content)
    if os.path.exists('/etc/nginx/sites-enabled/default'):
        os.remove('/etc/nginx/sites-enabled/default')
    if os.path.exists('/etc/nginx/sites-enabled/eero-dashboard'):
        os.remove('/etc/nginx/sites-enabled/eero-dashboard')
    os.symlink('/etc/nginx/sites-available/eero-dashboard', '/etc/nginx/sites-enabled/eero-dashboard')
    if run_command('nginx -t'):
        run_command('systemctl restart nginx')
        run_command('systemctl enable nginx')
        print_success("NGINX configured")
    else:
        print_error("NGINX configuration failed")
        sys.exit(1)

def create_systemd_service():
    print_info("Creating systemd service...")
    content = f"""[Unit]
Description=Eero Dashboard Backend v2
After=network.target

[Service]
Type=simple
User={USER}
WorkingDirectory={INSTALL_DIR}/backend
Environment="PATH={INSTALL_DIR}/venv/bin"
ExecStart={INSTALL_DIR}/venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 --timeout 120 eero_api:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    with open('/etc/systemd/system/eero-dashboard.service', 'w') as f:
        f.write(content)
    run_command('systemctl daemon-reload')
    run_command('systemctl enable eero-dashboard.service')
    run_command('systemctl start eero-dashboard.service')
    print_success("Systemd service created")

def create_kiosk_mode():
    print_info("Setting up kiosk mode...")
    content = """#!/bin/bash
xset s off 2>/dev/null
xset -dpms 2>/dev/null
xset s noblank 2>/dev/null
unclutter -idle 0.1 2>/dev/null &
if command -v chromium-browser &> /dev/null; then
    BROWSER="chromium-browser"
elif command -v chromium &> /dev/null; then
    BROWSER="chromium"
else
    echo "No chromium browser found"
    exit 1
fi
$BROWSER --kiosk --noerrdialogs --disable-infobars --no-first-run --fast --fast-start --disable-features=TranslateUI --disk-cache-dir=/dev/null --password-store=basic http://localhost
"""
    with open(f"{INSTALL_DIR}/start_kiosk.sh", 'w') as f:
        f.write(content)
    os.chmod(f"{INSTALL_DIR}/start_kiosk.sh", 0o755)
    run_command(f'chown {USER}:{USER} {INSTALL_DIR}/start_kiosk.sh')
    autostart_dir = f'/home/{USER}/.config/autostart'
    Path(autostart_dir).mkdir(parents=True, exist_ok=True)
    desktop_content = f"""[Desktop Entry]
Type=Application
Name=Eero Dashboard v2
Exec={INSTALL_DIR}/start_kiosk.sh
X-GNOME-Autostart-enabled=true
"""
    with open(f'{autostart_dir}/dashboard.desktop', 'w') as f:
        f.write(desktop_content)
    run_command(f'chown -R {USER}:{USER} /home/{USER}/.config')
    print_success("Kiosk mode configured")

def create_auth_helper():
    print_info("Creating authentication helper...")
    content = """#!/usr/bin/env python3
import requests
import json

def authenticate_eero():
    print("=" * 60)
    print("Eero API Authentication Setup")
    print("=" * 60)
    print()
    print("This process follows the official eero API authentication flow:")
    print("1. Generate unverified access token")
    print("2. Verify token with email code")
    print()
    
    email = input("Enter your API Development Email Address: ").strip()
    
    print("\\nStep 1: Generating unverified access token...")
    login_payload = {"login": email}
    
    try:
        response = requests.post("https://api-user.e2ro.com/2.2/pro/login", json=login_payload)
        response.raise_for_status()
        
        print(f"Response Status Code: {response.status_code}")
        response_data = response.json()
        
        if 'data' in response_data and 'user_token' in response_data['data']:
            unverified_token = response_data['data']['user_token']
            print(f"\\n✓ Unverified Access Token Generated:")
            print(f"  {unverified_token[:20]}...{unverified_token[-20:]}")
            print("\\n✓ Verification code sent to your email!")
            print(f"  Check the inbox of: {email}")
            
            code = input("\\nEnter the verification code from your email: ").strip()
            
            print("\\nStep 2: Verifying access token...")
            verify_url = "https://api-user.e2ro.com/2.2/login/verify"
            verify_payload = {"code": code}
            verify_headers = {"X-User-Token": unverified_token}
            
            verify_response = requests.post(verify_url, headers=verify_headers, data=verify_payload)
            verify_response.raise_for_status()
            
            verify_data = verify_response.json()
            
            if verify_data.get('data', {}).get('email', {}).get('verified'):
                print("\\n✓ Account Verified? True")
                print("\\n✓ Verified API Access Token:")
                print(f"  {unverified_token[:20]}...{unverified_token[-20:]}")
                
                with open('/home/eero/dashboard/.eero_token', 'w') as f:
                    f.write(unverified_token)
                
                print("\\n✓ Token saved to: /home/eero/dashboard/.eero_token")
                print("\\n✓ Authentication successful!")
                print("\\nYou can now restart the dashboard service:")
                print("  sudo systemctl restart eero-dashboard")
            else:
                print("\\n✗ Account verification failed.")
                print("Response:", json.dumps(verify_data, indent=2))
        else:
            print("\\n✗ Failed to get user token from response.")
            print("Response:", json.dumps(response_data, indent=2))
    
    except requests.exceptions.HTTPError as e:
        print(f"\\n✗ HTTP Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print("Response:", json.dumps(e.response.json(), indent=2))
            except:
                print("Response:", e.response.text)
    except Exception as e:
        print(f"\\n✗ Error: {e}")

if __name__ == "__main__":
    authenticate_eero()
"""
    with open(f"{INSTALL_DIR}/setup_eero_auth.py", 'w') as f:
        f.write(content)
    os.chmod(f"{INSTALL_DIR}/setup_eero_auth.py", 0o755)
    run_command(f'chown {USER}:{USER} {INSTALL_DIR}/setup_eero_auth.py')
    print_success("Authentication helper created")

def setup_logs():
    print_info("Configuring logs...")
    for log_file in [f"{INSTALL_DIR}/logs/backend.log", f"{INSTALL_DIR}/logs/nginx_access.log", f"{INSTALL_DIR}/logs/nginx_error.log"]:
        Path(log_file).touch()
    run_command(f'chown -R {USER}:{USER} {INSTALL_DIR}/logs')
    print_success("Logs configured")

def print_completion_message():
    print_header("Installation Complete!")
    print_success(f"Eero Dashboard v{SCRIPT_VERSION} installed successfully!")
    print()
    print_color(Colors.CYAN, "🎉 What's New in v2.0.1:")
    print_color(Colors.GREEN, "  ✓ Optimized for 1280x400 resolution (single row layout)")
    print_color(Colors.GREEN, "  ✓ Compact header design with logo and action buttons")
    print_color(Colors.GREEN, "  ✓ Device details panel (names, IPs, signal strength)")
    print_color(Colors.GREEN, "  ✓ Integrated speed test functionality")
    print_color(Colors.GREEN, "  ✓ No-scroll design - everything fits on screen")
    print_color(Colors.GREEN, "  ✓ Smart version upgrade system (v1 → v2)")
    print_color(Colors.GREEN, "  ✓ Official eero API authentication flow")
    print()
    print_info("Next steps:")
    print(f"  1. Place logo: sudo cp eero-logo.png {INSTALL_DIR}/frontend/assets/")
    print(f"  2. Authenticate: sudo -u {USER} {INSTALL_DIR}/venv/bin/python3 {INSTALL_DIR}/setup_eero_auth.py")
    print(f"  3. Restart: sudo systemctl restart eero-dashboard")
    print(f"  4. Access: http://localhost")
    print()
    print_warning("⚠️  Important: Use your API Development Email for authentication!")
    print_warning("⚠️  Don't forget to add your eero logo image!")

def main():
    os.system('clear')
    print_header(f"Eero Dashboard v2 Installer - v{SCRIPT_VERSION}")
    print_info(f"Repository: https://github.com/{GITHUB_REPO}")
    print()
    if '--no-update' not in sys.argv:
        check_for_updates()
    check_root()
    print_header("Starting Installation")
    try:
        create_user()
        update_system()
        install_dependencies()
        create_directory_structure()
        setup_python_environment()
        create_backend_api()
        create_frontend()
        configure_nginx()
        create_systemd_service()
        create_kiosk_mode()
        create_auth_helper()
        setup_logs()
        print_completion_message()
    except KeyboardInterrupt:
        print()
        print_error("Installation cancelled")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Installation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
