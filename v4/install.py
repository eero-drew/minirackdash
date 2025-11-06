#!/usr/bin/env python3
"""
Eero Dashboard v4.0.0 - Simplified Installer
Two-file system: installer + dashboard
"""
import os
import sys
import subprocess
import urllib.request
import json
from pathlib import Path
from datetime import datetime

VERSION = "4.0.0"
GITHUB_REPO = "eero-drew/minirackdash"
GITHUB_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/v4"
INSTALL_DIR = "/home/eero/dashboard"
CONFIG_FILE = f"{INSTALL_DIR}/.config.json"
STATE_FILE = f"{INSTALL_DIR}/.install_state.json"
USER = "eero"

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    BOLD = '\033[1m'
    NC = '\033[0m'

def c(color, msg):
    """Print colored message"""
    print(f"{color}{msg}{Colors.NC}")

def check_root():
    if os.geteuid() != 0:
        c(Colors.RED, "✗ Must run as root (use sudo)")
        sys.exit(1)

def run_cmd(cmd, timeout=300, show=False):
    """Run command"""
    try:
        if show:
            return subprocess.run(cmd, shell=True, timeout=timeout).returncode == 0
        return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE, timeout=timeout).returncode == 0
    except:
        return False

def load_json(path):
    """Load JSON file"""
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except:
            pass
    return {}

def save_json(path, data):
    """Save JSON file"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, indent=2, fp=f)
    os.chmod(path, 0o600)
    subprocess.run(['chown', f'{USER}:{USER}', path], check=False)

def download(url, desc):
    """Download file"""
    try:
        c(Colors.CYAN, f"ℹ Downloading {desc}...")
        with urllib.request.urlopen(url, timeout=30) as r:
            content = r.read()
        c(Colors.GREEN, f"✓ Downloaded {desc}")
        return content
    except Exception as e:
        c(Colors.RED, f"✗ Failed to download {desc}: {e}")
        return None

class Installer:
    def __init__(self):
        self.config = load_json(CONFIG_FILE)
        self.state = load_json(STATE_FILE)
        self.steps_done = self.state.get('steps_completed', [])
        
    def mark_done(self, step):
        """Mark step as complete"""
        if step not in self.steps_done:
            self.steps_done.append(step)
        self.state['steps_completed'] = self.steps_done
        self.state['last_run'] = datetime.now().isoformat()
        self.state['version'] = VERSION
        save_json(STATE_FILE, self.state)
    
    def is_done(self, step):
        """Check if step is done"""
        return step in self.steps_done
    
    def check_update_needed(self):
        """Check if update is needed"""
        installed_version = self.state.get('version', '0.0.0')
        if installed_version != VERSION:
            c(Colors.YELLOW, f"⚠ Update available: {installed_version} → {VERSION}")
            return True
        return False
    
    def step_foundation(self):
        """Install system foundation"""
        if self.is_done('foundation') and not self.check_update_needed():
            c(Colors.GREEN, "✓ Foundation already installed")
            return True
            
        c(Colors.BOLD + Colors.BLUE, "\n=== Installing Foundation ===\n")
        
        # Create user
        if subprocess.run(['id', USER], capture_output=True).returncode != 0:
            c(Colors.CYAN, "ℹ Creating user...")
            run_cmd(f'useradd -m -s /bin/bash {USER}')
        c(Colors.GREEN, f"✓ User: {USER}")
        
        # Update system
        c(Colors.CYAN, "ℹ Updating packages...")
        run_cmd('apt-get update', timeout=120, show=True)
        c(Colors.GREEN, "✓ Packages updated")
        
        # Install dependencies
        c(Colors.CYAN, "ℹ Installing dependencies...")
        pkgs = ['python3', 'python3-pip', 'python3-venv', 'git', 'curl', 'speedtest-cli']
        if run_cmd(f"DEBIAN_FRONTEND=noninteractive apt-get install -y {' '.join(pkgs)}", timeout=600, show=True):
            c(Colors.GREEN, "✓ Dependencies installed")
        
        # Create directories
        c(Colors.CYAN, "ℹ Creating directories...")
        for d in [f"{INSTALL_DIR}/backend", f"{INSTALL_DIR}/frontend", 
                  f"{INSTALL_DIR}/frontend/assets", f"{INSTALL_DIR}/logs"]:
            Path(d).mkdir(parents=True, exist_ok=True)
        run_cmd(f'chown -R {USER}:{USER} /home/eero')
        c(Colors.GREEN, "✓ Directories created")
        
        # Setup Python venv
        c(Colors.CYAN, "ℹ Setting up Python environment...")
        venv = f"{INSTALL_DIR}/venv"
        if run_cmd(f'sudo -u {USER} python3 -m venv {venv}', timeout=120):
            run_cmd(f'sudo -u {USER} {venv}/bin/pip install --quiet --upgrade pip', timeout=120)
            if run_cmd(f'sudo -u {USER} {venv}/bin/pip install --quiet flask flask-cors requests gunicorn speedtest-cli', timeout=300):
                c(Colors.GREEN, "✓ Python environment ready")
        
        # Setup sudo rules
        c(Colors.CYAN, "ℹ Configuring sudo...")
        sudoers = f"/etc/sudoers.d/eero-dashboard"
        with open(sudoers, 'w') as f:
            f.write(f"{USER} ALL=(ALL) NOPASSWD: /bin/systemctl restart eero-dashboard\n")
            f.write(f"{USER} ALL=(ALL) NOPASSWD: /bin/systemctl start eero-dashboard\n")
            f.write(f"{USER} ALL=(ALL) NOPASSWD: /bin/systemctl stop eero-dashboard\n")
            f.write(f"{USER} ALL=(ALL) NOPASSWD: /sbin/reboot\n")
        os.chmod(sudoers, 0o440)
        c(Colors.GREEN, "✓ Sudo configured")
        
        self.mark_done('foundation')
        return True
    
    def step_config(self):
        """Get network ID"""
        if self.config.get('network_id'):
            c(Colors.GREEN, f"✓ Network ID: {self.config['network_id']}")
            
            # Ask if user wants to change it
            change = input(f"{Colors.MAGENTA}Change Network ID? [y/N]: {Colors.NC}").strip().lower()
            if change == 'y':
                return self.prompt_network_id()
            return True
        
        return self.prompt_network_id()
    
    def prompt_network_id(self):
        """Prompt for network ID"""
        c(Colors.BOLD + Colors.BLUE, "\n=== Network Configuration ===\n")
        c(Colors.CYAN, "Please enter your Eero Network ID")
        c(Colors.YELLOW, "(or type 'cancel' to exit)")
        
        while True:
            network_id = input(f"{Colors.MAGENTA}Network ID: {Colors.NC}").strip()
            
            if network_id.lower() == 'cancel':
                sys.exit(0)
            
            if network_id.isdigit() and len(network_id) >= 5:
                confirm = input(f"{Colors.MAGENTA}Confirm {network_id}? [Y/n]: {Colors.NC}").strip().lower()
                if confirm != 'n':
                    self.config['network_id'] = network_id
                    self.config['network_id_updated'] = datetime.now().isoformat()
                    save_json(CONFIG_FILE, self.config)
                    c(Colors.GREEN, f"✓ Network ID saved: {network_id}")
                    return True
            else:
                c(Colors.RED, "✗ Invalid format (numeric, 5+ digits)")
    
    def step_dashboard(self):
        """Deploy dashboard"""
        c(Colors.BOLD + Colors.BLUE, "\n=== Deploying Dashboard ===\n")
        
        # Download dashboard.py
        url = f"{GITHUB_BASE}/dashboard.py"
        content = download(url, "dashboard")
        
        if not content:
            return False
        
        # Replace config variables
        content = content.decode('utf-8')
        content = content.replace('{{NETWORK_ID}}', self.config['network_id'])
        content = content.replace('{{USER}}', USER)
        content = content.replace('{{INSTALL_DIR}}', INSTALL_DIR)
        content = content.replace('{{GITHUB_REPO}}', GITHUB_REPO)
        
        # Write backend file
        backend_path = f"{INSTALL_DIR}/backend/eero_api.py"
        with open(backend_path, 'w') as f:
            f.write(content)
        os.chmod(backend_path, 0o755)
        subprocess.run(['chown', f'{USER}:{USER}', backend_path], check=False)
        c(Colors.GREEN, f"✓ Dashboard deployed")
        
        self.mark_done('dashboard')
        return True
    
    def step_service(self):
        """Setup systemd service"""
        c(Colors.BOLD + Colors.BLUE, "\n=== Setting up Service ===\n")
        
        service_content = f"""[Unit]
