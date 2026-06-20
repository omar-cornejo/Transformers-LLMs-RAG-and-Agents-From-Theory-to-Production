# Week 1 · Exercise 1 — Tokenize, locally

## Execution

### Exact command used
```bash
uv venv && source .venv/bin/activate && uv sync && python ex_01_tokenise.py
```

## Changes made

### 1. Paragraphs (PARAGRAPH_EN / PARAGRAPH_MINE)

**PARAGRAPH_EN (original):**
```python
"Three sad tigers swallow wheat in a wheat field,"
"in a wheat field three sad tigers swallow wheat."
"Which tiger swallows more wheat?"
"All three sad tigers swallow the same wheat in the wheat field."
```

**PARAGRAPH_MINE (Spanish):**
```python
"Tres tristes tigres tragan trigo en un trigal,"
"en un trigal tragan trigo tres tristes tigres."
"¿Qué tigre traga más trigo?"
"Los tres tristes tigres tragan igual trigo en el trigal."
```

### 2. Tokenizers compared

Three tokenizer pairs were tested:
- **Run 1:** `gpt2` vs `bert-base-uncased` (WordPiece)
- **Run 2:** `gpt2` vs `roberta-base` (BPE)
- **Run 3:** `gpt2` vs `EleutherAI/gpt-j-6B` (improved BPE)

---

## Results

### Demo sentence token count
```
Text: "The model never sees the letters in strawberry."
Tokens with gpt2: 9
```

### Multilingual penalty

| Metric | Value |
|---------|-------|
| English tokens | 40 |
| Spanish tokens | 68 |
| **Multilingual penalty** | **+70.0%** |

**Formula:** `(mine - en) / en = (68 - 40) / 40 = 28 / 40 = 0.70 = +70.0%`

Spanish requires **70% more tokens** than English with the GPT-2 tokenizer because:
- GPT-2 was trained primarily on English
- Spanish has more accented characters and morphological patterns that are not optimized in GPT-2's BPE vocabulary

---

### Comparison: tokenizers vs code

#### Run 1: GPT-2 vs BERT-base-uncased (WordPiece)

| Input | gpt2 | bert-base-uncased | Difference |
|-------|------|-------------------|-----------|
| python function | 26 | 22 | -4 tokens |
| JSON blob | 36 | 45 | +9 tokens |
| regex-heavy line | 41 | 44 | +3 tokens |
| whitespace-heavy | 20 | 5 | **-15 tokens** |

**Row-by-row analysis:**

1. **python function:** BERT is more efficient (-15.4%). BERT's WordPiece handles Python keywords such as `def` and `return` as complete units, while GPT-2's BPE splits them more often.

2. **JSON blob:** GPT-2 is more efficient (+25%). BERT penalizes special symbols such as `{}[]:"` and tokenizes them individually, while GPT-2's BPE keeps common structures together.

3. **regex-heavy line:** BERT uses more (+7.3%). Regex-special characters such as `\s*([A-Za-z_]` are tokenized inefficiently with WordPiece. GPT-2's byte-level BPE is better for unusual characters.

4. **whitespace-heavy:** **BERT is dramatically better (-75%)** ⭐ WordPiece normalizes and collapses repeated whitespace and tabs, while GPT-2's BPE tokenizes each space and tab separately as independent tokens.

#### Run 2: GPT-2 vs RoBERTa-base (BPE)

| Input | gpt2 | roberta-base | Difference |
|-------|------|--------------|-----------|
| python function | 26 | 26 | 0 |
| JSON blob | 36 | 36 | 0 |
| regex-heavy line | 41 | 41 | 0 |
| whitespace-heavy | 20 | 20 | 0 |

**Analysis:**
Both use BPE with compatible vocabularies. There is no notable difference in these examples because:
- They share the same base tokenization algorithm (BPE)
- RoBERTa is based on GPT-2's BPE, improved but still compatible
- The code examples do not exploit vocabulary differences between the two

#### Run 3: GPT-2 vs GPT-J-6B (advanced BPE)

| Input | gpt2 | EleutherAI/gpt-j-6B | Difference |
|-------|------|---------------------|-----------|
| python function | 26 | 26 | 0 |
| JSON blob | 36 | 36 | 0 |
| regex-heavy line | 41 | 41 | 0 |
| whitespace-heavy | 20 | 20 | 0 |

**Analysis:**
GPT-J keeps the same BPE tokenizer as GPT-2, so the results are identical. GPT-J differs only in model architecture (more parameters), not in tokenization.

---

## Conclusions

### 1. Architectural differences
- **WordPiece (BERT)** vs **BPE (GPT-2)**: Dramatic differences on whitespace-heavy text (BERT is 75% more efficient)
- **BPE variants (GPT-2 vs RoBERTa vs GPT-J)**: Practically identical in these examples

### 2. Multilingual
- Spanish incurs **+70% overhead** compared with English under GPT-2
- Recommendation: use multilingual tokenizers such as `bert-base-multilingual-cased` for better efficiency on non-English text

### 3. Practical implications
- For code, BERT is better (~15-25% more efficient)
- For whitespace and formatting, BERT is dramatically better
- GPT-2 is better for special JSON and regex symbols

---
