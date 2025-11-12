## 🧱 SYSTEM GOAL

> Create a robust, explainable, and user-friendly evaluation + interaction framework for the Meeting Intelligence Agent (MIA), enabling automated scoring, human review, and interactive feedback loops while minimizing cost and latency.

---

## 🔧 ENGINEERING NEXT STEPS — FULL PIPELINE

---

### 🧩 **Step 1 — Define the Evaluation Schema (Backend + Frontend Shared Contract)**

**Deliverable:**
`evaluation_schema.json` stored in repo and used by both LLM evaluators and UI.

**Example Schema:**

```json
{
  "summary": ["coverage", "factuality", "clarity"],
  "decisions": ["specificity", "completeness", "clarity"],
  "action_items": ["owner", "timeline", "clarity", "priority"],
  "risks": ["impact", "likelihood", "specificity"]
}
```

**Why:**

* Ensures consistency across backend LLM evaluations and frontend human scoring UI.
* Enables dynamic UI generation from schema.

---

### 🧠 **Step 2 — Automated Evaluation (LLM-as-a-Judge)**

**Deliverable:**
`evaluation_chain.py` using LangChain.

**What to do:**

* Create a `RunnableSequence` chain per component (summary, decisions, etc.).
* Use deterministic model (e.g., `gpt-4o-mini` or local `mistral`) for stable scoring.
* Return both **scores** and **explanations** for transparency.

**Frontend Integration:**

* Display LLM evaluation results in expandable panels with rationale text.
* Example:

  > *Coverage: 8/10* — “The summary missed the decision about the go-to-market timeline.”

**Key Considerations:**

* Add version tags (`judge_model`, `prompt_version`) for traceability.
* Cache evaluations using LangChain’s cache or Redis to reduce token spend.

---

### 🧑‍⚖️ **Step 3 — Human-in-the-Loop Review (HITL)**

**Deliverable:**

* `human_review_ui.py` (Streamlit, React, or Shadcn/UI)
* `review_api.py` for storing human feedback.

**Workflow:**

1. Display MIA output alongside ground truth (if available).
2. Allow rating per criterion (e.g., coverage, factuality) using sliders or dropdowns.
3. Collect free-text rationale (“Why did you give this rating?”).
4. Store results in a table:

   ```
   evaluation_results (
     transcript_id,
     component,
     criterion,
     llm_score,
     human_score,
     rationale,
     version,
     timestamp
   )
   ```

**Frontend Improvements:**
✅ Add **side-by-side comparison view** for ground truth vs model output.
✅ Provide **one-click feedback**: “Good”, “Partially Correct”, “Incorrect”.
✅ Show **explanations from LLM judge** next to each score for context.
✅ Let reviewers mark **examples for re-training** (checkbox).

**Important Backend Note:**
Use versioning for both `model_version` and `prompt_version` so you can compare outputs across iterations.

---

### ⚙️ **Step 4 — Combine LLM + Human Evaluations**

**Deliverable:**
`evaluation_aggregator.py`

**Logic Example:**

```python
if human_score:
    final_score = 0.7 * llm_score + 0.3 * human_score
else:
    final_score = llm_score
```

Store this in a single evaluation record with source metadata:

```json
{
  "component": "summary",
  "source": ["llm", "human"],
  "final_score": 0.87,
  "explanation": "LLM agreed with human on coverage, diverged on factuality"
}
```

**Frontend:**

* Add “Confidence Meter” (e.g., Low / Medium / High) based on LLM–Human agreement.
* Display **delta values** visually to highlight disagreement.

---

### 📊 **Step 5 — Metric-Based Evaluation (Non-LLM)**

**Deliverable:**
`metrics_evaluator.py`

Add traditional metrics:

* Summaries → ROUGE, BERTScore
* Decisions/Actions → Precision/Recall/F1
* Risks → Entity recall (impact, owner, etc.)

**Frontend:**

* Visualization panel for objective metrics (bar charts or radar plots).
* Tooltip explanations: “ROUGE measures overlap between reference and model summary.”

---

