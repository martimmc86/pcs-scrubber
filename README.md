# Merlon Scrubber — Windows Build Instructions

## Prerequisites
- Python 3.10+ installed on Windows
- pip available in PATH

## Build Steps

1. Open Command Prompt or PowerShell in this directory

2. Create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Build the executable:
   ```
   pyinstaller --windowed --onedir --name "Merlon Scrubber" --icon icon.ico --add-data "icon.png;." --add-data "icon.ico;." --noconfirm merlon_scrubber.py
   ```

5. The built application will be in `dist\Merlon Scrubber\`

6. To run: double-click `dist\Merlon Scrubber\Merlon Scrubber.exe`

## Notes
- The `tkinterdnd2` package enables drag-and-drop on Windows
- If drag-and-drop doesn't work, the file chooser button is always available
- The app uses Consolas font on Windows for the dark theme