Description=Eero Dashboard v4 - The Gibson
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={INSTALL_DIR}/backend
Environment="PATH={INSTALL_DIR}/venv/bin"
ExecStart={INSTALL_DIR}/venv/bin/gunicorn -w 2 -b 0.0.0.0:80 --user {USER} --group {USER} --timeout 120 --access-logfile {INSTALL_DIR}/logs/access.log --error-logfile {INSTALL_DIR}/logs/error.log eero_api:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        
        service_path = '/etc/systemd/system/eero-dashboard.service'
        with open(service_path, 'w') as f:
            f.write(service_content)
        
        run_cmd('systemctl daemon-reload')
        run_cmd('systemctl enable eero-dashboard.service')
        run_cmd('systemctl restart eero-dashboard.service')
        
        c(Colors.GREEN, "✓ Service started")
        self.mark_done('service')
        return True
    
    def step_kiosk(self):
        """Setup kiosk mode"""
        c(Colors.CYAN, "ℹ Setting up kiosk...")
        
        kiosk_script = f"""#!/bin/bash
xset s off 2>/dev/null
xset -dpms 2>/dev/null
xset s noblank 2>/dev/null
unclutter -idle 0.1 2>/dev/null &
if command -v chromium-browser &> /dev/null; then
    chromium-browser --kiosk --noerrdialogs --disable-infobars --no-first-run http://localhost
elif command -v chromium &> /dev/null; then
    chromium --kiosk --noerrdialogs --disable-infobars --no-first-run http://localhost
else
    echo "Chromium not found"
fi
"""
        
        kiosk_path = f"{INSTALL_DIR}/kiosk.sh"
        with open(kiosk_path, 'w') as f:
            f.write(kiosk_script)
        os.chmod(kiosk_path, 0o755)
        subprocess.run(['chown', f'{USER}:{USER}', kiosk_path], check=False)
        
        autostart_dir = f'/home/{USER}/.config/autostart'
        Path(autostart_dir).mkdir(parents=True, exist_ok=True)
        
        desktop_path = f'{autostart_dir}/dashboard.desktop'
        with open(desktop_path, 'w') as f:
            f.write(f"""[Desktop Entry]
Type=Application
Name=Eero Dashboard v4
Exec={kiosk_path}
X-GNOME-Autostart-enabled=true
""")
        
        run_cmd(f'chown -R {USER}:{USER} /home/{USER}/.config')
        c(Colors.GREEN, "✓ Kiosk configured")
        self.mark_done('kiosk')
        return True
    
    def step_auth(self):
        """Create auth helper"""
        c(Colors.CYAN, "ℹ Creating auth helper...")
        
        auth_script = '''#!/usr/bin/env python3
import requests
import json
from datetime import datetime

print("=" * 60)
print("Eero API Authentication")
print("=" * 60)

email = input("\\nEmail: ").strip()
print("\\nSending verification code...")

try:
    response = requests.post("https://api-user.e2ro.com/2.2/pro/login", json={"login": email})
    data = response.json()

    if 'data' in data and 'user_token' in data['data']:
        token = data['data']['user_token']
        print(f"✓ Token generated: {token[:20]}...")
        print(f"✓ Code sent to: {email}")
        
        code = input("\\nEnter verification code: ").strip()
        
        verify_response = requests.post(
            "https://api-user.e2ro.com/2.2/login/verify",
            headers={"X-User-Token": token},
            data={"code": code}
        )
        
        if verify_response.json().get('data', {}).get('email', {}).get('verified'):
            with open('/home/eero/dashboard/.eero_token', 'w') as f:
                f.write(token)
            with open('/home/eero/dashboard/.eero_token.timestamp', 'w') as f:
                f.write(datetime.now().isoformat())
            print("\\n✓ Authorized!")
            print("\\nRestart service: sudo systemctl restart eero-dashboard")
        else:
            print("\\n✗ Verification failed")
    else:
        print("\\n✗ Failed to generate token")
except Exception as e:
    print(f"\\n✗ Error: {e}")
'''
        
        auth_path = f"{INSTALL_DIR}/setup_eero_auth.py"
        with open(auth_path, 'w') as f:
            f.write(auth_script)
        os.chmod(auth_path, 0o755)
        subprocess.run(['chown', f'{USER}:{USER}', auth_path], check=False)
        
        c(Colors.GREEN, "✓ Auth helper created")
        self.mark_done('auth')
        return True
    
    def run(self):
        """Run installation"""
        c(Colors.BOLD + Colors.BLUE, f"\n{'='*70}")
        c(Colors.BOLD + Colors.BLUE, f"{'Eero Dashboard v4.0.0 Installer'.center(70)}")
        c(Colors.BOLD + Colors.BLUE, f"{'='*70}\n")
        
        check_root()
        
        # Run steps
        self.step_foundation()
        self.step_config()
        self.step_dashboard()
        self.step_service()
        self.step_kiosk()
        self.step_auth()
        
        # Done
        c(Colors.BOLD + Colors.GREEN, "\n" + "="*70)
        c(Colors.BOLD + Colors.GREEN, "Installation Complete!".center(70))
        c(Colors.BOLD + Colors.GREEN, "="*70 + "\n")
        c(Colors.CYAN, "🎉 What's New in v4:")
        c(Colors.GREEN, "  ✓ 2-file system - simple & clean")
        c(Colors.GREEN, "  ✓ Resumable installation")
        c(Colors.GREEN, "  ✓ No nginx - lightweight Flask")
        c(Colors.GREEN, "  ✓ The Gibson control panel")
        c(Colors.GREEN, "  ✓ Config persists across updates")
        print()
        c(Colors.CYAN, "Next steps:")
        print(f"  1. Authorize: sudo {INSTALL_DIR}/setup_eero_auth.py")
        print(f"  2. Check status: sudo systemctl status eero-dashboard")
        print(f"  3. View logs: tail -f {INSTALL_DIR}/logs/error.log")
        print(f"  4. Access: http://localhost")
        print()
        c(Colors.MAGENTA, "To update later:")
        print(f"  curl -O {GITHUB_BASE}/install.py")
        print(f"  sudo python3 install.py")
        print()

if __name__ == '__main__':
    try:
        Installer().run()
    except KeyboardInterrupt:
        c(Colors.RED, "\n✗ Cancelled")
        sys.exit(1)
    except Exception as e:
        c(Colors.RED, f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