### 🧩 **Step 6 — Evaluation Orchestration & Observability**

**Deliverable:**

* `evaluation_runner.py` (LangChain LCEL workflow)
* LangSmith integration for run logging.

**Backend Tasks:**

* Log all evaluations with metadata (`model_version`, `criteria`, `timestamp`).
* Use LangSmith to visualize runs, compare across versions, and detect regressions.

**Frontend Improvements:**

* Create an **Evaluation Dashboard**:

  * Filter by date, transcript, or model version.
  * Show trend lines for summary/decision/risk scores.
  * Add “Compare v1.0 vs v1.1” toggle.

---

### 🔁 **Step 7 — Continuous Feedback Loop**

**Deliverable:**
`feedback_loop.py`

**Pipeline:**

1. Low-scoring examples are auto-flagged.
2. Human reviewers mark “train this” or “prompt needs fix”.
3. Feed these examples to fine-tuning or RAG database.

**Frontend:**

* Add a “Flag for retraining” button on any MIA output.
* Show a list of flagged items to review before re-training.

---

### 💬 **Step 8 — Chat Interface Integration**

**Goal:**
Allow users to chat with MIA and reference evaluation data naturally.

**Example Queries:**

> “How accurate were the last 10 meeting summaries?”
> “Show me all meetings where coverage was below 80%.”
> “Compare v1.2 vs v1.3 decisions extraction performance.”

**Implementation:**

* LangChain Agent with tools:

  * `fetch_eval_results`
  * `compare_versions`
  * `get_low_confidence_meetings`
* Query evaluation data (from Postgres or LangSmith API).

**Frontend:**

* Chat window that supports **data-backed responses**:

  * When the user asks about model performance, show text + small chart.
  * Support follow-ups like “Why?” → MIA explains using stored LLM rationale.

---

### 🎨 **Step 9 — Frontend Enhancements Summary**

| Area                     | Improvement                               | Benefit                 |
| ------------------------ | ----------------------------------------- | ----------------------- |
| **Evaluation Display**   | Side-by-side views, expandable rationales | Transparency            |
| **Reviewer UI**          | Schema-driven sliders, comment boxes      | Consistency             |
| **Dashboard**            | Trend lines, comparison view              | Version visibility      |
| **Chat Integration**     | Data-aware responses                      | Interactive exploration |
| **Feedback System**      | One-click “Flag for retraining”           | Continuous improvement  |
| **Explainability Layer** | Show rationale from judge model           | Trust-building          |

If you’re using React + Shadcn/UI:

* Use `Tabs` for switching between “Summary”, “Decisions”, “Actions”, “Risks”.
* Use `Accordion` for detailed rationale expansion.
* Use `Progress` or `Radar` components for evaluation metrics.

---

### 🧩 **Step 10 — Cost Optimization + Persistence**

* Cache identical transcript evaluations (`hash(transcript_text)`).
* Store only deltas when model version changes.
* For transcripts >50k tokens:

  * Chunk them → summarize per section → merge results before scoring.

**Frontend Helper:**

* Show a **“Cached” label** next to results reused from prior runs.
* Indicate which parts were re-evaluated.

---

## 🚀 Final Deliverables Summary

| Category          | Deliverable                                           | Description                             |
| ----------------- | ----------------------------------------------------- | --------------------------------------- |
| **Schema**        | `evaluation_schema.json`                              | Shared criteria for LLM + UI            |
| **Evaluation**    | `evaluation_chain.py`, `metrics_evaluator.py`         | Automated evaluation                    |
| **Aggregation**   | `evaluation_aggregator.py`                            | Combine LLM, metrics, and human results |
| **Frontend UI**   | `review_ui`, `evaluation_dashboard`, `chat_interface` | Human review + visualization            |
| **Storage**       | `evaluation_results` table                            | Unified persistence layer               |
| **Feedback Loop** | `feedback_loop.py`                                    | Continuous improvement workflow         |
| **Observability** | LangSmith + Prometheus/Grafana                        | Track model regressions and cost        |
| **Caching**       | Redis / SQLite                                        | Reduce duplicate evaluations            |