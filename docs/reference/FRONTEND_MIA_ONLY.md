# Frontend Simplified for MIA-Only Testing

## Overview
The frontend has been updated to focus exclusively on testing the Meeting Intelligence Agent (MIA). REA (Requirement Extraction Agent) functionality has been removed/hidden and will be integrated later.

## Changes Made

### 1. Main Page (`src/pages/Index.tsx`)
- ✅ Removed REA output state and processing logic
- ✅ Removed workflow mode selector (only MIA workflow now)
- ✅ Simplified agent states to only include MIA
- ✅ Removed tabs - now shows only MIA output directly
- ✅ Updated header title to "Meeting Intelligence Agent (MIA)"
- ✅ Streamlined `handleProcess` to only handle MIA processing

### 2. Workflow Canvas (`src/components/WorkflowCanvas.tsx`)
- ✅ Simplified to show: Transcript Files → MIA Agent
- ✅ Removed REA agent node
- ✅ Removed workflow mode branching logic
- ✅ Updated to show simple single-agent flow

### 3. Export Buttons (`src/components/ExportButtons.tsx`)
- ✅ Removed CSV export format (was REA-specific)
- ✅ Simplified to only export JSON and Markdown for MIA
- ✅ Removed REA sections from markdown export
- ✅ Updated file naming to use `mia_report_` prefix

### 4. Config Panel (`src/components/ConfigPanel.tsx`)
- ✅ Removed CSV option from output format selector
- ✅ Only JSON and Markdown formats available now
- ✅ Kept Model Strategy and Preprocessing options (MIA-specific)

### 5. Type Definitions (`src/types/agent.ts`)
- ✅ Updated `AgentConfig.outputFormat` to only allow `'json' | 'markdown'`
- ✅ Removed `'csv'` option

## Current Workflow

1. **Upload Transcript**
   - User uploads transcript file (TXT, JSON, or SRT)
   - File is uploaded to backend

2. **Configure Settings**
   - Model Strategy: local, remote, or hybrid
   - Preprocessing: basic or advanced
   - Confidence Threshold: 0-100%
   - Output Format: JSON or Markdown

3. **Process Transcript**
   - Click "Process Transcript" button
   - Backend processes the transcript through MIA
   - Real-time progress updates shown in workflow canvas
   - Status polling until completion

4. **View Results**
   - Meeting summary
   - Key decisions with speakers and confidence
   - Action items with owners, due dates, priorities
   - Identified risks
   - Meeting participants

5. **Export Results**
   - Export as JSON or Markdown
   - Server-side export (if jobId available) or client-side fallback
   - Preview in browser console

## Files Not Modified (REA Components Still Exist)
- `src/components/REAOutput.tsx` - Not used but kept for future integration
- `src/components/WorkflowModeSelector.tsx` - Not used but kept for future
- `src/types/agent.ts` - REA types kept but not used in current workflow

## Testing MIA

1. **Start Backend**:
   ```powershell
   cd backend
   .\venv\Scripts\Activate.ps1
   uvicorn app.main:app --reload
   ```

2. **Start Frontend** (after installing Node.js):
   ```powershell
   npm install
   npm run dev
   ```

3. **Test Flow**:
   - Upload a transcript file from `backend/tests/`
   - Configure settings (or use defaults)
   - Click "Process Transcript"
   - Wait for processing to complete
   - Review MIA results
   - Export results if needed

## Future Integration Points

When ready to add REA back:
1. Restore workflow mode selector
2. Add REA agent state and processing logic
3. Re-enable REA output tab/component
4. Add CSV export back for REA user stories
5. Update workflow canvas to show MIA → REA flow

## Notes
- All REA-related code has been commented out or removed from the active workflow
- REA components/types are preserved for easy future integration
- Backend API endpoints for REA are not yet implemented (focus is on MIA Sprint 1)
