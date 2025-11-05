# MIA Model Requirements Guide

This document explains what types of models the Meeting Intelligence Agent (MIA) needs and what to look for when searching HuggingFace.

## Overview

MIA uses **4 types of models** to extract structured insights from meeting transcripts:

1. **Summarization Model** - Creates meeting summaries
2. **Named Entity Recognition (NER) Model** - Extracts people, organizations, locations
3. **Embedding Model** - Creates semantic embeddings for similarity/search
4. **Classification Model** (Optional) - Zero-shot classification for categorizing content

---

## 1. Summarization Model

### Purpose
- Generates concise summaries of meeting transcripts
- Handles long conversations (chunks text if needed)
- Creates abstractive summaries (not just extraction)

### What to Look For on HuggingFace

**Search Terms:**
- `summarization`
- `bart-summarization`
- `pegasus-summarization`
- `t5-summarization`
- `samsum` (conversational summarization)
- `cnn-dailymail` (news summarization, works for meetings)

**Model Characteristics:**
- ✅ Task: `summarization` or `text2text-generation`
- ✅ Trained on: SAMSum, CNN/DailyMail, XSum datasets
- ✅ Model types: BART, Pegasus, T5, mT5
- ✅ Size: Large models (base or large) for better quality
- ✅ Context window: 1024+ tokens (to handle long meetings)

**Recommended Model Families:**
- **BART models**: `facebook/bart-large-cnn`, `facebook/bart-large-xsum`
- **Pegasus models**: `google/pegasus-xsum`, `google/pegasus-cnn_dailymail`
- **T5 models**: `t5-base`, `t5-large` (for summarization)
- **Conversational**: Any model fine-tuned on SAMSum dataset

**What to Avoid:**
- ❌ Models that only extract sentences (extractive summarization)
- ❌ Models with very small context windows (< 512 tokens)
- ❌ Models marked as deprecated or archived

**Example Good Models:**
- `facebook/bart-large-cnn` (if available)
- `google/pegasus-xsum`
- `sshleifer/distilbart-cnn-12-6` (smaller, faster)
- `philschmid/bart-large-cnn-samsum` (if available)

---

## 2. Named Entity Recognition (NER) Model

### Purpose
- Extracts named entities: people names, organizations, locations, dates
- Identifies speakers and participants
- Helps with action item ownership

### What to Look For on HuggingFace

**Search Terms:**
- `ner`
- `named-entity-recognition`
- `token-classification`
- `bert-ner`

**Model Characteristics:**
- ✅ Task: `token-classification` or `ner`
- ✅ Labels: PER (person), ORG (organization), LOC (location), MISC
- ✅ Model types: BERT, RoBERTa, DistilBERT
- ✅ Size: Base models are usually sufficient
- ✅ Aggregation strategy: Should support "simple" or "max" aggregation

**Recommended Model Families:**
- **BERT-based**: `dslim/bert-base-NER` (currently used)
- **RoBERTa**: `xlm-roberta-base-finetuned-panx-all`
- **DistilBERT**: `distilbert-base-uncased` (if fine-tuned for NER)

**What to Avoid:**
- ❌ Models that don't support standard NER labels (PER, ORG, LOC)
- ❌ Models that require custom tokenization schemes

**Example Good Models:**
- `dslim/bert-base-NER` ✅ (currently used)
- `dbmdz/bert-large-cased-finetuned-conll03-english`
- `Jean-Baptiste/roberta-large-ner-english`

---

## 3. Embedding Model

### Purpose
- Creates semantic embeddings for text similarity
- Used for finding similar segments or topics
- Enables semantic search within transcripts

### What to Look For on HuggingFace

**Search Terms:**
- `sentence-transformers`
- `sentence-embedding`
- `semantic-similarity`
- `all-MiniLM` or `all-mpnet`

**Model Characteristics:**
- ✅ Library: `sentence-transformers` (not raw transformers)
- ✅ Task: Sentence similarity/embedding
- ✅ Output: Dense vector embeddings (384, 512, or 768 dimensions)
- ✅ Size: Base models are efficient (MiniLM, MPNet)
- ✅ Speed: Fast inference for real-time use

**Recommended Model Families:**
- **MiniLM**: `sentence-transformers/all-MiniLM-L6-v2` ✅ (currently used)
- **MPNet**: `sentence-transformers/all-mpnet-base-v2`
- **Universal Sentence Encoder**: `sentence-transformers/universal-sentence-encoder`

**What to Avoid:**
- ❌ Models that require special preprocessing
- ❌ Very large models (> 500MB) unless you have GPU
- ❌ Models that don't use sentence-transformers library

