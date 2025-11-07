#!/usr/bin/env python3
"""
MiniRack Dashboard v4.0.1 - Complete Backend + Frontend
Single file with embedded HTML
"""
import os
import requests
import speedtest
import threading
import subprocess
import json
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging

# Configuration (replaced by installer)
NETWORK_ID = "{{NETWORK_ID}}"
USER = "{{USER}}"
INSTALL_DIR = "{{INSTALL_DIR}}"
GITHUB_REPO = "{{GITHUB_REPO}}"

# Flask app setup
app = Flask(__name__)
CORS(app)

logging.basicConfig(
    filename=f'{INSTALL_DIR}/logs/backend.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

CONFIG_FILE = f"{INSTALL_DIR}/.config.json"
EERO_API_BASE = "https://api-user.e2ro.com/2.2"
API_TOKEN_FILE = f"{INSTALL_DIR}/.eero_token"

def load_config():
    """Load configuration"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'network_id': NETWORK_ID}
    return {'network_id': NETWORK_ID}

class EeroAPI:
    def __init__(self):
        self.session = requests.Session()
        self.api_token = self.load_token()
        self.network_id = load_config().get('network_id', NETWORK_ID)
        self.token_timestamp = self.load_token_timestamp()
    
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
    
    def load_token_timestamp(self):
        """Load token timestamp"""
        try:
            token_time_file = API_TOKEN_FILE + '.timestamp'
            if os.path.exists(token_time_file):
                with open(token_time_file, 'r') as f:
                    return datetime.fromisoformat(f.read().strip())
        except:
            pass
        return None
    
    def is_token_expired(self):
        """Check if token is older than 24 hours"""
        if not self.token_timestamp:
            return True
        age = datetime.now() - self.token_timestamp
        return age > timedelta(hours=24)
    
    def get_headers(self):
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'MiniRack-Dashboard/4.0.1'
        }
        if self.api_token:
            headers['X-User-Token'] = self.api_token
        return headers
    
    def get_all_devices(self):
        """Get all devices from the network"""
        try:
            url = f"{EERO_API_BASE}/networks/{self.network_id}/devices"
            logging.debug(f"Fetching devices from: {url}")
            response = self.session.get(url, headers=self.get_headers(), timeout=10)
            response.raise_for_status()
            devices_data = response.json()
            
            if 'data' in devices_data:
                if isinstance(devices_data['data'], list):
                    all_devices = devices_data['data']
                elif isinstance(devices_data['data'], dict) and 'devices' in devices_data['data']:
                    all_devices = devices_data['data']['devices']
                else:
                    all_devices = []
            else:
                all_devices = []
            
            logging.info(f"Found {len(all_devices)} total devices")
            return all_devices
            
        except Exception as e:
            logging.error(f"Error fetching devices: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return []

def safe_str(value, default=''):
    if value is None:
        return default
    return str(value)

def safe_lower(value, default=''):
    if value is None:
        return default
    return str(value).lower()

def categorize_device_os(device):
    """Categorize device by OS"""
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
    
    if device_type:
        if 'phone' in device_type or 'mobile' in device_type:
            return 'Android'
        elif 'tablet' in device_type:
            return 'Android'
        elif 'computer' in device_type or 'laptop' in device_type:
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
        if bars >= 5:
            return 'Excellent'
        elif bars == 4:
            return 'Very Good'
        elif bars == 3:
            return 'Good'
        elif bars == 2:
            return 'Fair'
        elif bars == 1:
            return 'Poor'
        else:
            return 'Unknown'
    except:
        return 'Unknown'

def convert_signal_dbm_to_percent(signal_dbm_str):
    try:
        if not signal_dbm_str or signal_dbm_str == 'N/A' or signal_dbm_str is None:
            return 0
        signal_str = str(signal_dbm_str).replace(' dBm', '').strip()
        signal_dbm = float(signal_str)
        if signal_dbm >= -50:
            return 100
        elif signal_dbm <= -100:
            return 0
        else:
            return int(2 * (signal_dbm + 100))
    except:
        return 0

def parse_frequency(interface):
    try:
        if interface is None:
            return 'N/A', 'Unknown'
        freq = interface.get('frequency')
        if freq is None or freq == 'N/A' or freq == '' or freq == 0:
            return 'N/A', 'Unknown'
        freq_val = float(freq)
        if 2.4 <= freq_val < 2.5:
            band = '2.4GHz'
        elif 5.0 <= freq_val < 6.0:
            band = '5GHz'
        elif 6.0 <= freq_val < 7.0:
            band = '6GHz'
        else:
            band = 'Unknown'
        return f"{freq} GHz", band
    except:
        return 'N/A', 'Unknown'

eero_api = EeroAPI()
data_cache = {
    'connected_users': [],
    'device_os': {},
    'frequency_distribution': {},
    'signal_strength_avg': [],
    'devices': [],
    'last_update': None,
    'speedtest_running': False,
    'speedtest_result': None,
    'token_age_hours': None,
    'token_expired': False
}

def update_cache():
    global data_cache
    try:
        logging.info("Starting cache update...")
        
        if eero_api.token_timestamp:
            age = datetime.now() - eero_api.token_timestamp
            data_cache['token_age_hours'] = age.total_seconds() / 3600
            data_cache['token_expired'] = eero_api.is_token_expired()
        
        all_devices = eero_api.get_all_devices()
        
        if not all_devices:
            logging.warning("No devices returned from API")
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
            
            if signal_avg_dbm is None and score_bars is not None and score_bars > 0:
                signal_avg_dbm = estimate_signal_from_bars(score_bars)
            
            signal_percent = convert_signal_dbm_to_percent(signal_avg_dbm)
            
            if signal_avg_dbm is not None:
                try:
                    if isinstance(signal_avg_dbm, (int, float)):
                        signal_float = float(signal_avg_dbm)
                    else:
                        signal_str = str(signal_avg_dbm).replace(' dBm', '').strip()
                        signal_float = float(signal_str)
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
                'signal_avg_dbm': f"{signal_avg_dbm} dBm" if signal_avg_dbm is not None else 'N/A',
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
        logging.info("Cache update complete")
        
    except Exception as e:
        logging.error(f"Error updating cache: {e}")
        import traceback
        logging.error(traceback.format_exc())

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
        
        data_cache['speedtest_result'] = {
            'download': round(download_speed, 2),
            'upload': round(upload_speed, 2),
            'ping': round(ping, 2),
            'timestamp': datetime.now().isoformat()
        }
        logging.info(f"Speed test complete: {data_cache['speedtest_result']}")
    except Exception as e:
        logging.error(f"Speed test failed: {e}")
        data_cache['speedtest_result'] = {'error': str(e)}
    finally:
        data_cache['speedtest_running'] = False

# Static HTML (embedded)
HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MiniRack Dashboard v4.0.1 - The Gibson</title>
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
        
        .pixelate {
            filter: blur(0px);
            transition: filter 0.3s ease-out;
        }
        
        .pixelate.active {
            filter: blur(8px) contrast(150%) brightness(80%);
        }
        
        .gibson-icon {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 30px;
            height: 30px;
            background: rgba(77, 166, 255, 0.9);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 999;
            box-shadow: 0 4px 15px rgba(77, 166, 255, 0.5);
            transition: all 0.3s ease;
            font-size: 18px;
            font-weight: bold;
            color: #ffffff;
            border: 2px solid rgba(255, 255, 255, 0.3);
        }
        
        .gibson-icon:hover {
            transform: scale(1.1) rotate(180deg);
            box-shadow: 0 6px 20px rgba(77, 166, 255, 0.8);
        }
        
        .token-warning {
            position: fixed;
            top: 60px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(255, 152, 0, 0.95);
            color: #000;
            padding: 12px 24px;
            border-radius: 8px;
            z-index: 998;
            display: none;
            align-items: center;
            gap: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        
        .token-warning.show { display: flex; }
        
        .token-warning-btn {
            background: #000;
            color: #fff;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
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
        }
        
        .chart-subtitle {
            font-size: 11px;
            text-align: center;
            color: rgba(255, 255, 255, 0.6);
            margin-bottom: 8px;
        }
        
        .chart-container {
            flex: 1;
            position: relative;
            min-height: 0;
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
        
        .modal.active { display: flex; }
        
        .modal-content {
            background: linear-gradient(135deg, #001a33 0%, #003366 100%);
            border-radius: 15px;
            padding: 30px;
            max-width: 900px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            border: 2px solid rgba(77, 166, 255, 0.3);
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
        }
        
        .gibson-modal .modal-content { max-width: 500px; }
        
        .gibson-title {
            font-size: 28px;
            color: #4da6ff;
            text-align: center;
            margin-bottom: 30px;
            font-weight: 700;
            text-shadow: 0 0 10px rgba(77, 166, 255, 0.5);
        }
        
        .gibson-actions {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        .gibson-btn {
            background: rgba(0, 40, 80, 0.7);
            border: 2px solid rgba(77, 166, 255, 0.5);
            border-radius: 10px;
            padding: 20px;
            color: #ffffff;
            cursor: pointer;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
            transition: all 0.3s ease;
        }
        
        .gibson-btn:hover {
            background: rgba(77, 166, 255, 0.2);
            border-color: #4da6ff;
            transform: translateY(-2px);
        }
        
        .gibson-btn i {
            font-size: 32px;
            color: #4da6ff;
        }
        
        .gibson-btn-label {
            font-size: 14px;
            font-weight: 600;
        }
        
        .gibson-btn-desc {
            font-size: 11px;
            color: rgba(255, 255, 255, 0.6);
            text-align: center;
        }
        
        .version-info {
            background: rgba(0, 0, 0, 0.3);
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .version-current {
            font-size: 14px;
            color: #4da6ff;
            margin-bottom: 5px;
        }
        
        .version-status {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.7);
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
        }
        
        .device-table td {
            padding: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
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
        }
        
        .signal-excellent { background: #4CAF50; }
        .signal-good { background: #8BC34A; }
        .signal-fair { background: #FFC107; }
        .signal-poor { background: #FF9800; }
        .signal-weak { background: #F44336; }
        
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
            text-align: center;
        }
        
        .speedtest-metric-label {
            font-size: 14px;
            color: #4da6ff;
            margin-bottom: 10px;
        }
        
        .speedtest-metric-value {
            font-size: 36px;
            font-weight: 600;
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
    </style>
</head>
<body>
    <div class="token-warning" id="tokenWarning">
        <i class="fas fa-exclamation-triangle"></i>
        <div>
            <strong>API Token Expired</strong>
            <div style="font-size: 11px;">Needs refresh</div>
        </div>
        <button class="token-warning-btn" onclick="openReauth()">Re-authorize</button>
        <button class="token-warning-btn" onclick="dismissTokenWarning()">Dismiss</button>
    </div>

    <div class="pixelate" id="mainContent">
        <div class="header">
            <div class="header-title">MiniRack Dashboard v4.0.1 - The Gibson</div>
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
                <div class="chart-subtitle">Wireless devices</div>
                <div class="chart-container">
                    <canvas id="usersChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <div class="chart-title">Device OS</div>
                <div class="chart-subtitle" id="deviceOsSubtitle">Loading...</div>
                <div class="chart-container">
                    <canvas id="deviceOSChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <div class="chart-title">Frequency</div>
                <div class="chart-subtitle" id="frequencySubtitle">Loading...</div>
                <div class="chart-container">
                    <canvas id="frequencyChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <div class="chart-title">Signal Strength</div>
                <div class="chart-subtitle">Average (dBm)</div>
                <div class="chart-container">
                    <canvas id="signalStrengthChart"></canvas>
                </div>
            </div>
        </div>
    </div>

    <div class="gibson-icon" id="gibsonIcon" title="The Gibson">π</div>

    <div class="modal gibson-modal" id="gibsonModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="gibson-title">⚡ THE GIBSON ⚡</h2>
                <button class="close-btn" id="closeGibson">&times;</button>
            </div>
            <div class="version-info">
                <div class="version-current">v4.0.1</div>
                <div class="version-status" id="versionStatus">Checking...</div>
            </div>
            <div class="gibson-actions">
                <div class="gibson-btn" id="updateBtn">
                    <i class="fas fa-download"></i>
                    <div class="gibson-btn-label">Check Updates</div>
                    <div class="gibson-btn-desc">Update to latest</div>
                </div>
                <div class="gibson-btn" id="restartServiceBtn">
                    <i class="fas fa-rotate"></i>
                    <div class="gibson-btn-label">Restart Service</div>
                    <div class="gibson-btn-desc">Restart backend</div>
                </div>
                <div class="gibson-btn" id="rebootSystemBtn">
                    <i class="fas fa-power-off"></i>
                    <div class="gibson-btn-label">Reboot System</div>
                    <div class="gibson-btn-desc">Restart device</div>
                </div>
                <div class="gibson-btn" id="reauthBtn">
                    <i class="fas fa-key"></i>
                    <div class="gibson-btn-label">Re-authorize</div>
                    <div class="gibson-btn-desc">Update API token</div>
                </div>
            </div>
        </div>
    </div>

    <div class="modal" id="deviceModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">Connected Devices</h2>
                <button class="close-btn" id="closeDeviceModal">&times;</button>
            </div>
            <div id="deviceCount">Loading...</div>
            <table class="device-table">
                <thead>
                    <tr>
                        <th>Device</th>
                        <th>OS</th>
                        <th>Frequency</th>
                        <th>IP</th>
                        <th>Signal</th>
                    </tr>
                </thead>
                <tbody id="deviceTableBody">
                    <tr><td colspan="5" style="text-align:center;">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <div class="modal" id="speedTestModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">Speed Test</h2>
                <button class="close-btn" id="closeSpeedTestModal">&times;</button>
            </div>
            <div style="text-align:center; padding:20px;" id="speedTestContainer">
                <p>Click "Run Test"</p>
                <button class="header-btn" id="runSpeedTest" style="margin: 20px auto;">
                    <i class="fas fa-play"></i>
                    <span>Run Test</span>
                </button>
            </div>
        </div>
    </div>

    <div class="modal" id="reauthModal">
        <div class="modal-content" style="max-width: 600px;">
            <div class="modal-header">
                <h2 class="modal-title">Re-authorize</h2>
                <button class="close-btn" id="closeReauth">&times;</button>
            </div>
            <div style="padding: 20px;">
                <p style="margin-bottom: 20px;">Run this command:</p>
                <div style="background: rgba(0,0,0,0.5); padding: 15px; border-radius: 8px; font-family: monospace;">
                    sudo {{INSTALL_DIR}}/setup_eero_auth.py
                </div>
                <p style="font-size: 12px; color: rgba(255,255,255,0.6); margin-top: 20px;">
                    Then restart service using The Gibson
                </p>
            </div>
        </div>
    </div>

    <script>
        let charts = {};
        const colors = {
            primary: '#4da6ff',
            success: '#51cf66',
            info: '#74c0fc',
            warning: '#ffd43b',
            orange: '#ff922b',
            purple: '#b197fc'
        };
        
        function initCharts() {
            const opts = {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#fff', font: { size: 10 } } } },
                scales: {
                    y: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } },
                    x: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } }
                }
            };
            
            charts.users = new Chart(document.getElementById('usersChart'), {
                type: 'line',
                data: { labels: [], datasets: [{ label: 'Connected', data: [], borderColor: colors.primary, backgroundColor: 'rgba(77,166,255,0.1)', tension: 0.4, fill: true }] },
                options: opts
            });
            
            charts.deviceOS = new Chart(document.getElementById('deviceOSChart'), {
                type: 'doughnut',
                data: { labels: ['iOS', 'Android', 'Windows', 'Other'], datasets: [{ data: [0,0,0,0], backgroundColor: [colors.primary, colors.success, colors.info, colors.warning] }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { color: '#fff', font: { size: 10 } } } } }
            });
            
            charts.frequency = new Chart(document.getElementById('frequencyChart'), {
                type: 'doughnut',
                data: { labels: ['2.4 GHz', '5 GHz', '6 GHz'], datasets: [{ data: [0,0,0], backgroundColor: [colors.orange, colors.primary, colors.purple] }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { color: '#fff', font: { size: 10 } } } } }
            });
            
            charts.signalStrength = new Chart(document.getElementById('signalStrengthChart'), {
                type: 'line',
                data: { labels: [], datasets: [{ label: 'Avg (dBm)', data: [], borderColor: colors.success, backgroundColor: 'rgba(81,207,102,0.1)', tension: 0.4, fill: true }] },
                options: opts
            });
        }
        
        async function updateDashboard() {
            try {
                const res = await fetch('/api/dashboard');
                const data = await res.json();
                
                if (data.token_expired) document.getElementById('tokenWarning').classList.add('show');
                
                charts.users.data.labels = data.connected_users.map(e => new Date(e.timestamp).toLocaleTimeString());
                charts.users.data.datasets[0].data = data.connected_users.map(e => e.count);
                charts.users.update();
                
                const os = data.device_os || {iOS:0, Android:0, Windows:0, Other:0};
                const total = Object.values(os).reduce((a,b) => a+b, 0);
                charts.deviceOS.data.datasets[0].data = [os.iOS||0, os.Android||0, os.Windows||0, os.Other||0];
                charts.deviceOS.update();
                document.getElementById('deviceOsSubtitle').textContent = `${total} devices`;
                
                const freq = data.frequency_distribution || {'2.4GHz':0, '5GHz':0, '6GHz':0};
                const freqTotal = (freq['2.4GHz']||0) + (freq['5GHz']||0) + (freq['6GHz']||0);
                charts.frequency.data.datasets[0].data = [freq['2.4GHz']||0, freq['5GHz']||0, freq['6GHz']||0];
                charts.frequency.update();
                document.getElementById('frequencySubtitle').textContent = `${freqTotal} devices`;
                
                charts.signalStrength.data.labels = data.signal_strength_avg.map(e => new Date(e.timestamp).toLocaleTimeString());
                charts.signalStrength.data.datasets[0].data = data.signal_strength_avg.map(e => e.avg_dbm);
                charts.signalStrength.update();
                
                document.getElementById('lastUpdate').textContent = `Updated: ${new Date(data.last_update).toLocaleTimeString()}`;
            } catch(e) {
                console.error('Update error:', e);
            }
        }
        
        function getSignalClass(s) {
            if (s >= 80) return 'signal-excellent';
            if (s >= 60) return 'signal-good';
            if (s >= 40) return 'signal-fair';
            if (s >= 20) return 'signal-poor';
            return 'signal-weak';
        }
        
        async function loadDevices() {
            try {
                const res = await fetch('/api/devices');
                const data = await res.json();
                document.getElementById('deviceCount').textContent = `${data.count} devices`;
                const tbody = document.getElementById('deviceTableBody');
                if (data.devices.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No devices</td></tr>';
                    return;
                }
                tbody.innerHTML = data.devices.map(d => `
                    <tr>
                        <td><strong>${d.name}</strong></td>
                        <td>${d.device_os}</td>
                        <td>${d.frequency}</td>
                        <td>${d.ip}</td>
                        <td>
                            <div class="signal-bar">
                                <div class="signal-fill ${getSignalClass(d.signal_avg)}" style="width:${d.signal_avg}%"></div>
                            </div>
                            <small>${d.signal_quality}</small>
                        </td>
                    </tr>
                `).join('');
            } catch(e) {
                console.error('Device load error:', e);
            }
        }
        
        async function runSpeedTest() {
            const btn = document.getElementById('runSpeedTest');
            const container = document.getElementById('speedTestContainer');
            btn.disabled = true;
            container.innerHTML = '<div class="spinner"></div><p>Testing...</p>';
            
            try {
                await fetch('/api/speedtest/start', {method: 'POST'});
                const check = setInterval(async () => {
                    const res = await fetch('/api/speedtest/status');
                    const data = await res.json();
                    if (!data.running && data.result) {
                        clearInterval(check);
                        if (data.result.error) {
                            container.innerHTML = `<p style="color:#ff6b6b;">Error: ${data.result.error}</p>`;
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
                                <button class="header-btn" onclick="runSpeedTest()" style="margin:20px auto;">
                                    <i class="fas fa-redo"></i><span>Again</span>
                                </button>
                            `;
                        }
                        btn.disabled = false;
                    }
                }, 2000);
            } catch(e) {
                container.innerHTML = `<p style="color:#ff6b6b;">Error: ${e.message}</p>`;
                btn.disabled = false;
            }
        }
        
        function openGibson() {
            document.getElementById('mainContent').classList.add('active');
            setTimeout(() => document.getElementById('gibsonModal').classList.add('active'), 300);
            checkUpdates();
        }
        
        function closeGibson() {
            document.getElementById('gibsonModal').classList.remove('active');
            setTimeout(() => document.getElementById('mainContent').classList.remove('active'), 100);
        }
        
        async function checkUpdates() {
            const el = document.getElementById('versionStatus');
            el.textContent = 'Checking...';
            try {
                const res = await fetch('/api/version');
                const data = await res.json();
                el.textContent = 'Up to date';
            } catch(e) {
                el.textContent = 'Check failed';
            }
        }
        
        async function restartService() {
            if (!confirm('Restart service?')) return;
            await fetch('/api/system/restart', {method: 'POST'});
            alert('Restarting...');
            setTimeout(() => location.reload(), 5000);
        }
        
        async function rebootSystem() {
            if (!confirm('Reboot system?')) return;
            if (!confirm('Sure? All connections lost.')) return;
            await fetch('/api/system/reboot', {method: 'POST'});
            alert('Rebooting...');
            closeGibson();
        }
        
        function openReauth() {
            document.getElementById('reauthModal').classList.add('active');
        }
        
        function dismissTokenWarning() {
            document.getElementById('tokenWarning').classList.remove('show');
        }
        
        // Event listeners
        document.getElementById('gibsonIcon').addEventListener('click', openGibson);
        document.getElementById('closeGibson').addEventListener('click', closeGibson);
        document.getElementById('updateBtn').addEventListener('click', () => alert('Run: sudo python3 {{INSTALL_DIR}}/install.py'));
        document.getElementById('restartServiceBtn').addEventListener('click', restartService);
        document.getElementById('rebootSystemBtn').addEventListener('click', rebootSystem);
        document.getElementById('reauthBtn').addEventListener('click', openReauth);
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
        document.getElementById('closeReauth').addEventListener('click', () => {
            document.getElementById('reauthModal').classList.remove('active');
        });
        document.getElementById('runSpeedTest').addEventListener('click', runSpeedTest);
        
        document.querySelectorAll('.modal').forEach(m => {
            m.addEventListener('click', (e) => {
                if (e.target === m) {
                    m.classList.remove('active');
                    if (m.id === 'gibsonModal') closeGibson();
                }
            });
        });
        
        window.addEventListener('load', () => {
            console.log('MiniRack Dashboard v4.0.1 - The Gibson');
            initCharts();
            updateDashboard();
            setInterval(updateDashboard, 60000);
        });
    </script>
</body>
</html>"""

# Routes
@app.route('/')
def index():
    """Serve main page"""
    html = HTML_CONTENT.replace('{{INSTALL_DIR}}', INSTALL_DIR)
    return html

@app.route('/api/dashboard')
def get_dashboard_data():
    update_cache()
    return jsonify(data_cache)

@app.route('/api/devices')
def get_devices():
    return jsonify({
        'devices': data_cache.get('devices', []),
        'count': len(data_cache.get('devices', []))
    })

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
    return jsonify({
        'running': data_cache['speedtest_running'],
        'result': data_cache['speedtest_result']
    })

@app.route('/api/system/restart', methods=['POST'])
def restart_service():
    """Restart service"""
    try:
        logging.info("Service restart requested")
        subprocess.Popen(['sudo', 'systemctl', 'restart', 'eero-dashboard'])
        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f"Restart failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/system/reboot', methods=['POST'])
def reboot_system():
    """Reboot system"""
    try:
        logging.info("System reboot requested")
        subprocess.Popen(['sudo', 'reboot'])
        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f"Reboot failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/version')
def get_version():
    return jsonify({
        'current_version': '4.0.1',
        'name': 'MiniRack Dashboard - The Gibson',
        'repository': f'https://github.com/{GITHUB_REPO}'
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'token_expired': data_cache.get('token_expired', False)
    })

if __name__ == '__main__':
    logging.info("Starting MiniRack Dashboard v4.0.1 - The Gibson")
    update_cache()
    app.run(host='0.0.0.0', port=80, debug=False)
