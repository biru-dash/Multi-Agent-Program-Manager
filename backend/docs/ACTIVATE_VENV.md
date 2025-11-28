# How to Activate Virtual Environment in PowerShell (Windows)

## Problem
If you see this error:
```
venv\Scripts\activate : The module 'venv' could not be loaded
```

## Solutions

### Option 1: Use Full Path with PowerShell Script (Recommended)
```powershell
.\venv\Scripts\Activate.ps1
```

### Option 2: If You Get Execution Policy Error
If PowerShell blocks the script execution, you may need to change the execution policy:

**For current session only (safest):**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\venv\Scripts\Activate.ps1
```

**Or run:**
```powershell
& .\venv\Scripts\Activate.ps1
```

### Option 3: Use Command Prompt (CMD) Instead
If PowerShell continues to give issues, you can use CMD:
```cmd
venv\Scripts\activate.bat
```

## Create Virtual Environment (if it doesn't exist)
```powershell
py -m venv venv
```

## Verify Activation
After activation, you should see `(venv)` at the start of your prompt:
```
(venv) PS C:\Users\...\backend>
```

## Deactivate
To deactivate the virtual environment:
```powershell
deactivate
```

## Quick Setup Script
Run these commands in sequence:
```powershell
# 1. Create venv (if doesn't exist)
py -m venv venv

# 2. Activate it
.\venv\Scripts\Activate.ps1

# 3. Upgrade pip
python -m pip install --upgrade pip

# 4. Install requirements
pip install -r requirements.txt
```
