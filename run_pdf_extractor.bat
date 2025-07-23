@echo off
title PDF Outline Extractor - Windows
echo ========================================
echo PDF Outline Extractor - Windows Setup
echo ========================================

echo.
echo 1. Installing dependencies...
pip install PyMuPDF regex
if %errorlevel% neq 0 (
    echo Failed to install with pip, trying with --user flag...
    pip install --user PyMuPDF regex
)

echo.
echo 2. Running the PDF extractor...
python process_pdfs_local.py

echo.
echo Done!
pause