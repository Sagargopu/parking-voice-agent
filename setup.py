"""
Installation and Setup Verification Script
Run this after creating your virtual environment to ensure everything is set up correctly
"""
import sys
import subprocess
import os
from pathlib import Path


def check_python_version():
    """Ensure Python 3.10+ is being used"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"❌ Python 3.10+ required, found {version.major}.{version.minor}")
        return False
    print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
    return True


def check_venv():
    """Check if virtual environment is activated"""
    if sys.prefix == sys.base_prefix:
        print("❌ Virtual environment not activated")
        print("   Please run: .venv\\Scripts\\activate (Windows)")
        return False
    print(f"✓ Virtual environment: {sys.prefix}")
    return True


def install_requirements():
    """Install requirements.txt"""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def check_env_file():
    """Check if .env file exists"""
    if not Path(".env").exists():
        print("\n⚠️  .env file not found")
        print("   Creating from .env.example...")
        try:
            if Path(".env.example").exists():
                import shutil
                shutil.copy(".env.example", ".env")
                print("✓ .env file created")
                print("   ⚠️  Please edit .env and add your API keys!")
                return True
            else:
                print("❌ .env.example not found")
                return False
        except Exception as e:
            print(f"❌ Failed to create .env: {e}")
            return False
    print("✓ .env file exists")
    return True


def verify_imports():
    """Verify critical imports work"""
    print("\n🔍 Verifying package installations...")
    packages = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("sqlmodel", "SQLModel"),
        ("sqlalchemy", "SQLAlchemy"),
        ("cartesia", "Cartesia SDK"),
        ("twilio", "Twilio SDK"),
        ("httpx", "HTTPX"),
        ("dateutil", "python-dateutil"),
        ("pydantic", "Pydantic"),
    ]
    
    all_ok = True
    for module_name, display_name in packages:
        try:
            __import__(module_name)
            print(f"  ✓ {display_name}")
        except ImportError:
            print(f"  ❌ {display_name} - not installed")
            all_ok = False
    
    return all_ok


def check_database_dir():
    """Ensure we can create database files"""
    try:
        # Just check write permissions
        test_file = Path(".test_write")
        test_file.touch()
        test_file.unlink()
        print("✓ Directory is writable (for SQLite databases)")
        return True
    except Exception as e:
        print(f"❌ Directory not writable: {e}")
        return False


def print_next_steps():
    """Print what to do next"""
    print("\n" + "="*60)
    print("🎉 Setup Complete!")
    print("="*60)
    print("\n📝 Next Steps:")
    print("\n1. Edit .env file with your credentials:")
    print("   - CARTESIA_API_KEY (get from https://play.cartesia.ai/)")
    print("   - TWILIO credentials")
    print("   - SMTP settings (optional)")
    print("\n2. Start the development server:")
    print("   Windows: start_dev.bat")
    print("   Or: uvicorn app.main:app --reload")
    print("\n3. Set up ngrok for local testing:")
    print("   ngrok http 8000")
    print("\n4. Create Cartesia agent:")
    print("   python scripts/setup_cartesia.py")
    print("\n5. Test the API:")
    print("   http://localhost:8000/docs")
    print("\n📚 Documentation:")
    print("   - QUICKSTART.md - Step-by-step setup guide")
    print("   - README.md - Full documentation")
    print("   - IMPLEMENTATION_SUMMARY.md - What was built")
    print("\n" + "="*60)


def main():
    print("="*60)
    print("RapidPark Voice Agent - Setup & Verification")
    print("="*60)
    print()
    
    checks = [
        ("Python version", check_python_version),
        ("Virtual environment", check_venv),
        ("Database directory", check_database_dir),
        ("Environment file", check_env_file),
    ]
    
    all_passed = True
    for name, check_func in checks:
        if not check_func():
            all_passed = False
    
    if not all_passed:
        print("\n❌ Some checks failed. Please fix the issues above.")
        sys.exit(1)
    
    # Install dependencies
    if not install_requirements():
        print("\n❌ Failed to install dependencies")
        sys.exit(1)
    
    # Verify imports
    if not verify_imports():
        print("\n❌ Some packages failed to import")
        print("   Try: pip install -r requirements.txt")
        sys.exit(1)
    
    print_next_steps()


if __name__ == "__main__":
    main()
