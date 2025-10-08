#!/usr/bin/env python3
"""
PDF Password Cracker - Launcher Script
Quick launcher untuk PDF Password Cracker & Viewer
"""

import sys
import subprocess
import os

def run_app():
    """Jalankan aplikasi PDF Password Cracker"""
    print("� Menjalankan PDF Password Cracker & Viewer...")
    print("📁 Modular Architecture - Production Ready")
    print("-" * 50)
    subprocess.run([sys.executable, "main.py"])

def show_info():
    """Tampilkan informasi aplikasi"""
    print("""
🔓 PDF Password Cracker & Viewer
========================================
📋 Modular Architecture Edition

Features:
✅ 6-digit & 8-digit password cracking
✅ Single-thread & Multi-thread processing
✅ Advanced PDF viewer dengan zoom & navigation
✅ Pause/Resume functionality  
✅ Real-time progress tracking
✅ Keyboard shortcuts support

Architecture:
📂 core/           - Password cracking algorithms
📂 ui/             - User interface components
📁 main.py         - Main application

Usage:
    python main.py          - Direct run
    python launcher.py      - Launch via script
    python launcher.py info - Show this information
    
Dependencies:
    pip install -r requirements.txt
    """)

def main():
    """Main launcher function"""
    if len(sys.argv) < 2:
        # Default: run application
        run_app()
        return
    
    arg = sys.argv[1].lower()
    
    if arg in ['info', 'i', 'help', 'h', '?']:
        show_info()
    elif arg in ['run', 'start', 'launch']:
        run_app()
    else:
        print(f"ℹ️ Running application (unknown option: {arg})")
        run_app()

if __name__ == "__main__":
    main()