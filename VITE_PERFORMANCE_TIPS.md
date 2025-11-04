# Vite Dev Server Performance Optimization

## Why Is It Slow?

If `http://localhost:8080` (or 8081) is refreshing slowly, it's likely because Vite is watching too many files, including:

1. **Python virtual environment** (`venv/`) - thousands of Python files
2. **Backend directory** (`backend/`) - Python files that don't need watching
3. **Node modules** - large dependency directories
4. **Large files** in the project root
5. **File watcher limitations** on Windows

## ✅ Already Fixed

I've updated `vite.config.ts` to exclude these directories from file watching:
- `backend/` - Python backend files
- `venv/` - Python virtual environment
- `node_modules/` - Dependencies
- `.git/` - Git files
- Python files (`*.py`)
- Cache and output directories

## Additional Optimizations

### 1. Clear Vite Cache (if issues persist)

```powershell
# Stop the dev server (Ctrl+C)
# Then clear cache:
Remove-Item -Recurse -Force .vite -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force node_modules/.vite -ErrorAction SilentlyContinue

# Restart dev server
npm run dev
```

### 2. Check Port Configuration

**Note**: Your `vite.config.ts` is set to port **8080**, but you mentioned accessing **8081**. 

- If you're using port 8081, update the config or check if something else is running on 8081
- Check what's running:
  ```powershell
  Get-NetTCPConnection -LocalPort 8080,8081 | Select-Object LocalPort, State
  ```

### 3. Move Large Files Out of Project Root

If you have large files (like `Aftermarket Revenue Visibility_ Discovery read-out.txt` - 38KB), consider:
- Moving them to `docs/` or another subdirectory
- Or add them to `.gitignore` if not needed

### 4. Disable Component Tagger in Development (Optional)

The `lovable-tagger` plugin can slow things down. If you don't need it, you can disable it:

```typescript
// In vite.config.ts, temporarily comment out:
plugins: [react()], // componentTagger() disabled
```

### 5. Use Windows WSL2 (Alternative)

If you're on Windows, file watching can be slower. Consider:
- Using WSL2 (Windows Subsystem for Linux) for development
- Or using a different file watcher: `npm install -D chokidar`

### 6. Increase File Watcher Limits (Windows)

Windows has default limits on file watchers. To increase:

```powershell
# Run as Administrator
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

Then restart your computer.

## Quick Performance Check

1. **Check what Vite is watching**:
   - Look at the terminal output when you start `npm run dev`
   - It should show "Local: http://localhost:8080"
   - No warnings about too many watched files

2. **Test refresh speed**:
   - Make a small change to a React component
   - It should update in < 100ms typically
   - If it takes > 1 second, something is wrong

3. **Monitor CPU/Network**:
   - Open Task Manager
   - Watch Node.js process when you save a file
   - Should spike briefly then return to normal

## Expected Performance

After optimizations:
- **Initial load**: 1-3 seconds (first time)
- **Hot reload**: < 100ms (file changes)
- **Full page reload**: < 500ms

## Troubleshooting

### Still slow after optimizations?

1. **Check if backend is interfering**:
   ```powershell
   # Make sure backend is on different port (8000)
   # Not running on 8080/8081
   ```

2. **Verify exclusions are working**:
   - Make a change in `backend/app/main.py`
   - Frontend should NOT reload (if it does, exclusions aren't working)

3. **Clear all caches**:
   ```powershell
   Remove-Item -Recurse -Force .vite, node_modules/.vite, dist -ErrorAction SilentlyContinue
   npm run dev
   ```

4. **Check antivirus**:
   - Some antivirus software scans file changes
   - Add project folder to exclusions

## Current Configuration

Your `vite.config.ts` now includes:
- ✅ File watcher exclusions for `backend/`, `venv/`, `node_modules/`
- ✅ Optimized dependency pre-bundling
- ✅ HMR improvements
- ✅ Build optimizations

Restart your dev server to apply changes:
```powershell
# Stop current server (Ctrl+C)
npm run dev
```