**Example Good Models:**
- `sentence-transformers/all-MiniLM-L6-v2` ✅ (currently used - fast & accurate)
- `sentence-transformers/all-mpnet-base-v2` (more accurate, slower)
- `sentence-transformers/paraphrase-MiniLM-L6-v2`

---

## 4. Classification Model (Optional)

### Purpose
- Zero-shot classification for categorizing content
- Classifies decisions, action items, risks
- Currently uses keyword matching as fallback

### What to Look For on HuggingFace

**Search Terms:**
- `zero-shot-classification`
- `mnli` (Multi-Genre Natural Language Inference)
- `nli` (Natural Language Inference)

**Model Characteristics:**
- ✅ Task: `zero-shot-classification` or `text-classification`
- ✅ Model types: BART-MNLI, RoBERTa-MNLI
- ✅ Can classify text into arbitrary labels without training

**Recommended Model Families:**
- **BART-MNLI**: `facebook/bart-large-mnli` (currently used)
- **RoBERTa-MNLI**: `roberta-large-mnli`
- **DistilBERT-MNLI**: `typeform/distilbert-base-uncased-mnli`

**Example Good Models:**
- `facebook/bart-large-mnli` ✅ (currently used)
- `valhalla/distilbart-mnli-12-3` (smaller, faster)

---

## Model Selection Criteria

### For Summarization Models:

1. **Check Availability:**
   - ✅ Model is active (not archived)
   - ✅ Inference API is available (if using hybrid/remote)
   - ✅ Model card shows recent activity

2. **Performance:**
   - ✅ ROUGE scores (for summarization quality)
   - ✅ Context window size (1024+ tokens preferred)
   - ✅ Model size (balance between quality and speed)

3. **Dataset Compatibility:**
   - ✅ Trained on conversational data (SAMSum) or news (CNN/DailyMail)
   - ✅ Abstractive summarization (not extractive)

### For NER Models:

1. **Label Support:**
   - ✅ Standard NER labels: PER, ORG, LOC, MISC
   - ✅ Aggregation strategy support

2. **Language:**
   - ✅ English language models
   - ✅ Multilingual if needed

### For Embedding Models:

1. **Library:**
   - ✅ Uses `sentence-transformers` library
   - ✅ Easy to integrate

2. **Performance:**
   - ✅ Fast inference
   - ✅ Good semantic similarity scores

---

## How to Test Models on HuggingFace

1. **Check Model Card:**
   - Look at the "Model Card" tab
   - Check if model is archived or deprecated
   - Review recent commits/updates

2. **Test Inference API:**
   - Use the "Hosted inference API" widget
   - Test with sample meeting transcript text
   - Verify it returns expected output format

3. **Check Model Size:**
   - Ensure model fits your hardware constraints
   - Consider download time for local models

4. **Review Documentation:**
   - Check required parameters
   - Verify input/output formats
   - Look for usage examples

---

## Current Configuration

```env
SUMMARIZATION_MODEL=philschmid/bart-large-cnn-samsum  # (Needs verification)
NER_MODEL=dslim/bert-base-NER                         # ✅ Working
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2 # ✅ Working
```

---

## Recommended Model Search Strategy

1. **Start with verified models:**
   - Look for models with high download counts
   - Check for recent updates
   - Read user comments/feedback

2. **Test multiple candidates:**
   - Try 2-3 models per category
   - Compare quality and speed
   - Check for API availability

3. **Consider fallbacks:**
   - Have backup models ready
   - Use local models as fallback (current setup)
   - Test both API and local versions

4. **Monitor deprecation:**
   - HuggingFace models can be deprecated
   - Have replacement models ready
   - Consider using model versioning

---

## Quick Checklist for Model Selection

For each model, verify:
- [ ] Model is active (not archived)
- [ ] Task type matches (summarization, ner, etc.)
- [ ] Supports English language
- [ ] Model size is reasonable for your hardware
- [ ] API is available (if using remote/hybrid)
- [ ] Documentation is clear
- [ ] Recent updates/commits
- [ ] High download/usage count
- [ ] Good performance metrics (ROUGE, F1, etc.)

---

## Troubleshooting

**If a model returns 410 Gone:**
- Model has been deprecated/removed
- Search for alternative models
- Use local fallback (already implemented)

**If a model is too slow:**
- Try smaller models (distil variants)
- Use local models instead of API
- Consider model quantization

**If a model quality is poor:**
- Try larger models (large vs base)
- Use models fine-tuned on relevant datasets
- Consider ensemble approaches

