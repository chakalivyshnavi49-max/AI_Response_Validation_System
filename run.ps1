Set-Location $PSScriptRoot
if (!(Test-Path '.venv\Scripts\python.exe')) { python -m venv .venv }
& .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
