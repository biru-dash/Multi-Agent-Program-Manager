# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Setup Backend

```bash
cd backend

# Activate virtual environment (if not already activated)
venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Unix/MacOS

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Create .env file (if not exists)
# Copy from .env.example and add your HUGGINGFACE_TOKEN
```

### Step 2: Start Backend Server

```bash
# In backend directory, with venv activated
uvicorn app.main:app --reload
```

✅ Backend running at: `http://localhost:8000`  
✅ API docs at: `http://localhost:8000/docs`

### Step 3: Setup Frontend

Open a **new terminal**:

```bash
# From project root
npm install

# Create .env file (if not exists)
echo "VITE_API_BASE_URL=http://localhost:8000" > .env
```

### Step 4: Start Frontend Server

```bash
npm run dev
```

✅ Frontend running at: `http://localhost:5173`

### Step 5: Test the System

1. Open `http://localhost:5173` in your browser
2. Drag and drop `backend/tests/sample_transcript.txt` onto the upload area
3. Click "Process"
4. Wait for results (30-60 seconds for first run)
5. Review extracted insights!

## 🧪 Run Automated Tests

```bash
cd backend
venv\Scripts\activate
python test_api.py
```

## 📋 Checklist

- [ ] Backend dependencies installed
- [ ] Backend `.env` file created with `HUGGINGFACE_TOKEN`
- [ ] Backend server running on port 8000
- [ ] Frontend dependencies installed
- [ ] Frontend `.env` file created
- [ ] Frontend server running on port 5173
- [ ] Test file uploaded successfully
- [ ] Processing completes without errors
- [ ] Results displayed correctly

## 🆘 Common Issues

**Backend won't start?**
- Check if port 8000 is already in use
- Verify `.env` file exists with `HUGGINGFACE_TOKEN`
- Make sure you're in `backend/` directory

**Frontend can't connect?**
- Verify backend is running
- Check `VITE_API_BASE_URL` in frontend `.env`
- Check browser console for CORS errors

**Processing takes too long?**
- First run downloads models (several GB)
- Use `hybrid` strategy for faster results
- Check backend logs for progress

For detailed testing instructions, see [TESTING.md](./TESTING.md)
