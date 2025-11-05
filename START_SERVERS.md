# Starting the Servers

This guide explains how to start the backend and frontend servers with visible logs.

## Quick Start

### Option 1: Using the Startup Scripts (Recommended)

1. **Start Backend Server:**
   ```bash
   ./start-backend.sh
   ```
   This will:
   - Activate the Python virtual environment
   - Install dependencies if needed
   - Start the FastAPI server on `http://localhost:8000`
   - Show all logs in the terminal

2. **Start Frontend Server (in a new terminal):**
   ```bash
   ./start-frontend.sh
   ```
   This will:
   - Install npm dependencies if needed
   - Start the Vite dev server (usually on port 8080 or next available)
   - Show all logs in the terminal

### Option 2: Manual Start

**Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

**Frontend (in a new terminal):**
```bash
npm run dev
```

## Accessing the Application

- **Frontend:** http://localhost:8080 (or the port shown in terminal)
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs

## Using Meeting Transcripts Folder

1. Place your transcript files (.txt, .json, .srt) in the `meeting_transcripts` folder in the project root
2. The frontend will automatically scan this folder and list available files
3. Select a file from the "From Folder" tab to process it

## Troubleshooting

- **Backend won't start?** Check that port 8000 is not in use
- **Frontend won't start?** Check that ports 8080-8086 are not all in use
- **No transcript files found?** Make sure files are in `meeting_transcripts/` folder with .txt, .json, or .srt extensions
- **Processing errors?** Check the backend terminal for detailed error logs

