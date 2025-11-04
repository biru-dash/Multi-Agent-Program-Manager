# Node.js/npm Setup Guide for Windows

## Problem
If you see:
```
npm : The term 'npm' is not recognized
```

This means Node.js is not installed or not in your PATH.

## Solution: Install Node.js

### Option 1: Download from Official Website (Recommended)

1. **Download Node.js**:
   - Go to: https://nodejs.org/
   - Download the **LTS (Long Term Support)** version
   - Choose the Windows Installer (.msi) for your system (64-bit recommended)

2. **Install**:
   - Run the installer
   - Follow the installation wizard (use default settings)
   - Make sure "Add to PATH" is checked during installation

3. **Verify Installation**:
   - Close and reopen PowerShell
   - Run:
     ```powershell
     node --version
     npm --version
     ```
   - You should see version numbers

### Option 2: Install via Winget (Windows Package Manager)

If you have Winget installed:
```powershell
winget install OpenJS.NodeJS.LTS
```

Then restart PowerShell and verify:
```powershell
node --version
npm --version
```

### Option 3: Install via Chocolatey

If you have Chocolatey installed:
```powershell
choco install nodejs-lts
```

## After Installation

1. **Close and reopen PowerShell** (important for PATH changes to take effect)

2. **Verify installation**:
   ```powershell
   node --version
   npm --version
   ```

3. **Navigate to project root and install dependencies**:
   ```powershell
   cd "C:\Users\birup\OneDrive\Documents\Code\Multi Agent Program Manager"
   npm install
   ```

4. **Create frontend .env file** (if not exists):
   ```powershell
   echo "VITE_API_BASE_URL=http://localhost:8000" > .env
   ```

5. **Start frontend**:
   ```powershell
   npm run dev
   ```

## Quick Check Commands

```powershell
# Check if Node.js is installed
node --version

# Check if npm is installed
npm --version

# Check if it's in PATH
where.exe node
where.exe npm
```

## Troubleshooting

**If node/npm still not recognized after installation:**
1. Close all PowerShell windows
2. Reopen PowerShell as Administrator
3. Try again

**If PATH issue persists:**
1. Check PATH manually:
   ```powershell
   $env:Path -split ';' | Select-String -Pattern 'node'
   ```
2. Node.js should be in: `C:\Program Files\nodejs\`
3. Add manually if needed (not recommended - reinstall is better)

## Alternative: Use nvm-windows (Node Version Manager)

If you need multiple Node.js versions:
1. Install nvm-windows from: https://github.com/coreybutler/nvm-windows/releases
2. Then install Node.js via nvm:
   ```powershell
   nvm install lts
   nvm use lts
   ```
