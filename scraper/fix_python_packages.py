#!/usr/bin/env python3
"""
Quick fix script for patchright/botright installation issues
Handles the pkgutil.ImpImporter AttributeError in Python 3.12
"""

import subprocess
import sys
import os

def run_command(cmd, description=""):
    """Run a command and return success status"""
    print(f"🔧 {description}")
    print(f"   Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"   ✅ Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed: {e.stderr.strip()}")
        return False

def check_python_version():
    """Check Python version and warn about compatibility"""
    version = sys.version_info
    print(f"🐍 Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor == 12:
        print("⚠️  WARNING: Python 3.12 has compatibility issues with some packages")
        print("   Consider using Python 3.11 for better compatibility")
        return False
    elif version.major == 3 and version.minor in [10, 11]:
        print("✅ Python version is compatible")
        return True
    else:
        print("⚠️  Python version may have compatibility issues")
        return False

def fix_setuptools_issue():
    """Fix the setuptools compatibility issue"""
    print("\n🛠️  Fixing setuptools compatibility issue...")
    
    # Method 1: Update pip and setuptools
    if not run_command(f"{sys.executable} -m pip install --upgrade pip", "Updating pip"):
        return False
    
    # Clear cache
    run_command(f"{sys.executable} -m pip cache purge", "Clearing pip cache")
    
    # Install compatible setuptools version
    if not run_command(f'{sys.executable} -m pip install "setuptools<70.0.0"', "Installing compatible setuptools"):
        return False
    
    return True

def install_package_with_fallbacks(package_name):
    """Try multiple methods to install a package"""
    print(f"\n📦 Installing {package_name}...")
    
    methods = [
        (f"{sys.executable} -m pip install {package_name}", "Normal installation"),
        (f"{sys.executable} -m pip install --no-build-isolation {package_name}", "No build isolation"),
        (f"{sys.executable} -m pip install --no-cache-dir {package_name}", "No cache"),
        (f"{sys.executable} -m pip install --force-reinstall {package_name}", "Force reinstall"),
    ]
    
    for cmd, description in methods:
        print(f"\n   Trying: {description}")
        if run_command(cmd, f"Installing {package_name} with {description}"):
            print(f"   ✅ {package_name} installed successfully!")
            return True
    
    print(f"   ❌ All installation methods failed for {package_name}")
    return False

def install_alternatives():
    """Install alternative packages if main ones fail"""
    print("\n🔄 Installing alternative packages...")
    
    alternatives = [
        ("playwright-stealth", "Alternative to patchright"),
        ("undetected-chromedriver", "Alternative to botright"),
        ("selenium-stealth", "Additional stealth option"),
    ]
    
    for package, description in alternatives:
        print(f"\n📦 Installing {package} ({description})...")
        run_command(f"{sys.executable} -m pip install {package}", f"Installing {package}")

def verify_installation():
    """Verify which packages are installed"""
    print("\n🔍 Verifying installation...")
    
    core_packages = ["playwright", "beautifulsoup4", "aiohttp", "requests", "lxml", "pydoll-python"]
    optional_packages = ["patchright", "botright", "playwright-stealth", "undetected-chromedriver"]
    
    print("\nCore packages:")
    for package in core_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package}")
    
    print("\nOptional packages:")
    for package in optional_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ⚠️  {package}")

def main():
    print("🚀 Python Package Fix Script")
    print("=" * 40)
    
    # Check Python version
    python_ok = check_python_version()
    
    # Install core packages first
    print("\n📦 Installing core packages...")
    core_packages = ["playwright", "beautifulsoup4", "aiohttp", "requests", "lxml"]
    
    for package in core_packages:
        run_command(f"{sys.executable} -m pip install {package}", f"Installing {package}")
    
    # Install pydoll (usually works fine)
    print("\n📦 Installing pydoll...")
    if not run_command(f"{sys.executable} -m pip install pydoll-python", "Installing pydoll"):
        print("❌ Failed to install pydoll - this is required!")
        return False
    
    # Fix setuptools issue
    if not python_ok:
        if not fix_setuptools_issue():
            print("❌ Failed to fix setuptools issue")
    
    # Try to install patchright
    patchright_success = install_package_with_fallbacks("patchright")
    
    # Try to install botright
    botright_success = install_package_with_fallbacks("botright")
    
    # If main packages failed, install alternatives
    if not patchright_success or not botright_success:
        install_alternatives()
    
    # Install Playwright browsers
    print("\n🌐 Installing Playwright browsers...")
    run_command(f"{sys.executable} -m playwright install chromium", "Installing Chromium browser")
    
    # Verify installation
    verify_installation()
    
    print("\n" + "=" * 40)
    print("🎉 Package installation complete!")
    print("\nNext steps:")
    print("1. Test the setup: python test_captcha_setup.py")
    print("2. Run the scraper: python scrapeevents.py")
    
    if not patchright_success or not botright_success:
        print("\nNote: Some packages failed to install, but the scraper")
        print("will still work with pydoll and standard Playwright.")

if __name__ == "__main__":
    main()