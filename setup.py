import subprocess
import sys
import os
import time
import winreg
import urllib.request
from pathlib import Path

def install_package(package):
    """Install a Python package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"Successfully installed {package}")
        return True
    except subprocess.CalledProcessError:
        print(f"Failed to install {package}")
        return False

def check_and_install_packages():
    """Check and install required Python packages"""
    required_packages = {
        'pyautogui': 'pyautogui',
        'keyboard': 'keyboard',
        'pillow': 'pillow',
        'numpy': 'numpy',
        'pytesseract': 'pytesseract',
        'opencv-python': 'opencv-python'
    }
    
    installed = []
    for package, pip_name in required_packages.items():
        try:
            __import__(package)
            print(f"[OK] {package} is already installed")
            installed.append(package)
        except ImportError:
            print(f"Installing {package}...")
            if install_package(pip_name):
                installed.append(package)

    return len(installed) == len(required_packages)

def is_tesseract_installed():
    """Check if Tesseract is installed"""
    try:
        import pytesseract
        # Set the tesseract path explicitly
        tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if os.path.exists(tesseract_path):
            os.environ['PATH'] = os.environ['PATH'] + ';' + os.path.dirname(tesseract_path)
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            version = pytesseract.get_tesseract_version()
            print(f"Found Tesseract version {version} at: {tesseract_path}")
            return True
        else:
            print("Tesseract executable not found in the default location.")
            print("Please ensure Tesseract is installed correctly.")
            return False
    except Exception as e:
        print(f"Error checking Tesseract: {e}")
        print("Please ensure Tesseract is installed and the path is correct.")
        return False

def get_temp_dir():
    """Get Windows temp directory"""
    return os.path.join(os.environ.get('TEMP', os.path.expanduser('~')))

def download_tesseract():
    """Download Tesseract installer"""
    tesseract_url = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
    installer_path = os.path.join(get_temp_dir(), "tesseract_installer.exe")
    
    print("Downloading Tesseract installer...")
    try:
        # Add headers to avoid 403 error
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(tesseract_url, headers=headers)
        with urllib.request.urlopen(req) as response, open(installer_path, 'wb') as out_file:
            out_file.write(response.read())
        return installer_path
    except Exception as e:
        print(f"Failed to download Tesseract: {e}")
        print("Please download and install Tesseract manually from: https://github.com/UB-Mannheim/tesseract/releases")
        print("After installation, make sure to add Tesseract to your PATH environment variable")
        return None

def install_tesseract(installer_path):
    """Install Tesseract"""
    try:
        print("Installing Tesseract...")
        # Run installer silently and wait for completion
        result = subprocess.run([installer_path, '/S'], check=True, capture_output=True)
        
        # Add Tesseract to system PATH
        tesseract_path = r'C:\Program Files\Tesseract-OCR'
        
        # Use PowerShell to add to system PATH permanently
        ps_command = f'[Environment]::SetEnvironmentVariable("Path", $env:Path + ";{tesseract_path}", [System.EnvironmentVariableTarget]::Machine)'
        subprocess.run(['powershell', '-Command', ps_command], check=True, capture_output=True)
        
        # Also add to current session PATH
        os.environ['PATH'] += f';{tesseract_path}'
        
        print("Added Tesseract to system PATH")
        
        # Verify installation
        try:
            subprocess.run(['tesseract', '--version'], check=True, capture_output=True)
            print("Tesseract installed successfully and added to PATH!")
            return True
        except subprocess.CalledProcessError:
            print("Tesseract installed but there might be an issue with PATH")
            print("Please try restarting your terminal/IDE after installation")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"Failed to install Tesseract: {e}")
        print("Please try installing Tesseract manually and add it to PATH")
        return False

def check_and_install_tesseract():
    """Check and install Tesseract if needed"""
    if is_tesseract_installed():
        print("[OK] Tesseract is already installed")
        return True
    
    print("Tesseract not found. Installing...")
    installer_path = download_tesseract()
    if installer_path and install_tesseract(installer_path):
        try:
            os.remove(installer_path)
        except:
            pass
        return True
    return False

def setup_environment():
    """Main setup function"""
    print("Checking and installing required components...")
    
    # Install Python packages
    if not check_and_install_packages():
        print("Failed to install required Python packages.")
        return False
    
    # Install Tesseract
    if not check_and_install_tesseract():
        print("Failed to install Tesseract.")
        return False
    
    print("\nAll components installed successfully!")
    return True

if __name__ == "__main__":
    import time  # Import at the start of the main block
    if setup_environment():
        print("\nStarting Cursor automation...")
        time.sleep(2)
        # Import and run the main automation script
        try:
            from cursor_automation import main as run_automation
            run_automation()
        except ImportError:
            print("Please place the automation script in the same directory as this setup script.")
    else:
        print("\nSetup failed. Please check the error messages above.")