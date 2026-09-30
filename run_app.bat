@echo off
REM Interest Rate Calculator - create a virtual environment (first run only) and start the app.
cd /d "%~dp0"
if not exist .venv (
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)
streamlit run app.py
