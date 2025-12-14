"""
Quick Start Script - Run the Provider Data Validation System
"""

import subprocess
import sys
import os

def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║     Provider Data Validation System - EY Techathon 2025       ║
    ║                                                               ║
    ║  AI-Powered Healthcare Provider Directory Validation          ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Check if streamlit is installed
    try:
        import streamlit
        print("✓ Streamlit is installed")
    except ImportError:
        print("✗ Streamlit not found. Installing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Run the application
    print("\n🚀 Starting the Provider Data Validation Dashboard...")
    print("   Open http://localhost:8501 in your browser\n")
    
    os.system(f"{sys.executable} -m streamlit run app.py")


if __name__ == "__main__":
    main()
