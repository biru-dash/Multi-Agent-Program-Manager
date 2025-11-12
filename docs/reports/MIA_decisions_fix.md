🧠 Step 1. Diagnose the Root Gap
✅ What the Agent Is Doing Now

Your current results show:

Extraction of individual decision-like sentences with some “High” confidence score.

It’s catching explicit language like “We decided…”, “Marcus, do this…”, etc.

But it’s missing structured synthesis — it doesn’t group or reason across turns, and doesn’t normalize into themes (e.g., “Launch Date Change,” “Feature Set,” etc.).

❌ What’s Missing

Contextual aggregation: Multiple statements belong to one larger decision.

Implicit decisions: It’s missing decisions expressed indirectly (“Let’s move the launch two weeks later” vs “We decided to move launch”).

Temporal and relational reasoning: It’s not linking decisions to timelines, owners, or categories.

Decision titles or grouping logic: Desired output has high-level headers summarizing themes (e.g., “Launch Date Change”), but current results just have raw lines.

⚙️ Step 2. Engineering Next Steps (By Category)
1️⃣ Improve Upstream Chunking / Context Window

Your current model is probably reading text sentence by sentence or in short chunks.
That’s too shallow for decisions which unfold over multi-speaker exchanges.

Actions:

Process meetings in larger semantic windows (e.g., 500–1000 tokens).

Use semantic chunking rather than fixed token windows.

from semantic_text_splitter import TextSplitter
splitter = TextSplitter.from_huggingface_model('all-MiniLM-L6-v2')
chunks = splitter.chunks(transcript, max_tokens=1000)


Pass each chunk through the decision extractor model and then aggregate results.

2️⃣ Upgrade Decision Extraction Prompts / Model

Current extraction looks like a simple “find statements that include ‘decide’”.
You need reasoning-based summarization, not rule-based filtering.

Actions:

Use a reasoning-tuned model (e.g., mistral, llama3, or phi3) via Ollama or a hosted LLM like Mixtral-8x7B-Instruct.

Prompt it to:

Identify all possible decisions, including implied ones.

Consolidate duplicates.

Group them under thematic categories.

Example Prompt:

You are a meeting summarization assistant. Read the following transcript and extract all key decisions.
1. Combine fragmented or repeated decisions into one.
2. Infer decisions even when not stated explicitly (e.g., “let’s move the date” → launch date change).
3. Output as a JSON array with the structure:
[
  {
    "title": "<short name of decision>",
    "summary": "<concise description>",
    "details": [ "<supporting statements>" ]
  }
]
Transcript:
{{chunk}}


Optional improvement: Use function calling / JSON schema prompting if your LLM supports it (Ollama models like Llama 3 often handle this well).

3️⃣ Add a Post-Processing Aggregation Step

Your desired output shows hierarchical grouping (Launch Date Change, Feature Set, Go-To-Market, etc.).
This grouping can be an additional pass after initial extraction.

Actions:

Run a clustering or LLM summarization pass over all extracted decisions:

prompt = """
Group the following decisions into thematic categories and produce concise section titles:
{{all_decisions}}
"""


Use embeddings (nomic-embed-text or sentence-transformers) to group similar decision summaries (e.g., all related to “features” or “launch plan”).

4️⃣ Incorporate Implicit Decision Detection (Reasoning Layer)

Most missed cases (like timeline changes or gating criteria) are implicit decisions.
They rely on temporal reasoning or conditional logic.

Actions:

Fine-tune or instruction-tune a small model (e.g., phi3-mini) using examples like:

Input: paragraph of meeting dialogue

Output: "Decision: Launch moved from Oct 15 → Oct 29 to allow buffer"

Alternatively, run a two-step reasoning pipeline:

Use a QA model to answer “What was decided about launch, timeline, features, audit, etc.?”

Merge results into final decision summary.

5️⃣ Add Decision-Type Classification

Your output needs structure like “Launch Date Change,” “Feature Set,” “Features Cut.”
Train or prompt a classifier to categorize each decision.

Actions:

Build a taxonomy of decision types: ["timeline", "feature", "budget", "security", "go-to-market", "meeting cadence"].

Either:

Use zero-shot classification (facebook/bart-large-mnli on Hugging Face).

Or prompt your LLM:

For each decision, assign a category: [timeline, feature, budget, security, communication, other]

6️⃣ Fine-tune or few-shot train on target output format

To move from “sentence list” → “structured grouped output,” it helps to fine-tune on a few examples like the “desired results” you showed.

Actions:

Collect 20–50 meetings annotated in your desired structure.

Use LoRA fine-tuning (e.g., mistral-7b or phi3) with your JSON schema.

Hugging Face tools: trl + peft for instruction tuning.

🧩 Step 3. Model Recommendations (Local + Open Source)
Purpose	Ollama Model	Alt (Hugging Face)	Notes
Semantic chunking	nomic-embed-text	all-MiniLM-L6-v2	for similarity-based grouping
Decision extraction	mistral / phi3	Mixtral-8x7B-Instruct, Llama-3-8B-Instruct	capable of JSON structured reasoning
Grouping & reasoning	llama3	DeepSeek-Coder-V2 or Claude 3 Haiku	for “thematic summarization”
Classification	phi3-mini	facebook/bart-large-mnli	for labeling decision types
🧠 Step 4. Example Multi-Pass Pipeline
# Step 1: Semantic chunking
chunks = semantic_chunk(transcript)

# Step 2: Extract raw decisions per chunk
decisions = [extract_decisions(chunk) for chunk in chunks]

# Step 3: Aggregate and deduplicate
merged = aggregate_decisions(decisions)

# Step 4: Group into themes
grouped = group_decisions(merged)

# Step 5: Format into final structured summary
summary = generate_final_json(grouped)


Each step can use an LLM or embedding model optimized for that specific reasoning layer.

🧾 Step 5. Validation Framework

To know you’re improving, build an evaluation harness:

Compare generated decisions vs. ground truth using:

Semantic similarity (cosine sim on sentence embeddings)

Overlap in unique themes (timeline, feature, budget, etc.)

Human annotation precision/recall

That lets you quantify improvement as you iterate.