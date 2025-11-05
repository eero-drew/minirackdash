#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import re
import shutil
import threading
import time
import json
import requests
from pathlib import Path

SCRIPT_VERSION = "3.0.1"
GITHUB_REPO = "eero-drew/minirackdash"
GITHUB_RAW = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
SCRIPT_URL_V1 = f"{GITHUB_RAW}/init_dashboard.py"
SCRIPT_URL_V2 = f"{GITHUB_RAW}/v2/init_dashboard.py"
SCRIPT_URL_V3 = f"{GITHUB_RAW}/v3/init_dashboard.py"
INSTALL_DIR = "/home/eero/dashboard"
CONFIG_FILE = f"{INSTALL_DIR}/.config.json"
TOKEN_FILE = f"{INSTALL_DIR}/.eero_token"
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

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                print_info(f"Loaded existing configuration")
                return config
    except Exception as e:
        print_warning(f"Could not load config: {e}")
    return {}

def save_config(config):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        os.chmod(CONFIG_FILE, 0o600)
        if os.geteuid() == 0:
            import pwd
            uid = pwd.getpwnam(USER).pw_uid
            gid = pwd.getpwnam(USER).pw_gid
            os.chown(CONFIG_FILE, uid, gid)
        print_success(f"Configuration saved")
        return True
    except Exception as e:
        print_error(f"Could not save config: {e}")
        return False

def input_with_timeout(prompt, timeout, default=None):
    result = [None]
    
    def get_input():
        try:
            result[0] = input().strip()
        except:
            pass
    
    if default:
        print_color(Colors.MAGENTA, f"{prompt} [Default: {default}]")
    else:
        print_color(Colors.MAGENTA, prompt)
    
    thread = threading.Thread(target=get_input)
    thread.daemon = True
    thread.start()
    
    for i in range(timeout, 0, -1):
        if not thread.is_alive():
            break
        if default:
            print_color(Colors.YELLOW, f"  Using default in {i} seconds...        ", end='\r')
        else:
            print_color(Colors.YELLOW, f"  Waiting for input... {i}s              ", end='\r')
        time.sleep(1)
    
    print()
    
    if thread.is_alive() or result[0] is None or result[0] == '':
        if default:
            print_color(Colors.YELLOW, f"  Using default: {default}                    ")
            return default
        else:
            print_color(Colors.YELLOW, f"  No input received                           ")
            return None
    
    return result[0]

