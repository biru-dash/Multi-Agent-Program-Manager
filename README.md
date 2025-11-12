# Meeting Intelligence Agent (MIA)

A multi-agent system for extracting structured insights from meeting transcripts using Hugging Face models.

## Features

- **Multi-format Support**: Upload transcripts in TXT, JSON, or SRT format
- **Advanced Preprocessing**: Filler removal, speaker normalization, topic segmentation
- **Flexible Model Strategy**: Choose between local, remote (HF API), or hybrid inference
- **Structured Extraction**: Automatically extract decisions, action items, risks, and owners
- **Confidence Scoring**: Each extracted item includes a confidence score
- **Export Options**: Download results as JSON or Markdown

## Tech Stack

### Backend
- Python 3.10+
- FastAPI
- Hugging Face Transformers
- Sentence Transformers
- scikit-learn

### Frontend
- React 18
- TypeScript
- Vite
- Tailwind CSS
- shadcn-ui

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- Node.js 18+ and npm
- Hugging Face account with API token (for remote/hybrid strategies)

### Backend Setup

1. **Clone and navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   # Windows
   py -m venv venv
   venv\Scripts\activate

   # Unix/MacOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create `.env` file in backend directory:**
   ```env
   HUGGINGFACE_TOKEN=your_token_here
   MODEL_STRATEGY=hybrid
   UPLOAD_DIR=./uploads
   OUTPUT_DIR=./outputs
   MAX_FILE_SIZE_MB=50
   SUMMARIZATION_MODEL=knkarthick/bart-large-xsum-samsum
   NER_MODEL=dslim/bert-base-NER
   EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
   ```

5. **Start the backend server:**
   ```bash
   uvicorn app.main:app --reload
   ```

   The API will be available at `http://localhost:8000`
   API documentation: `http://localhost:8000/docs`

### Frontend Setup

1. **Navigate to project root (where package.json is located)**

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Create `.env` file in project root:**
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   ```

4. **Start the development server:**
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:5173`

## Usage

1. **Upload a transcript file** (TXT, JSON, or SRT format)
2. **Configure settings:**
   - Model Strategy: Choose local, remote, or hybrid
   - Preprocessing: Choose basic or advanced
3. **Click "Process"** to start analysis
4. **View results** in the output panel
5. **Export results** as JSON or Markdown

## Meeting Summary Pipeline

The meeting summary that appears in the UI is produced entirely in the backend through the `MeetingExtractor` pipeline defined in `backend/app/extraction/extractor.py`. The end-to-end flow is:

1. **Transcript preprocessing** (`backend/app/preprocessing/cleaner.py`):
   - `TranscriptCleaner.process` removes greetings, small talk, and filler speech.
   - Consecutive short turns from the same speaker are merged for better context.
   - Speaker names are normalized and (optionally) segments are grouped by topic using embeddings.
   ```text
   Before: "Hey everyone, uh yeah just wanted to kick things off... okay so I think launch is October 15."
   After:  "Just wanted to kick things off. I think launch is October 15."
   ```

2. **Hierarchical summarization** (`MeetingExtractor.extract_summary`):
   - Cleansed transcript is chunked into ~500–700 token windows using semantic chunking when embeddings are available, otherwise a word-based fallback.
   - Each chunk is summarized through `ModelAdapter.summarize`.
   - `_hierarchical_summarize` recursively combines partial summaries into a single narrative.
   ```text
   Before: 1,200-word raw discussion with repeated status updates.
   After:  "The team reviewed launch blockers, confirmed feature readiness, and aligned on timeline adjustments."
   ```

3. **Structured reasoning support** (`MeetingExtractor.extract_structured_data`):
   - Specialized extractors (decisions, actions, risks) in `backend/app/extraction/specialized_extractors.py` analyze the same segments.
   - Provenance tracking anchors each item to supporting transcript spans.
   - Semantic confidence scoring and validation prune low-quality signals and push results to the frontend.
   ```text
   Before: "We’ll push beta two weeks and Alex owns the risk mitigation."
   After:  Decision → "Push beta to Oct 29"; Action → "Alex to drive mitigation plan"; Risk → "Timeline slip if QA fails."
   ```

4. **Executive summary synthesis** (`MeetingExtractor._synthesize_executive_summary`):
   - The initial narrative summary, structured artifacts, and derived metadata (meeting type, duration estimate, main topic) are combined.
   - A templated prompt re-invokes `ModelAdapter.summarize` to ensure required factual elements (dates, metrics, before/after decisions) are present.
   - Result is a polished two to three paragraph executive summary ready for the UI.
   ```text
   Before: "Discussed launch plan and risk mitigation."
   After:  "The planning session was a 45-minute review of the launch program, confirming the move from Oct 15 to Oct 29, highlighting four critical blockers, and assigning three mitigation owners."
   ```

5. **Quality gating** (`MeetingExtractor.process`):
   - Redundancy, coverage, and confidence metrics are calculated for the synthesized summary.
   - If thresholds are not met, the system falls back to the hierarchical summary to avoid hallucinated structure.
   - The UI receives both the final summary and a quality warning flag when confidence is low.

   This pipeline ensures that the displayed meeting summary is grounded in the cleaned transcript, preserves quantitative details, and aligns with the structured outputs surfaced elsewhere in the app.

## Model Strategy Options

- **Hybrid** (Recommended): Uses local models for extraction, HF API for summarization
- **Local**: Runs all models locally (requires GPU for best performance)
- **Remote**: Uses Hugging Face Inference API for all tasks

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes
│   │   ├── config/       # Configuration settings
│   │   ├── extraction/   # Information extraction pipeline
│   │   ├── models/       # Model adapters
│   │   ├── preprocessing/ # Transcript preprocessing
│   │   ├── utils/        # Utility functions
│   │   └── main.py       # FastAPI app entry point
│   ├── tests/
│   ├── uploads/          # Uploaded transcript files
│   └── outputs/          # Processing results
├── src/
│   ├── components/       # React components
│   ├── services/         # API service client
│   ├── pages/            # Page components
│   └── types/            # TypeScript types
└── venv/                 # Python virtual environment (git-ignored)
```

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests (if configured)
npm test
```

### Building for Production

```bash
# Frontend
npm run build

# Backend (using Docker)
docker build -t mia-backend ./backend
```

## Notes

- Models are cached locally in `backend/models_cache/` to avoid repeated downloads
- First run may take longer as models are downloaded
- For best performance with local models, a GPU is recommended
- Free Hugging Face API tier has rate limits

## License

[Your License Here]
