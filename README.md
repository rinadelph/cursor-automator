# Cursor Automation

A Python application that automates the process of clicking "Run Command" buttons in Cursor IDE using OCR and GUI automation.

## Features

- User-friendly GUI interface
- Region selection for button detection
- OCR-based text recognition
- Automatic Ctrl+Enter execution
- Error handling and logging
- Pause/Resume functionality

## Requirements

- Python 3.8+
- Tesseract OCR
- Required Python packages (see requirements.txt)

## Installation

1. Install Tesseract OCR:
   - Windows: Download and install from [GitHub Tesseract Release](https://github.com/UB-Mannheim/tesseract/wiki)
   - Linux: `sudo apt-get install tesseract-ocr`
   - Mac: `brew install tesseract`

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
   python cursor_automation.py
   ```

2. Click "Select Region" and select the area where the "Run Command" button appears
3. Click "Start" to begin automation
4. Use the Pause/Resume button to control the automation

## Configuration

- The application creates a `logs` directory for logging information
- Adjust the selection timeout in the code if needed (default: 30 seconds)
- OCR settings can be modified in the code for better recognition

## License

MIT License - see LICENSE file for details 