def prompt_network_id():
    print_header("Network Configuration")
    config = load_config()
    saved_network_id = config.get('network_id')
    
    if saved_network_id:
        print_info(f"Saved Network ID: {saved_network_id}")
        print_info("Press Enter to use saved ID, or enter a new one:")
    else:
        print_info("No saved Network ID found. Please enter your Eero Network ID:")
    
    timeout = 5 if saved_network_id else 30
    network_id = input_with_timeout("Network ID: ", timeout, default=saved_network_id)
    
    if not network_id:
        if saved_network_id:
            print_warning("Using saved Network ID")
            return saved_network_id
        else:
            print_error("Network ID is required!")
            sys.exit(1)
    
    if not network_id.isdigit():
        print_error("Network ID must be numeric!")
        sys.exit(1)
    
    config['network_id'] = network_id
    config['last_updated'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    save_config(config)
    print_success(f"Network ID set to: {network_id}")
    return network_id

def authenticate_eero(network_id):
    print_header("Eero API Authentication")
    
    if os.path.exists(TOKEN_FILE):
        print_info("Existing authentication token found")
        response = input_with_timeout("Do you want to re-authenticate? (yes/no): ", 5, default="no")
        if response and response.lower() not in ['yes', 'y']:
            print_info("Using existing token")
            return True
    
    print_info("This process will authenticate your Eero API access")
    print_info("You will receive a verification code via email")
    print()
    
    email = input("Enter your Eero API email address: ").strip()
    
    if not email or '@' not in email:
        print_error("Invalid email address")
        return False
    
    print_info(f"Sending verification code to: {email}")
    
    try:
        login_payload = {"login": email}
        response = requests.post("https://api-user.e2ro.com/2.2/pro/login", json=login_payload, timeout=10)
        response.raise_for_status()
        response_data = response.json()
        
        if 'data' not in response_data or 'user_token' not in response_data['data']:
            print_error("Failed to generate access token")
            return False
        
        unverified_token = response_data['data']['user_token']
        print_success("Verification code sent to your email!")
        print_info(f"Check your inbox: {email}")
        print()
        
        code = input("Enter the verification code from your email: ").strip()
        
        if not code:
            print_error("Verification code is required")
            return False
        
        print_info("Verifying access token...")
        
        verify_url = "https://api-user.e2ro.com/2.2/login/verify"
        verify_payload = {"code": code}
        verify_headers = {"X-User-Token": unverified_token}
        verify_response = requests.post(verify_url, headers=verify_headers, data=verify_payload, timeout=10)
        verify_response.raise_for_status()
        verify_data = verify_response.json()
        
        if verify_data.get('data', {}).get('email', {}).get('verified'):
            print_success("Authentication successful!")
            os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
            with open(TOKEN_FILE, 'w') as f:
                f.write(unverified_token)
            os.chmod(TOKEN_FILE, 0o600)
            
            if os.geteuid() == 0:
                import pwd
                uid = pwd.getpwnam(USER).pw_uid
                gid = pwd.getpwnam(USER).pw_gid
                os.chown(TOKEN_FILE, uid, gid)
            
            print_success(f"Token saved to: {TOKEN_FILE}")
            return True
        else:
            print_error("Account verification failed")
            return False
            
    except Exception as e:
        print_error(f"Authentication error: {e}")
        return False

def check_for_updates():
    print_header("Version Check")
    current_major = get_major_version(SCRIPT_VERSION)
    print_info(f"Current Version: v{SCRIPT_VERSION}")
    print_info("Checking for updates from GitHub...")
    
    try:
        if current_major == 3:
            try:
                with urllib.request.urlopen(SCRIPT_URL_V3, timeout=10) as response:
                    latest_v3_script = response.read().decode('utf-8')
                latest_v3_version = extract_version_from_script(latest_v3_script)
            except:
                latest_v3_version = None
                latest_v3_script = None
            
            if latest_v3_version:
                print_info(f"Latest v3 Version: v{latest_v3_version}")
                comparison = compare_versions(latest_v3_version, SCRIPT_VERSION)
                
                if comparison == 0:
                    print_success("You are running the latest v3 version!")
                    return False
                elif comparison > 0:
                    print_warning(f"New v3 version available: v{latest_v3_version}")
                    current_script = os.path.abspath(__file__)
                    backup_script = f"{current_script}.backup"
                    shutil.copy2(current_script, backup_script)
                    with open(current_script, 'w') as f:
                        f.write(latest_v3_script)
                    os.chmod(current_script, 0o755)
                    print_success("Script updated successfully!")
                    time.sleep(1)
                    os.execv(sys.executable, [sys.executable, current_script] + sys.argv[1:])
    except Exception as e:
        print_warning(f"Could not check for updates: {e}")
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
    except:
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
    run_command('apt-get update', timeout=120, show_output=True)
    run_command('DEBIAN_FRONTEND=noninteractive apt-get upgrade -y', timeout=600, show_output=True)

def install_dependencies():
    print_header("Installing Dependencies")
    packages = 'python3 python3-pip python3-venv nginx git curl speedtest-cli chromium-browser unclutter x11-xserver-utils xdotool'
    run_command(f"DEBIAN_FRONTEND=noninteractive apt-get install -y {packages}", timeout=600, show_output=True)
    print_success("Dependencies installed")

def create_directory_structure():
    for directory in [f"{INSTALL_DIR}/backend", f"{INSTALL_DIR}/frontend", f"{INSTALL_DIR}/frontend/assets", f"{INSTALL_DIR}/logs"]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    run_command(f'chown -R {USER}:{USER} /home/eero')

def setup_python_environment():
    venv_path = f"{INSTALL_DIR}/venv"
    run_command(f'sudo -u {USER} python3 -m venv {venv_path}', timeout=120)
    run_command(f'sudo -u {USER} {venv_path}/bin/pip install --quiet flask flask-cors requests gunicorn speedtest-cli', timeout=300)
    print_success("Python environment ready")
def create_backend_api(network_id):
    print_info("Creating backend API...")
    backend_code = """#!/usr/bin/env python3
import os
import sys
import requests
import speedtest
import threading
import subprocess
import urllib.request
import re
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(
    filename='/home/eero/dashboard/logs/backend.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

NETWORK_ID = "NETWORK_ID_PLACEHOLDER"
EERO_API_BASE = "https://api-user.e2ro.com/2.2"
API_TOKEN_FILE = "/home/eero/dashboard/.eero_token"
GITHUB_REPO = "GITHUB_REPO_PLACEHOLDER"
GITHUB_RAW = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
SCRIPT_URL_V3 = f"{GITHUB_RAW}/v3/init_dashboard.py"

class EeroAPI:
    def __init__(self):
        self.session = requests.Session()
        self.api_token = self.load_token()
    
    def load_token(self):
        try:
            if os.path.exists(API_TOKEN_FILE):
                with open(API_TOKEN_FILE, 'r') as f:
                    token = f.read().strip()
                    logging.info(f"Loaded API token: {token[:10]}...")
                    return token
        except Exception as e:
            logging.error(f"Error loading API token: {e}")
        return None
    
    def get_headers(self):
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Eero-Dashboard/3.0'
        }
        if self.api_token:
            headers['X-User-Token'] = self.api_token
        return headers
    
    def get_all_devices(self):
        try:
            url = f"{EERO_API_BASE}/networks/{NETWORK_ID}/devices"
            response = self.session.get(url, headers=self.get_headers(), timeout=10)
            response.raise_for_status()
            devices_data = response.json()
            
            if 'data' in devices_data:
                if isinstance(devices_data['data'], list):
                    return devices_data['data']
                elif isinstance(devices_data['data'], dict) and 'devices' in devices_data['data']:
                    return devices_data['data']['devices']
            return []
        except Exception as e:
            logging.error(f"Error fetching devices: {e}")
            return []

def safe_str(value, default=''):
    return default if value is None else str(value)

def safe_lower(value, default=''):
    return default if value is None else str(value).lower()

def categorize_device_os(device):
    manufacturer = safe_lower(device.get('manufacturer'), '')
    device_type = safe_lower(device.get('device_type'), '')
    hostname = safe_lower(device.get('hostname'), '')
    model_name = safe_lower(device.get('model_name'), '')
    display_name = safe_lower(device.get('display_name'), '')
    all_text = f"{manufacturer} {device_type} {hostname} {model_name} {display_name}"
    
    apple_keywords = ['apple', 'iphone', 'ipad', 'ipod', 'mac', 'macbook', 'airpods', 'apple watch', 'ios']
    for keyword in apple_keywords:
        if keyword in all_text:
            return 'iOS'
    
    android_keywords = ['android', 'samsung', 'google', 'pixel', 'huawei', 'xiaomi', 'oppo', 'lg', 'motorola', 'sony', 'oneplus']
    for keyword in android_keywords:
        if keyword in all_text:
            return 'Android'
    
    windows_keywords = ['windows', 'microsoft', 'dell', 'hp', 'lenovo', 'asus', 'acer', 'surface', 'pc', 'laptop']
    for keyword in windows_keywords:
        if keyword in all_text:
            return 'Windows'
    
    return 'Other'

def estimate_signal_from_bars(score_bars):
    score_map = {5: -45, 4: -55, 3: -65, 2: -75, 1: -85, 0: -90}
    return score_map.get(score_bars, -90)

def get_signal_quality(score_bars):
    if score_bars is None:
        return 'Unknown'
    try:
        bars = int(score_bars)
        if bars >= 5: return 'Excellent'
        elif bars == 4: return 'Very Good'
        elif bars == 3: return 'Good'
        elif bars == 2: return 'Fair'
        elif bars == 1: return 'Poor'
    except:
        pass
    return 'Unknown'

def convert_signal_dbm_to_percent(signal_dbm_str):
    try:
        if not signal_dbm_str or signal_dbm_str == 'N/A':
            return 0
        signal_dbm = float(str(signal_dbm_str).replace(' dBm', '').strip())
        if signal_dbm >= -50: return 100
        elif signal_dbm <= -100: return 0
        else: return int(2 * (signal_dbm + 100))
    except:
        return 0

def parse_frequency(interface):
    try:
        if interface is None:
            return 'N/A', 'Unknown'
        freq = interface.get('frequency')
        if freq is None or freq == 'N/A' or freq == '':
            return 'N/A', 'Unknown'
        freq_val = float(freq)
        if 2.4 <= freq_val < 2.5: band = '2.4GHz'
        elif 5.0 <= freq_val < 6.0: band = '5GHz'
        elif 6.0 <= freq_val < 7.0: band = '6GHz'
        else: band = 'Unknown'
        return f"{freq} GHz", band
    except:
        return 'N/A', 'Unknown'

def extract_version_from_script(script_content):
    match = re.search(r'SCRIPT_VERSION\\s*=\\s*["\']([^"\']+)["\']', script_content)
    return match.group(1) if match else None

def compare_versions(v1, v2):
    parts1 = [int(x) for x in v1.split('.')]
    parts2 = [int(x) for x in v2.split('.')]
    for i in range(max(len(parts1), len(parts2))):
        p1 = parts1[i] if i < len(parts1) else 0
        p2 = parts2[i] if i < len(parts2) else 0
        if p1 > p2: return 1
        elif p1 < p2: return -1
    return 0

eero_api = EeroAPI()
data_cache = {
    'connected_users': [],
    'device_os': {},
    'frequency_distribution': {},
    'signal_strength_avg': [],
    'devices': [],
    'last_update': None,
    'speedtest_running': False,
    'speedtest_result': None
}

def update_cache():
    global data_cache
    try:
        all_devices = eero_api.get_all_devices()
        if not all_devices:
            return
        
        wireless_connected = []
        for device in all_devices:
            is_connected = device.get('connected', False)
            connection_type = safe_lower(device.get('connection_type'), '')
            is_wireless = device.get('wireless', False)
            if is_connected and (connection_type == 'wireless' or is_wireless):
                wireless_connected.append(device)
        
        current_time = datetime.now()
        data_cache['connected_users'].append({
            'timestamp': current_time.isoformat(),
            'count': len(wireless_connected)
        })
        
        two_hours_ago = current_time - timedelta(hours=2)
        data_cache['connected_users'] = [
            entry for entry in data_cache['connected_users']
            if datetime.fromisoformat(entry['timestamp']) > two_hours_ago
        ]
        
        device_os = {'iOS': 0, 'Android': 0, 'Windows': 0, 'Other': 0}
        frequency_dist = {'2.4GHz': 0, '5GHz': 0, '6GHz': 0, 'Unknown': 0}
        signal_strengths = []
        device_list = []
        
        for device in wireless_connected:
            os_type = categorize_device_os(device)
            device_os[os_type] += 1
            
            connectivity = device.get('connectivity', {}) or {}
            interface = device.get('interface', {}) or {}
            
            freq_display, freq_band = parse_frequency(interface)
            if freq_band in frequency_dist:
                frequency_dist[freq_band] += 1
            
            signal_avg_dbm = connectivity.get('signal_avg')
            score_bars = connectivity.get('score_bars', 0)
            
            if signal_avg_dbm is None and score_bars:
                signal_avg_dbm = estimate_signal_from_bars(score_bars)
            
            signal_percent = convert_signal_dbm_to_percent(signal_avg_dbm)
            
            if signal_avg_dbm is not None:
                try:
                    signal_float = float(signal_avg_dbm) if isinstance(signal_avg_dbm, (int, float)) else float(str(signal_avg_dbm).replace(' dBm', '').strip())
                    signal_strengths.append(signal_float)
                except:
                    pass
            
            device_name = device.get('nickname') or device.get('hostname') or device.get('display_name') or 'Unknown Device'
            
            device_info = {
                'name': safe_str(device_name),
                'ip': ', '.join(device.get('ips', [])) if device.get('ips') else 'N/A',
                'mac': safe_str(device.get('mac'), 'N/A'),
                'manufacturer': safe_str(device.get('manufacturer'), 'Unknown'),
                'signal_avg': signal_percent,
                'signal_avg_dbm': f"{signal_avg_dbm} dBm" if signal_avg_dbm else 'N/A',
                'score_bars': score_bars,
                'signal_quality': get_signal_quality(score_bars),
                'device_os': os_type,
                'frequency': freq_display,
                'frequency_band': freq_band
            }
            device_list.append(device_info)
        
        data_cache['device_os'] = device_os
        data_cache['frequency_distribution'] = frequency_dist
        data_cache['devices'] = sorted(device_list, key=lambda x: x['name'].lower())
        
        if signal_strengths:
            avg_signal = sum(signal_strengths) / len(signal_strengths)
            data_cache['signal_strength_avg'].append({
                'timestamp': current_time.isoformat(),
                'avg_dbm': round(avg_signal, 2)
            })
            data_cache['signal_strength_avg'] = [
                entry for entry in data_cache['signal_strength_avg']
                if datetime.fromisoformat(entry['timestamp']) > two_hours_ago
            ]
        
        data_cache['last_update'] = current_time.isoformat()
    except Exception as e:
        logging.error(f"Error updating cache: {e}")

def run_speedtest():
    global data_cache
    try:
        data_cache['speedtest_running'] = True
        st = speedtest.Speedtest()
        st.get_best_server()
        data_cache['speedtest_result'] = {
            'download': round(st.download() / 1_000_000, 2),
            'upload': round(st.upload() / 1_000_000, 2),
            'ping': round(st.results.ping, 2),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        data_cache['speedtest_result'] = {'error': str(e)}
    finally:
        data_cache['speedtest_running'] = False

@app.route('/api/dashboard')
def get_dashboard_data():
    update_cache()
    return jsonify(data_cache)

@app.route('/api/devices')
def get_devices():
    return jsonify({'devices': data_cache.get('devices', []), 'count': len(data_cache.get('devices', []))})

@app.route('/api/speedtest/start', methods=['POST'])
def start_speedtest():
    if data_cache['speedtest_running']:
        return jsonify({'status': 'running'}), 409
    thread = threading.Thread(target=run_speedtest)
    thread.daemon = True
    thread.start()
    return jsonify({'status': 'started'})

@app.route('/api/speedtest/status')
def get_speedtest_status():
    return jsonify({'running': data_cache['speedtest_running'], 'result': data_cache['speedtest_result']})

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/api/version')
def get_version():
    return jsonify({'version': '3.0.1', 'name': 'Eero Dashboard', 'network_id': NETWORK_ID})

@app.route('/api/admin/check-update')
def check_update():
    try:
        with urllib.request.urlopen(SCRIPT_URL_V3, timeout=10) as response:
            latest_script = response.read().decode('utf-8')
        latest_version = extract_version_from_script(latest_script)
        current_version = '3.0.1'
        if latest_version:
            update_available = compare_versions(latest_version, current_version) > 0
        else:
            latest_version = current_version
            update_available = False
        return jsonify({'current_version': current_version, 'latest_version': latest_version, 'update_available': update_available})
    except Exception as e:
        return jsonify({'current_version': '3.0.1', 'latest_version': '3.0.1', 'update_available': False, 'error': str(e)})

@app.route('/api/admin/update', methods=['POST'])
def update_system():
    try:
        with urllib.request.urlopen(SCRIPT_URL_V3, timeout=10) as response:
            latest_script = response.read().decode('utf-8')
        latest_version = extract_version_from_script(latest_script)
        if not latest_version or compare_versions(latest_version, '3.0.1') <= 0:
            return jsonify({'success': False, 'message': 'Already running latest version'})
        script_path = '/root/init_dashboard.py'
        if not os.path.exists(script_path):
            script_path = os.path.abspath(sys.argv[0])
        with open(f"{script_path}.backup", 'w') as f:
            with open(script_path, 'r') as orig:
                f.write(orig.read())
        with open(script_path, 'w') as f:
            f.write(latest_script)
        os.chmod(script_path, 0o755)
        subprocess.Popen(['/usr/bin/sudo', '/usr/bin/python3', script_path, '--no-update'])
        return jsonify({'success': True, 'message': f'Updated to v{latest_version}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Update failed: {str(e)}'}), 500

@app.route('/api/admin/restart', methods=['POST'])
def restart_service():
    try:
        result = subprocess.run(['sudo', 'systemctl', 'restart', 'eero-dashboard'], capture_output=True, timeout=10)
        if result.returncode == 0:
            return jsonify({'success': True, 'message': 'Service restarted'})
        return jsonify({'success': False, 'message': 'Restart failed'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/reboot', methods=['POST'])
def reboot_system():
    try:
        subprocess.Popen(['sudo', 'reboot'])
        return jsonify({'success': True, 'message': 'System rebooting'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    logging.info("Starting Eero Dashboard Backend v3.0.1")
    update_cache()
    app.run(host='127.0.0.1', port=5000, debug=False)
"""
    backend_code = backend_code.replace('NETWORK_ID_PLACEHOLDER', network_id)
    backend_code = backend_code.replace('GITHUB_REPO_PLACEHOLDER', GITHUB_REPO)
    with open(f"{INSTALL_DIR}/backend/eero_api.py", 'w') as f:
        f.write(backend_code)
    os.chmod(f"{INSTALL_DIR}/backend/eero_api.py", 0o755)
    run_command(f'chown {USER}:{USER} {INSTALL_DIR}/backend/eero_api.py')
    print_success("Backend API created")

def create_frontend():
    print_info("Creating frontend dashboard...")
    # Due to size, I'm using a compact version - you can expand styles as needed
    html_content = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Eero Dashboard v3</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>*{margin:0;padding:0;box-sizing:border-box}body{background:linear-gradient(135deg,#001a33 0%,#003366 100%);font-family:'Segoe UI',sans-serif;color:#fff;overflow:hidden;height:100vh}.header{background:rgba(0,20,40,.9);padding:8px 20px;display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid rgba(77,166,255,.3)}.logo-container{display:flex;align-items:center;gap:10px}.logo{height:30px}.header-title{font-size:18px;font-weight:600;color:#4da6ff}.header-actions{display:flex;gap:10px;align-items:center}.header-btn{padding:6px 12px;background:rgba(77,166,255,.2);border:2px solid #4da6ff;border-radius:6px;color:#fff;cursor:pointer;display:flex;align-items:center;gap:6px;font-size:12px;transition:all .3s}.header-btn:hover{background:rgba(77,166,255,.4);transform:translateY(-2px)}.header-btn:disabled{opacity:.5;cursor:not-allowed}.status-indicator{display:flex;align-items:center;gap:6px;padding:6px 12px;background:rgba(0,0,0,.3);border-radius:15px;font-size:11px}.status-dot{width:8px;height:8px;border-radius:50%;background:#4CAF50;animation:pulse 2s infinite}@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}.pi-icon{position:fixed;bottom:20px;right:20px;width:60px;height:60px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 4px 20px rgba(102,126,234,.4);transition:all .3s;z-index:999;font-size:28px;font-weight:700;color:#fff;border:3px solid rgba(255,255,255,.3)}.pi-icon:hover{transform:scale(1.1) rotate(180deg)}.pixelate{filter:blur(5px)}.dashboard-container{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:10px;padding:10px;height:calc(100vh - 60px);transition:filter .3s}.chart-card{background:rgba(0,40,80,.7);border-radius:10px;padding:10px;box-shadow:0 8px 32px rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.1);display:flex;flex-direction:column}.chart-title{font-size:14px;font-weight:600;margin-bottom:8px;text-align:center;color:#4da6ff;text-transform:uppercase}.chart-subtitle{font-size:11px;text-align:center;color:rgba(255,255,255,.6);margin-bottom:8px}.chart-container{flex:1;position:relative;min-height:0}canvas{max-width:100%;max-height:100%}.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.8);z-index:1000;justify-content:center;align-items:center}.modal.active{display:flex}.modal-content{background:linear-gradient(135deg,#001a33 0%,#003366 100%);border-radius:15px;padding:30px;max-width:900px;width:90%;max-height:80vh;overflow-y:auto;border:2px solid rgba(77,166,255,.3)}.gibson-modal .modal-content{max-width:600px;background:linear-gradient(135deg,#0a0e27 0%,#1a1a2e 100%);border:2px solid #667eea}.gibson-title{font-size:32px;color:#667eea;text-align:center;margin-bottom:10px;font-weight:700;text-shadow:0 0 20px rgba(102,126,234,.5);letter-spacing:2px}.gibson-subtitle{text-align:center;color:rgba(255,255,255,.6);font-size:12px;margin-bottom:30px;font-style:italic}.version-info{background:rgba(0,0,0,.3);padding:20px;border-radius:10px;margin-bottom:20px;border:1px solid rgba(102,126,234,.3)}.version-row{display:flex;justify-content:space-between;margin-bottom:10px;font-size:14px}.version-label{color:#667eea;font-weight:600}.version-value{color:#fff;font-family:'Courier New',monospace}.version-status{text-align:center;padding:10px;border-radius:8px;margin-top:15px;font-weight:600}.version-status.up-to-date{background:rgba(76,175,80,.2);color:#4CAF50;border:1px solid #4CAF50}.version-status.update-available{background:rgba(255,193,7,.2);color:#ffc107;border:1px solid #ffc107}.version-status.checking{background:rgba(77,166,255,.2);color:#4da6ff;border:1px solid #4da6ff}.admin-actions{display:grid;gap:15px;margin-top:20px}.admin-btn{padding:15px 20px;border:none;border-radius:10px;font-size:16px;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:10px;transition:all .3s}.admin-btn:hover{transform:translateY(-2px)}.admin-btn:disabled{opacity:.5;cursor:not-allowed;transform:none}.admin-btn.update{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff}.admin-btn.restart{background:linear-gradient(135deg,#f093fb 0%,#f5576c 100%);color:#fff}.admin-btn.reboot{background:linear-gradient(135deg,#fa709a 0%,#fee140 100%);color:#1a1a2e}.modal-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding-bottom:15px;border-bottom:2px solid rgba(77,166,255,.3)}.modal-title{font-size:24px;color:#4da6ff}.close-btn{background:0 0;border:none;color:#fff;font-size:28px;cursor:pointer}.close-btn:hover{color:#ff6b6b}.device-table{width:100%;border-collapse:collapse;margin-top:15px}.device-table th{background:rgba(77,166,255,.2);padding:12px;text-align:left;font-weight:600;color:#4da6ff;border-bottom:2px solid rgba(77,166,255,.3)}.device-table td{padding:12px;border-bottom:1px solid rgba(255,255,255,.1)}.device-table tr:hover{background:rgba(77,166,255,.1)}.signal-bar{width:100px;height:8px;background:rgba(255,255,255,.1);border-radius:4px;overflow:hidden}.signal-fill{height:100%;border-radius:4px}.signal-excellent{background:#4CAF50}.signal-good{background:#8BC34A}.signal-fair{background:#FFC107}.signal-poor{background:#FF9800}.signal-weak{background:#F44336}.speedtest-container{text-align:center;padding:20px}.speedtest-results{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:30px}.speedtest-metric{background:rgba(0,40,80,.5);padding:25px;border-radius:10px;border:1px solid rgba(77,166,255,.3)}.speedtest-metric-label{font-size:14px;color:#4da6ff;margin-bottom:10px}.speedtest-metric-value{font-size:36px;font-weight:600;color:#fff}.speedtest-metric-unit{font-size:14px;color:rgba(255,255,255,.7)}.spinner{border:4px solid rgba(77,166,255,.3);border-top:4px solid #4da6ff;border-radius:50%;width:50px;height:50px;animation:spin 1s linear infinite;margin:20px auto}@keyframes spin{0%{transform:rotate(0)}100%{transform:rotate(360deg)}}.device-count{font-size:16px;color:rgba(255,255,255,.8);margin-bottom:15px}.action-message{padding:15px;border-radius:8px;margin-top:15px;text-align:center;font-weight:600}.action-message.success{background:rgba(76,175,80,.2);color:#4CAF50;border:1px solid #4CAF50}.action-message.error{background:rgba(244,67,54,.2);color:#f44336;border:1px solid #f44336}.action-message.info{background:rgba(77,166,255,.2);color:#4da6ff;border:1px solid #4da6ff}</style></head><body>
<div class="header"><div class="logo-container"><img src="/assets/eero-logo.png" alt="Eero" class="logo" onerror="this.style.display='none'"><div class="header-title">Network Dashboard v3.0.1</div></div><div class="header-actions"><div class="status-indicator"><div class="status-dot"></div><span id="lastUpdate">Loading...</span></div><button class="header-btn" id="deviceDetailsBtn"><i class="fas fa-list"></i><span>Devices</span></button><button class="header-btn" id="speedTestBtn"><i class="fas fa-gauge-high"></i><span>Speed Test</span></button></div></div>
<div class="dashboard-container" id="dashboardContainer"><div class="chart-card"><div class="chart-title">Connected Users</div><div class="chart-subtitle">Wireless devices over time</div><div class="chart-container"><canvas id="usersChart"></canvas></div></div><div class="chart-card"><div class="chart-title">Device OS</div><div class="chart-subtitle" id="deviceOsSubtitle">Loading...</div><div class="chart-container"><canvas id="deviceOSChart"></canvas></div></div><div class="chart-card"><div class="chart-title">Frequency Distribution</div><div class="chart-subtitle" id="frequencySubtitle">Loading...</div><div class="chart-container"><canvas id="frequencyChart"></canvas></div></div><div class="chart-card"><div class="chart-title">Average Signal Strength</div><div class="chart-subtitle">Network-wide average (dBm)</div><div class="chart-container"><canvas id="signalStrengthChart"></canvas></div></div></div>
<div class="pi-icon" id="piIcon" title="System Admin">π</div>
<div class="modal gibson-modal" id="gibsonModal"><div class="modal-content"><div class="modal-header"><h2 class="gibson-title">THE GIBSON</h2><button class="close-btn" id="closeGibsonModal">&times;</button></div><div class="gibson-subtitle">"Hack the Planet!"</div><div class="version-info"><div class="version-row"><span class="version-label">Current Version:</span><span class="version-value" id="currentVersion">Loading...</span></div><div class="version-row"><span class="version-label">Latest Version:</span><span class="version-value" id="latestVersion">Checking...</span></div><div class="version-row"><span class="version-label">Network ID:</span><span class="version-value" id="networkId">Loading...</span></div><div class="version-status checking" id="versionStatus"><i class="fas fa-spinner fa-spin"></i> Checking for updates...</div></div><div class="admin-actions"><button class="admin-btn update" id="updateBtn" disabled><i class="fas fa-download"></i><span>Update to Latest Version</span></button><button class="admin-btn restart" id="restartBtn"><i class="fas fa-rotate-right"></i><span>Restart Dashboard Service</span></button><button class="admin-btn reboot" id="rebootBtn"><i class="fas fa-power-off"></i><span>Reboot System</span></button></div><div id="actionMessage"></div></div></div>
<div class="modal" id="deviceModal"><div class="modal-content"><div class="modal-header"><h2 class="modal-title">Connected Wireless Devices</h2><button class="close-btn" id="closeDeviceModal">&times;</button></div><div class="device-count" id="deviceCount">Loading...</div><table class="device-table"><thead><tr><th>Device Name</th><th>OS</th><th>Frequency</th><th>IP Address</th><th>Manufacturer</th><th>Signal Quality</th></tr></thead><tbody id="deviceTableBody"><tr><td colspan="6" style="text-align:center">Loading devices...</td></tr></tbody></table></div></div>
<div class="modal" id="speedTestModal"><div class="modal-content"><div class="modal-header"><h2 class="modal-title">Internet Speed Test</h2><button class="close-btn" id="closeSpeedTestModal">&times;</button></div><div class="speedtest-container" id="speedTestContainer"><p>Click "Run Test" to measure your internet speed</p><button class="header-btn" id="runSpeedTest" style="margin:20px auto"><i class="fas fa-play"></i><span>Run Test</span></button></div></div></div>
<script>
let charts={users:null,deviceOS:null,frequency:null,signalStrength:null};let versionData={};const chartColors={primary:'#4da6ff',success:'#51cf66',warning:'#ffd43b',info:'#74c0fc',purple:'#b197fc',orange:'#ff922b'};const mainChartOptions={responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#fff',font:{size:10}}}},scales:{y:{ticks:{color:'#fff',font:{size:9}},grid:{color:'rgba(255,255,255,0.1)'}},x:{ticks:{color:'#fff',font:{size:9}},grid:{color:'rgba(255,255,255,0.1)'}}}};
function initCharts(){const usersCtx=document.getElementById('usersChart').getContext('2d');charts.users=new Chart(usersCtx,{type:'line',data:{labels:[],datasets:[{label:'Connected Wireless',data:[],borderColor:chartColors.primary,backgroundColor:'rgba(77,166,255,0.1)',tension:0.4,fill:true,borderWidth:2}]},options:mainChartOptions});const deviceOSCtx=document.getElementById('deviceOSChart').getContext('2d');charts.deviceOS=new Chart(deviceOSCtx,{type:'doughnut',data:{labels:['iOS','Android','Windows','Other'],datasets:[{data:[0,0,0,0],backgroundColor:[chartColors.primary,chartColors.success,chartColors.info,chartColors.warning],borderWidth:2,borderColor:'#001a33'}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom',labels:{color:'#fff',font:{size:10},padding:8}}}}});const frequencyCtx=document.getElementById('frequencyChart').getContext('2d');charts.frequency=new Chart(frequencyCtx,{type:'doughnut',data:{labels:['2.4 GHz','5 GHz','6 GHz'],datasets:[{data:[0,0,0],backgroundColor:[chartColors.orange,chartColors.primary,chartColors.purple],borderWidth:2,borderColor:'#001a33'}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom',labels:{color:'#fff',font:{size:10},padding:8}}}}});const signalStrengthCtx=document.getElementById('signalStrengthChart').getContext('2d');charts.signalStrength=new Chart(signalStrengthCtx,{type:'line',data:{labels:[],datasets:[{label:'Avg Signal (dBm)',data:[],borderColor:chartColors.success,backgroundColor:'rgba(81,207,102,0.1)',tension:0.4,fill:true,borderWidth:2}]},options:mainChartOptions});}
async function updateDashboard(){try{const response=await fetch('/api/dashboard');const data=await response.json();const userLabels=data.connected_users.map(entry=>{const date=new Date(entry.timestamp);return date.toLocaleTimeString();});const userCounts=data.connected_users.map(entry=>entry.count);charts.users.data.labels=userLabels;charts.users.data.datasets[0].data=userCounts;charts.users.update();const deviceOS=data.device_os||{iOS:0,Android:0,Windows:0,Other:0};const totalDevices=Object.values(deviceOS).reduce((a,b)=>a+b,0);charts.deviceOS.data.datasets[0].data=[deviceOS.iOS||0,deviceOS.Android||0,deviceOS.Windows||0,deviceOS.Other||0];charts.deviceOS.update();document.getElementById('deviceOsSubtitle').textContent=`${totalDevices} devices`;const freqDist=data.frequency_distribution||{'2.4GHz':0,'5GHz':0,'6GHz':0};const totalFreq=(freqDist['2.4GHz']||0)+(freqDist['5GHz']||0)+(freqDist['6GHz']||0);charts.frequency.data.datasets[0].data=[freqDist['2.4GHz']||0,freqDist['5GHz']||0,freqDist['6GHz']||0];charts.frequency.update();document.getElementById('frequencySubtitle').textContent=`${totalFreq} devices`;const signalLabels=data.signal_strength_avg.map(entry=>{const date=new Date(entry.timestamp);return date.toLocaleTimeString();});const signalData=data.signal_strength_avg.map(entry=>entry.avg_dbm);charts.signalStrength.data.labels=signalLabels;charts.signalStrength.data.datasets[0].data=signalData;charts.signalStrength.update();const lastUpdate=new Date(data.last_update);document.getElementById('lastUpdate').textContent=`Updated: ${lastUpdate.toLocaleTimeString()}`;}catch(error){console.error('Error updating dashboard:',error);}}
function getSignalClass(strength){if(strength>=80)return 'signal-excellent';if(strength>=60)return 'signal-good';if(strength>=40)return 'signal-fair';if(strength>=20)return 'signal-poor';return 'signal-weak';}
async function loadDevices(){try{const response=await fetch('/api/devices');const data=await response.json();document.getElementById('deviceCount').textContent=`Total Connected Wireless: ${data.count} devices`;const tbody=document.getElementById('deviceTableBody');if(data.devices.length===0){tbody.innerHTML='<tr><td colspan="6" style="text-align:center">No wireless devices connected</td></tr>';return;}tbody.innerHTML=data.devices.map(device=>`<tr><td><strong>${device.name}</strong></td><td>${device.device_os}</td><td>${device.frequency}</td><td>${device.ip}</td><td>${device.manufacturer}</td><td><div style="display:flex;align-items:center;gap:10px"><div class="signal-bar"><div class="signal-fill ${getSignalClass(device.signal_avg)}" style="width:${device.signal_avg}%"></div></div><small style="color:rgba(255,255,255,0.6)">${device.signal_quality} (${device.signal_avg_dbm})</small></div></td></tr>`).join('');}catch(error){console.error('Error loading devices:',error);}}
async function runSpeedTest(){const btn=document.getElementById('runSpeedTest');const container=document.getElementById('speedTestContainer');btn.classList.add('running');btn.innerHTML='<i class="fas fa-spinner fa-spin"></i><span>Running...</span>';btn.disabled=true;container.innerHTML='<div class="spinner"></div><p>Testing your internet speed...</p><p style="font-size:12px;color:rgba(255,255,255,0.6)">This may take 30-60 seconds</p>';try{await fetch('/api/speedtest/start',{method:'POST'});const checkStatus=setInterval(async()=>{const response=await fetch('/api/speedtest/status');const data=await response.json();if(!data.running&&data.result){clearInterval(checkStatus);if(data.result.error){container.innerHTML=`<p style="color:#ff6b6b">Error: ${data.result.error}</p>`;}else{container.innerHTML=`<div class="speedtest-results"><div class="speedtest-metric"><div class="speedtest-metric-label">Download</div><div class="speedtest-metric-value">${data.result.download}</div><div class="speedtest-metric-unit">Mbps</div></div><div class="speedtest-metric"><div class="speedtest-metric-label">Upload</div><div class="speedtest-metric-value">${data.result.upload}</div><div class="speedtest-metric-unit">Mbps</div></div><div class="speedtest-metric"><div class="speedtest-metric-label">Ping</div><div class="speedtest-metric-value">${data.result.ping}</div><div class="speedtest-metric-unit">ms</div></div></div><button class="header-btn" onclick="runSpeedTest()" style="margin:20px auto"><i class="fas fa-redo"></i><span>Test Again</span></button>`;}btn.classList.remove('running');btn.innerHTML='<i class="fas fa-play"></i><span>Run Test</span>';btn.disabled=false;}},2000);}catch(error){console.error('Speed test error:',error);container.innerHTML=`<p style="color:#ff6b6b">Error: ${error.message}</p>`;btn.classList.remove('running');btn.innerHTML='<i class="fas fa-play"></i><span>Run Test</span>';btn.disabled=false;}}
async function checkVersion(){try{const response=await fetch('/api/version');const data=await response.json();versionData.current=data.version;document.getElementById('currentVersion').textContent=`v${data.version}`;document.getElementById('networkId').textContent=data.network_id||'N/A';const latestResponse=await fetch('/api/admin/check-update');const latestData=await latestResponse.json();versionData.latest=latestData.latest_version;versionData.updateAvailable=latestData.update_available;document.getElementById('latestVersion').textContent=`v${latestData.latest_version}`;const statusDiv=document.getElementById('versionStatus');const updateBtn=document.getElementById('updateBtn');if(latestData.update_available){statusDiv.className='version-status update-available';statusDiv.innerHTML='<i class="fas fa-exclamation-circle"></i> Update Available!';updateBtn.disabled=false;}else{statusDiv.className='version-status up-to-date';statusDiv.innerHTML='<i class="fas fa-check-circle"></i> Up to Date';updateBtn.disabled=true;}}catch(error){console.error('Error checking version:',error);}}
async function updateSystem(){const btn=document.getElementById('updateBtn');const messageDiv=document.getElementById('actionMessage');btn.disabled=true;btn.innerHTML='<i class="fas fa-spinner fa-spin"></i><span>Updating...</span>';messageDiv.className='action-message info';messageDiv.innerHTML='<i class="fas fa-info-circle"></i> Starting update process...';try{const response=await fetch('/api/admin/update',{method:'POST'});const data=await response.json();if(data.success){messageDiv.className='action-message success';messageDiv.innerHTML='<i class="fas fa-check-circle"></i> '+data.message;setTimeout(()=>{messageDiv.innerHTML+='<br>Reloading dashboard in 5 seconds...';setTimeout(()=>location.reload(),5000);},2000);}else{messageDiv.className='action-message error';messageDiv.innerHTML='<i class="fas fa-times-circle"></i> '+data.message;btn.disabled=false;btn.innerHTML='<i class="fas fa-download"></i><span>Update to Latest Version</span>';}}catch(error){messageDiv.className='action-message error';messageDiv.innerHTML='<i class="fas fa-times-circle"></i> Update failed: '+error.message;btn.disabled=false;btn.innerHTML='<i class="fas fa-download"></i><span>Update to Latest Version</span>';}}
async function restartService(){if(!confirm('Restart the dashboard service? This will take about 10 seconds.'))return;const btn=document.getElementById('restartBtn');const messageDiv=document.getElementById('actionMessage');btn.disabled=true;btn.innerHTML='<i class="fas fa-spinner fa-spin"></i><span>Restarting...</span>';messageDiv.className='action-message info';messageDiv.innerHTML='<i class="fas fa-info-circle"></i> Restarting dashboard service...';try{const response=await fetch('/api/admin/restart',{method:'POST'});const data=await response.json();if(data.success){messageDiv.className='action-message success';messageDiv.innerHTML='<i class="fas fa-check-circle"></i> Service restarted successfully!';setTimeout(()=>{messageDiv.innerHTML+='<br>Reloading dashboard in 3 seconds...';setTimeout(()=>location.reload(),3000);},2000);}else{messageDiv.className='action-message error';messageDiv.innerHTML='<i class="fas fa-times-circle"></i> '+data.message;btn.disabled=false;btn.innerHTML='<i class="fas fa-rotate-right"></i><span>Restart Dashboard Service</span>';}}catch(error){messageDiv.className='action-message error';messageDiv.innerHTML='<i class="fas fa-times-circle"></i> Restart failed: '+error.message;btn.disabled=false;btn.innerHTML='<i class="fas fa-rotate-right"></i><span>Restart Dashboard Service</span>';}}
async function rebootSystem(){if(!confirm('REBOOT THE ENTIRE SYSTEM? This will disconnect you!'))return;if(!confirm('Are you ABSOLUTELY SURE? The system will reboot immediately!'))return;const btn=document.getElementById('rebootBtn');const messageDiv=document.getElementById('actionMessage');btn.disabled=true;btn.innerHTML='<i class="fas fa-spinner fa-spin"></i><span>Rebooting...</span>';messageDiv.className='action-message info';messageDiv.innerHTML='<i class="fas fa-info-circle"></i> System is rebooting... Please wait 30-60 seconds.';try{await fetch('/api/admin/reboot',{method:'POST'});messageDiv.className='action-message success';messageDiv.innerHTML='<i class="fas fa-power-off"></i> System is rebooting. Reconnect in about 60 seconds.';}catch(error){messageDiv.className='action-message success';messageDiv.innerHTML='<i class="fas fa-power-off"></i> System is rebooting. Reconnect in about 60 seconds.';}}
document.getElementById('piIcon').addEventListener('click',()=>{const container=document.getElementById('dashboardContainer');const header=document.querySelector('.header');const modal=document.getElementById('gibsonModal');container.classList.add('pixelate');header.classList.add('pixelate');setTimeout(()=>{modal.classList.add('active');checkVersion();},300);});document.getElementById('closeGibsonModal').addEventListener('click',()=>{const container=document.getElementById('dashboardContainer');const header=document.querySelector('.header');const modal=document.getElementById('gibsonModal');modal.classList.remove('active');setTimeout(()=>{container.classList.remove('pixelate');header.classList.remove('pixelate');},300);});document.getElementById('updateBtn').addEventListener('click',updateSystem);document.getElementById('restartBtn').addEventListener('click',restartService);document.getElementById('rebootBtn').addEventListener('click',rebootSystem);document.getElementById('deviceDetailsBtn').addEventListener('click',()=>{document.getElementById('deviceModal').classList.add('active');loadDevices();});document.getElementById('closeDeviceModal').addEventListener('click',()=>{document.getElementById('deviceModal').classList.remove('active');});document.getElementById('speedTestBtn').addEventListener('click',()=>{document.getElementById('speedTestModal').classList.add('active');});document.getElementById('closeSpeedTestModal').addEventListener('click',()=>{document.getElementById('speedTestModal').classList.remove('active');});document.getElementById('runSpeedTest').addEventListener('click',runSpeedTest);document.querySelectorAll('.modal').forEach(modal=>{modal.addEventListener('click',(e)=>{if(e.target===modal){modal.classList.remove('active');const container=document.getElementById('dashboardContainer');const header=document.querySelector('.header');container.classList.remove('pixelate');header.classList.remove('pixelate');}});});window.addEventListener('load',()=>{initCharts();updateDashboard();setInterval(updateDashboard,60000);});
</script></body></html>"""
    with open(f"{INSTALL_DIR}/frontend/index.html", 'w') as f:
        f.write(html_content)
    run_command(f'chown {USER}:{USER} {INSTALL_DIR}/frontend/index.html')
    print_success("Frontend created")

def configure_nginx():
    print_info("Configuring NGINX...")
    nginx_config = """server {
    listen 80 default_server;
    server_name _;
    root /home/eero/dashboard/frontend;
    index index.html;
    location / { try_files $uri $uri/ =404; }
    location /assets/ { alias /home/eero/dashboard/frontend/assets/; }
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_read_timeout 120s;
    }
}"""
    with open('/etc/nginx/sites-available/eero-dashboard', 'w') as f:
        f.write(nginx_config)
    if os.path.exists('/etc/nginx/sites-enabled/default'):
        os.remove('/etc/nginx/sites-enabled/default')
    if os.path.exists('/etc/nginx/sites-enabled/eero-dashboard'):
        os.remove('/etc/nginx/sites-enabled/eero-dashboard')
    os.symlink('/etc/nginx/sites-available/eero-dashboard', '/etc/nginx/sites-enabled/eero-dashboard')
    run_command('nginx -t')
    run_command('systemctl restart nginx')
    run_command('systemctl enable nginx')
    print_success("NGINX configured")

def create_systemd_service():
    print_info("Creating systemd service...")
    service_content = f"""[Unit]
Description=Eero Dashboard Backend v3
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
        f.write(service_content)
    run_command('systemctl daemon-reload')
    run_command('systemctl enable eero-dashboard.service')
    print_success("Systemd service created")

def start_service():
    print_info("Starting dashboard service...")
    run_command('systemctl start eero-dashboard.service')
    time.sleep(2)
    result = subprocess.run(['systemctl', 'is-active', 'eero-dashboard.service'], capture_output=True, text=True)
    if result.stdout.strip() == 'active':
        print_success("Service is running!")
    else:
        print_warning("Service may not be running correctly")

def create_kiosk_mode():
    print_info("Setting up kiosk mode...")
    kiosk_script = """#!/bin/bash
xset s off 2>/dev/null
xset -dpms 2>/dev/null
xset s noblank 2>/dev/null
unclutter -idle 0.1 2>/dev/null &
if command -v chromium-browser &> /dev/null; then
    BROWSER="chromium-browser"
elif command -v chromium &> /dev/null; then
    BROWSER="chromium"
else
    exit 1
fi
$BROWSER --kiosk --noerrdialogs --disable-infobars --no-first-run http://localhost
"""
    with open(f"{INSTALL_DIR}/start_kiosk.sh", 'w') as f:
        f.write(kiosk_script)
    os.chmod(f"{INSTALL_DIR}/start_kiosk.sh", 0o755)
    run_command(f'chown {USER}:{USER} {INSTALL_DIR}/start_kiosk.sh')
    autostart_dir = f'/home/{USER}/.config/autostart'
    Path(autostart_dir).mkdir(parents=True, exist_ok=True)
    desktop_content = f"""[Desktop Entry]
Type=Application
Name=Eero Dashboard v3
Exec={INSTALL_DIR}/start_kiosk.sh
X-GNOME-Autostart-enabled=true
"""
    with open(f'{autostart_dir}/dashboard.desktop', 'w') as f:
        f.write(desktop_content)
    run_command(f'chown -R {USER}:{USER} /home/{USER}/.config')
    print_success("Kiosk mode configured")

def setup_logs():
    for log_file in [f"{INSTALL_DIR}/logs/backend.log", f"{INSTALL_DIR}/logs/nginx_access.log", f"{INSTALL_DIR}/logs/nginx_error.log"]:
        Path(log_file).touch()
    run_command(f'chown -R {USER}:{USER} {INSTALL_DIR}/logs')
    print_success("Logs configured")

def print_completion_message():
    print_header("Installation Complete!")
    print_success(f"Eero Dashboard v{SCRIPT_VERSION} installed successfully!")
    print()
    print_color(Colors.CYAN, "🎉 What's New in v3.0.1:")
    print_color(Colors.GREEN, "  ✓ The Gibson admin panel (π icon)")
    print_color(Colors.GREEN, "  ✓ Web-based system management")
    print_color(Colors.GREEN, "  ✓ One-click updates")
    print_color(Colors.GREEN, "  ✓ Service restart from UI")
    print_color(Colors.GREEN, "  ✓ System reboot from UI")
    print()
    config = load_config()
    if config.get('network_id'):
        print_info(f"Network ID: {config['network_id']}")
    print_info(f"Dashboard: http://localhost")
    print_info(f"Click the π icon (bottom-right) for admin panel")

def main():
    os.system('clear')
    print_header(f"Eero Dashboard v3 Installer - v{SCRIPT_VERSION}")
    if '--no-update' not in sys.argv:
        check_for_updates()
    check_root()
    print_header("Starting Installation")
    try:
        create_user()
        update_system()
        install_dependencies()
        create_directory_structure()
        network_id = prompt_network_id()
        setup_python_environment()
        auth_success = authenticate_eero(network_id)
        if not auth_success:
            print_error("Authentication failed. Please run setup again.")
            sys.exit(1)
        create_backend_api(network_id)
        create_frontend()
        configure_nginx()
        create_systemd_service()
        start_service()
        create_kiosk_mode()
        setup_logs()
        print_completion_message()
    except KeyboardInterrupt:
        print()
        print_error("Installation cancelled")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Installation failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
