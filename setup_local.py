#!/usr/bin/env python3
"""
Setup script for local PDF outline extraction
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ Python 3.7+ is required")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def install_dependencies():
    """Install required Python packages"""
    packages = [
        "PyMuPDF==1.23.22",
        "regex==2023.12.25"
    ]
    
    print("📦 Installing dependencies...")
    for package in packages:
        try:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {package}")
            print("💡 Try running: pip install --user PyMuPDF regex")
            return False
    return True

def create_directories():
    """Create input and output directories"""
    directories = ["input", "output"]
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir()
            print(f"✅ Created '{dir_name}' directory")
        else:
            print(f"📁 '{dir_name}' directory already exists")

def create_sample_readme():
    """Create a local README with instructions"""
    readme_content = """# Local PDF Outline Extractor

## Quick Start

1. **Place PDF files** in the `input/` folder
2. **Run the extractor**: `python process_pdfs_local.py`
3. **Check results** in the `output/` folder

## Folder Structure
```
project/
├── input/           # Place your PDF files here
│   ├── document1.pdf
│   ├── document2.pdf
│   └── ...
├── output/          # JSON results appear here
│   ├── document1.json
│   ├── document2.json
│   └── ...
├── process_pdfs_local.py    # Main script
└── README_LOCAL.md          # This file
```

## Expected Output Format
Each PDF generates a JSON file like this:
```json
{
  "title": "Document Title",
  "outline": [
    {"level": "H1", "text": "Main Section", "page": 1},
    {"level": "H2", "text": "Subsection", "page": 2},
    {"level": "H3", "text": "Sub-subsection", "page": 3}
  ]
}
```

## Troubleshooting

**Import Error: No module named 'fitz'**
- Run: `pip install PyMuPDF`

**Permission Errors**
- Try: `pip install --user PyMuPDF regex`

**No PDFs found**
- Make sure PDF files are in the `input/` folder
- Check file extensions are `.pdf`

**Empty results**
- The PDF might be image-based without text
- Try with a different PDF that has selectable text
"""
    
    with open("README_LOCAL.md", "w", encoding='utf-8') as f:
        f.write(readme_content)
    print("✅ Created README_LOCAL.md with instructions")

def main():
    """Main setup function"""
    print("🚀 PDF Outline Extractor - Local Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Install dependencies
    print("\n📦 Installing Dependencies...")
    if not install_dependencies():
        print("\n⚠️  Some dependencies failed to install.")
        print("💡 You can try manually: pip install PyMuPDF regex")
        print("💡 Or with user flag: pip install --user PyMuPDF regex")
    
    # Create directories
    print("\n📁 Setting up directories...")
    create_directories()
    
    # Create local README
    print("\n📖 Creating documentation...")
    create_sample_readme()
    
    print("\n🎉 Setup complete!")
    print("\n📋 Next steps:")
    print("1. Place PDF files in the 'input' folder")
    print("2. Run: python process_pdfs_local.py")
    print("   OR double-click: run_pdf_extractor.bat")
    print("3. Check results in the 'output' folder")
    print("\n📖 See README_LOCAL.md for detailed instructions")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())