# The Minirack eero Network Dashboard v5.2.4

A comprehensive, real-time network monitoring dashboard for eero networks with a beautiful web interface and powerful admin features. Built specifically for a fresh install of a Raspberry Pi with Chromium and kiosk mode support.

![Version](https://img.shields.io/badge/version-5.2.4-blue.svg)
![Python](https://img.shields.io/badge/python-3.7+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

---
![alt text](https://github.com/adam-p/markdown-here/raw/master/src/common/images/icon48.png](https://github.com/eero-drew/minirackdash/blob/main/mrdash-01.png) "MR Dash Screenshot")

## 🌟 Features

### Real-Time Network Monitoring
- **Live Device Tracking** - Monitor all connected wireless devices in real-time
- **Connection History** - View device connection trends over the last 2 hours
- **Signal Strength Monitoring** - Track network-wide average signal strength (dBm)
- **Auto-Refresh** - Dashboard updates automatically every 60 seconds

### Beautiful Visualizations
- **Connected Users Chart** - Line graph showing wireless device count over time
- **Device OS Distribution** - Doughnut chart breaking down iOS, Android, Windows, and Other devices
- **Frequency Band Distribution** - Visual breakdown of devices on 2.4GHz, 5GHz, and 6GHz bands
- **Signal Strength Trends** - Historical signal strength data displayed in an easy-to-read line chart

### Detailed Device Information
- **Comprehensive Device List** - View all connected wireless devices with:
  - Device name (nickname or hostname)
  - IP address
  - MAC address
  - Manufacturer
  - Operating system
  - Frequency band (2.4/5/6 GHz)
  - Signal strength (dBm and quality rating)
  - Visual signal strength indicator
- **Smart OS Detection** - Automatically categorizes devices by operating system
- **Signal Quality Ratings** - Excellent, Very Good, Good, Fair, Poor

### Integrated Speed Test
- **Built-in Speed Testing** - Run speed tests directly from the dashboard
- **Real-time Progress** - Live updates while test is running
- **Detailed Results** - View download speed, upload speed, and ping
- **Historical Tracking** - See when last test was performed

### Powerful Admin Panel (π Menu)
- **System Information** - View current version, network ID, environment, and API URL
- **Update Management** - Check for and install updates directly from GitHub
- **Network Configuration** - Change network ID without reinstalling
- **API Reauthorization** - Easily refresh API credentials when needed
- **Service Control** - Restart the dashboard service with one click
- **System Reboot** - Safely reboot the entire system from the dashboard

### Environment Support
- **Production Environment** - Connect to `api-user.e2ro.com`
- **Staging Environment** - Connect to sandbox environment
- **Easy Switching** - Change environments through configuration

### Raspberry Pi Optimized
- **Kiosk Mode** - Full-screen browser mode perfect for dedicated displays
- **Auto-Start** - Dashboard launches automatically on boot
- **Lightweight** - Optimized for Raspberry Pi 3/4/5
- **Low Resource Usage** - Minimal CPU and memory footprint

### Modern UI/UX
- **Responsive Design** - Beautiful gradient background with glassmorphism effects
- **Dark Theme** - Easy on the eyes for 24/7 monitoring
- **Interactive Modals** - Smooth pop-ups for devices, speed test, and admin panel
- **Font Awesome Icons** - Professional iconography throughout
- **Animated Elements** - Subtle animations and hover effects
- **Status Indicator** - Live pulse indicator showing system status

### Technical Features
- **RESTful API Backend** - Flask-based API for all data operations
- **CORS Enabled** - Safe cross-origin requests
- **Token-Based Authentication** - Secure Eero API authentication
- **Configuration Persistence** - Settings saved across reboots
- **Automatic Backups** - Config and tokens backed up during updates
- **Error Handling** - Graceful error handling and user feedback
- **Logging** - Comprehensive logging for troubleshooting
- **Systemd Service** - Runs as a proper Linux service with auto-restart

---

## 📋 Requirements

### Hardware
- Raspberry Pi 3, 4, or 5 (recommended)
- MicroSD card (8GB minimum, 16GB+ recommended)
- Internet connection
- (Optional) Display for kiosk mode

### Software
- Raspberry Pi OS (Debian-based)
- Python 3.7 or higher
- Root/sudo access

### Network
- Active eero network
- Eero API access credentials
- Port 80 available (no other web servers running)

---

## 🚀 Quick Start Installation

### One-Line Install

```bash
sudo python3 init_dashboard.py
```

### Detailed Installation Steps

1. **Download the installer:**
   ```bash
   wget https://raw.githubusercontent.com/eero-drew/minirackdash/main/v5/init_dashboard.py
   ```

2. **Make it executable:**
   ```bash
   chmod +x init_dashboard.py
   ```

3. **Run the installer:**
   ```bash
   sudo python3 init_dashboard.py
   ```

4. **Follow the prompts:**
   - Select environment (Production or Sandbox)
   - Enter your eero Network ID
   - Provide email for API authentication - Must be a registered API user!
   - Enter verification code from email

5. **Access the dashboard:**
   - Open browser to `http://localhost` or `http://<raspberry-pi-ip>`

---

## ⚙️ Configuration

### Environment Selection
- **Production**: Uses `api-user.e2ro.com`
- **Sandbox**: Uses sandbox environment

Configuration is saved to `/home/eero/dashboard/.config.json`

### Network ID
Your Eero Network ID is required for API access. This can be:
- Set during installation
- Changed later via the Admin Panel (π menu)

### API Authentication
- Uses token-based authentication
- Token stored securely at `/home/eero/dashboard/.eero_token`
- Can be refreshed via Admin Panel

---

## 📊 Usage

### Main Dashboard
The main dashboard displays four key charts:
1. **Connected Users** - Real-time count of wireless devices
2. **Device OS** - Distribution of device operating systems
3. **Frequency Distribution** - Breakdown by WiFi band
4. **Signal Strength** - Network-wide average signal quality

### Viewing Devices
1. Click the **Devices** button in the header
2. View detailed information for all connected devices
3. See real-time signal strength for each device

### Running Speed Tests
1. Click the **Speed Test** button in the header
2. Click **Start Speed Test**
3. Wait for results (typically 30-60 seconds)
4. View download, upload, and ping results

### Admin Panel (π Menu)
1. Click the **π** icon in the bottom-right corner
2. Access system information and administrative functions:
   - **Check for Updates** - Download and install latest version
   - **Change Network ID** - Update network configuration
   - **Reauthorize API** - Refresh API credentials
   - **Restart Service** - Restart the dashboard service
   - **Reboot System** - Reboot the Raspberry Pi

---

## 🔧 System Management

### Service Commands
```bash
# Check service status
sudo systemctl status eero-dashboard

# Start service
sudo systemctl start eero-dashboard

# Stop service
sudo systemctl stop eero-dashboard

# Restart service
sudo systemctl restart eero-dashboard

# View logs
sudo journalctl -u eero-dashboard -f
```

### Backend Logs
```bash
# View backend logs
tail -f /home/eero/dashboard/logs/backend.log
```

### Manual Update
```bash
# Force update from GitHub
sudo python3 init_dashboard.py
```

---

## 📁 File Structure

```
/home/eero/dashboard/
├── backend/
│   └── eero_api.py           # Flask backend API
├── frontend/
│   └── index.html            # Web dashboard
├── logs/
│   └── backend.log           # Application logs
├── venv/                     # Python virtual environment
├── .config.json              # Configuration file
├── .eero_token               # API authentication token
└── start_kiosk.sh           # Kiosk mode startup script
```

---

## 🐛 Troubleshooting

### Dashboard Not Loading
1. Check if service is running:
   ```bash
   sudo systemctl status eero-dashboard
   ```
2. Check logs for errors:
   ```bash
   sudo journalctl -u eero-dashboard -n 50
   ```
3. Verify port 80 is not in use:
   ```bash
   sudo lsof -i :80
   ```

### No Devices Showing
1. Verify Network ID is correct in Admin Panel
2. Check API token is valid - try reauthorizing
3. Ensure network has wireless devices connected
4. Check backend logs for API errors

### Authentication Failed
1. Verify you're using the correct environment (Production/Staging)
2. Check email for verification code
3. Try reauthorizing via Admin Panel
4. Ensure Eero account has API access

### Port 80 Conflict
If another service is using port 80:
```bash
# Stop conflicting services
sudo systemctl stop apache2
sudo systemctl stop nginx
sudo systemctl disable apache2
sudo systemctl disable nginx
```

### Charts Not Displaying
1. Clear browser cache
2. Check browser console for JavaScript errors
3. Ensure Chart.js CDN is accessible
4. Verify internet connection

---

## 🔄 Updating

### Automatic Update (Recommended)
1. Click π icon to open Admin Panel
2. Click **Check for Updates**
3. If update available, click **Update Now**
4. Dashboard will restart automatically

### Manual Update
```bash
cd /root
sudo python3 init_dashboard.py
```

The installer automatically:
- Backs up your configuration
- Downloads the latest version
- Preserves your settings
- Restarts the service

---

## 🎨 Customization

### Changing Refresh Interval
Edit `/home/eero/dashboard/frontend/index.html`:
```javascript
// Default: 60000 (60 seconds)
setInterval(updateDashboard, 60000);
```

### Modifying Data Retention
Edit `/home/eero/dashboard/backend/eero_api.py`:
```python
# Default: 2 hours
two_hours_ago = ct - timedelta(hours=2)
```

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## 📝 Version History

### v5.2.4 (Current)
- ✅ Fixed modal pop-ups for devices, speed test, and admin panel
- ✅ Fixed chart sizing to prevent container overflow
- ✅ Improved responsive design
- ✅ Enhanced error handling

### v5.2.3
- Added environment selection (Production/Staging)
- Improved configuration management
- Enhanced admin panel features

### v5.2.0
- Complete rewrite with modular architecture
- Added admin panel
- Improved authentication flow

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- eero for providing network hardware and API access
- Chart.js for beautiful data visualizations
- Font Awesome for icon library
- Flask and Python communities

---

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review troubleshooting section

---

## 🔐 Security

- API tokens are stored securely with 600 permissions
- Configuration files are protected
- No credentials stored in code
- HTTPS used for all API communications

---

**Made with ❤️ for eero Networks by Drew Lentz - drlentz@eero.com or drew@drewlentz.com**

---

*Note: This dashboard is designed for internal network monitoring. Ensure proper security measures if exposing to external networks.*
