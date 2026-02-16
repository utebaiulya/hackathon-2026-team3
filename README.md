# hackathon-2026-team3

#  E‑E‑A‑T Scoring Rules (Derived from Your JSON)



This guide explains how to compute **E‑E‑A‑T subscores** and an overall **0–100** score from the JSON output you shared.

> Note: This is a practical auditing rubric inspired by Google’s E‑E‑A‑T concepts. It is **not** an official Google scoring system, so you should validate it against real-world outcomes (rankings, quality rater alignment, conversions, etc.).

---

## 1) Inputs we read from your JSON

We use these sections:

- `experience_m`  
  A set of questions (Q1–Q6) indicating whether the content demonstrates **first-hand experience**.

- `expertise_m`  
  A set of questions (Q1–Q10) indicating **subject-matter competence**, depth, and whether it includes **citations**.

- `content_quality_m`  
  A set of questions (Q1–Q9) indicating clarity, organization, correctness, usefulness, and completeness.

- `trust_m.question_ratings`  
  Core trust questions and an authoritativeness signal:
  - Q1: reliability
  - Q2: accuracy / “full picture”
  - Q3: safety / misleading risk
  - Q6: authoritativeness

- `author_info_m`  
  Whether an **author** is explicitly present (`author_present`) (and/or `rating`).

- `contributor_author`  
  Whether a **reviewer/editor/endorser** is present (`reviewer_editor_endorser_present`) (and/or `rating`).

- `content_angle_m`  
  Declared content angle:
  - `angle_experience` (bool)
  - `angle_expertise` (bool)

- `ymyl.task 2`  
  YMYL classification (we only use `spectrum`):
  - `ymyl.task 2.spectrum` (e.g., `"Clear YMYL"`)

---

## 2) Normalization (convert to a consistent 0–1 scale)

Different sections store “ratings” in different shapes, so we normalize everything into a single scale.

### 2.1 Rating values
- `rating: 1` → **1.0**
- `rating: 0` → **0.0**
- `rating: 0.5` → **0.5**

### 2.2 Boolean values
- `True` → **1.0**
- `False` → **0.0**

### 2.3 Averaging question sets
For a section like `experience_m` or `expertise_m`, compute:

$$avg = \frac{\sum ratings}{ number of questions}$$

To convert any average to a 0–100 score:

$$score = 100 \times avg$$

---

## 3) Determine the “content angle” state

Based on `content_angle_m`:

- **Experience-led**  
  `angle_experience = True` and `angle_expertise = False`

- **Expertise-led**  
  `angle_experience = False` and `angle_expertise = True`

- **Mixed / Unclear**  
  both `True` or both `False`

This angle influences (a) mismatch penalties and (b) optional score weighting.

---

## 4) Subscores (0–100 each)

We compute four subscores:

- **E** = Experience  
- **Ex** = Expertise  
- **A** = Authoritativeness  
- **T** = Trust  

Each is computed from specific JSON signals.

---

# 4A) Experience score (E)

### What it measures
Evidence of **first-hand experience**: personal testing, observed outcomes, hands-on comparisons, original photos from usage, first-person insights, etc.

### Inputs
- `experience_m.question_1..6.rating`

### Formula
$$
E = 100 \times avg(experience\_m[Q1..Q6])
$$

### Angle alignment penalty (recommended)
If the content is **Experience-led** but experience signals are weak:

- If `angle_state = experience-led` and `E < 30` → subtract **10** points

$$
E = \max(0, E - 10)
$$

---

# 4B) Expertise score (Ex)

### What it measures
Whether the content demonstrates **competent, knowledgeable coverage** of the topic and communicates it well.

### Inputs
- `expertise_m.question_1..10.rating`
- `content_quality_m.question_1..9.rating`

### Formula (weighted blend)
We weight “expertise signals” more than general content quality:

$$
Ex = 100 \times \Big(0.6 \times avg(expertise\_m[Q1..Q10]) + 0.4 \times avg(content\_quality\_m[Q1..Q9])\Big)
$$

### Angle alignment penalty (recommended)
If the content is **Expertise-led** but expertise is not strong:

- If `angle_state = expertise-led` and `Ex < 60` → subtract **10** points

$$
Ex = \max(0, Ex - 10)
$$

---

# 4C) Authoritativeness score (A)

### What it measures
Whether the page shows “who stands behind this” via:
- site/brand authority cues, and
- accountable people (author and/or reviewer/editor).

### Inputs
- `trust_m.question_ratings.question_6.rating`  (authority cue)
- `author_info_m.author_present` (or `author_info_m.rating`)
- `contributor_author.reviewer_editor_endorser_present` (or `contributor_author.rating`)

### Component values (each 0–1)
- **Domain authority proxy**
  - $$A_{domain} = trust\_m.Q6$$
- **Author presence**
  - $$A_{author} = author\_present$$
- **Reviewer/editor presence**
  - $$A_{reviewer} = reviewer\_present$$

### Formula
$$
A = 100 \times (0.5 \times A_{domain} + 0.3 \times A_{author} + 0.2 \times A_{reviewer})
$$

---

# 4D) Trust score (T)

### What it measures
Reliability and safety—especially important for **YMYL**.

### Inputs

**From `trust_m.question_ratings`:**
- Q1 reliability
- Q2 accuracy / full picture
- Q3 safety / misleading risk

**From `content_quality_m`:**
- Q3 grammar/care
- Q4 accuracy

**From `expertise_m`:**
- Q10 citations / reputable sources

**From author/reviewer signals:**
- `author_info_m.author_present`
- `contributor_author.reviewer_editor_endorser_present`

### Component values (0–1)

**Core trust**
$$
T_{core} = avg(trust\_m[Q1..Q3])
$$

**Accuracy proxy**
$$
T_{accuracy} = avg(content\_quality\_m[Q3, Q4])
$$

**Citations**
$$
T_{citations} = expertise\_m.Q10
$$

**Transparency (accountability)**
$$
T_{transparency} = avg(author\_present, reviewer\_present)
$$

### Base formula
$$
T_{base} = 100 \times (0.6 \times T_{core} + 0.2 \times T_{accuracy} + 0.1 \times T_{citations} + 0.1 \times T_{transparency})
$$

---

## 5) YMYL strictness rules (recommended)

We read:

- `ymyl.task 2.spectrum`

If:

- `spectrum == "Clear YMYL"`

Then apply conservative caps when key trust evidence is missing.

### 5.1 YMYL Trust caps
If **Clear YMYL**:

- If `T_citations = 0` → cap Trust at **75**
- If `T_transparency = 0` → cap Trust at **70**

In practice:

$$
T = \min(T_{base},\ 75\ \text{if}\ T_{citations}=0,\ 70\ \text{if}\ T_{transparency}=0)
$$

---

## 6) Overall E‑E‑A‑T score (0–100)

We compute the final score as a weighted sum of the four subscores.

### 6.1 Default weights (non‑YMYL / general)
- E 25%
- Ex 25%
- A 20%
- T 30%

### 6.2 Clear YMYL weights
Trust matters more for YMYL:
- E 10%
- Ex 30%
- A 20%
- T 40%

### 6.3 Optional: Angle-based reweighting

If you want the final score to reflect the declared “angle,” adjust weights as follows.

#### Non‑YMYL
- **Default**: E 25%, Ex 25%, A 20%, T 30%
- **Experience-led**: E 35%, Ex 20%, A 15%, T 30%
- **Expertise-led**: E 15%, Ex 35%, A 20%, T 30%

#### Clear YMYL (Trust stays dominant)
- **Default**: E 10%, Ex 30%, A 20%, T 40%
- **Experience-led**: E 15%, Ex 25%, A 20%, T 40%
- **Expertise-led**: E 5%, Ex 35%, A 20%, T 40%

### 6.4 Final formula
$$
EEAT = w_E E + w_{Ex} Ex + w_A A + w_T T
$$

---

## 7) Explainability flags (recommended outputs)

These flags help interpret scores and prioritize fixes:

- `missing_author`  
  `author_info_m.author_present == False`

- `missing_reviewer_editor`  
  `contributor_author.reviewer_editor_endorser_present == False`

- `missing_citations`  
  `expertise_m.question_10.rating == 0`

- `experience_angle_mismatch_penalty`  
  Experience-led but `E < 30` (penalty applied)

- `expertise_angle_mismatch_penalty`  
  Expertise-led but `Ex < 60` (penalty applied)

- `ymyl_citation_cap_applied`  
  Clear YMYL + no citations (Trust capped)

- `ymyl_transparency_cap_applied`  
  Clear YMYL + no author/reviewer (Trust capped)

---

## 8) Interpretation bands (optional)

- **90–100**: exceptional (strong evidence, accountability, safety rigor)
- **70–89**: strong (minor gaps)
- **50–69**: moderate (gaps likely limit performance in YMYL)
- **<50**: weak (significant missing signals)

---


# Why some were not used?

Those objects weren’t used because the scoring model is strictly anchored to signals that most directly map to E‑E‑A‑T (first‑hand experience, expertise depth/citations, authority/accountability, and trust/reliability). The four listed are real quality signals, but they’re either:

Not E‑E‑A‑T pillars themselves (they’re “page quality / UX / conversion” signals), or
Already partially represented by fields we used (to avoid double-counting), or
Harder to score consistently without clearer numeric structure (some are qualitative) unless we explicitly add them as “supporting modifiers.”

That said, you can and often should incorporate them—especially for product pages. Here’s why each was excluded and how to add it cleanly.

### 1) page_purpose_m

Why it wasn’t used:
“Page purpose” is more of a baseline Page Quality gate than an E‑E‑A‑T pillar. If purpose is bad/misleading, E‑E‑A‑T doesn’t matter much. Your JSON has page_purpose_rating: "Good" (string), not a numeric rating, so it also needs mapping logic.

How to use it (recommended):
Use it as a multiplier/gate on the final score.

Example mapping:

"Good" → multiplier 1.00
"OK" → 0.90
"Bad" → 0.60

Then:

$$EEAT_{final} = EEAT \times multiplier$$
### 2) product_page_optimization_url

Why it wasn’t used:
This is largely conversion/UX completeness (price, availability, variants, delivery), not E‑E‑A‑T. It can correlate with trust, but it’s not the same thing. Also your JSON already provides a numeric-ish field (product_optimization_rating: 0.5) which is good—but we didn’t integrate “commerce UX” in the first pass to keep the model E‑E‑A‑T focused.

How to use it (recommended for PDPs):
Feed it into Trust (T) as a minor component (transparency/completeness), or apply a small overall bonus/penalty.

Example: add to Trust at 5–10% weight:

$$T = 100 \times (0.55T_{core} + 0.20T_{accuracy} + 0.10T_{citations} + 0.10T_{transparency} + 0.05T_{pdp})$$
Where:
$$T_{pdp} = product_optimization_rating$$
### 3) multimedia_content_m

Why it wasn’t used:
Presence of images/video is a quality/UX signal, but it can be superficial (stock images ≠ experience). Also you already had strong content_quality_m, and adding multimedia without “originality” signals can inflate scores.

How to use it safely:
Use as a small supporting input to Experience (E) only if you later add a way to detect original media. With current JSON (just “images present / video present”), I’d use it as a small content quality modifier instead.

Example (lightweight):

images_present = multimedia_content_m.question_1.rating
video_present = multimedia_content_m.question_2.rating
$$M = avg(images_present, video_present)$$
Then either:
Add + up to 5 points to Ex or E, or
Add 5% weight inside Ex (since it improves comprehension).

### 4) expertise_talent_skill

Why it wasn’t used:
This block mostly evaluates writing/marketing skill and presentation (tone, flow, examples, visuals). That overlaps heavily with content_quality_m (organization, clarity, usefulness) and parts of expertise_m. Including it without rebalancing would double-count quality.

How to incorporate (best practice):
Treat it as a “communication skill” component inside Expertise (Ex), but reduce the weight of content_quality_m accordingly.

Example revised Expertise:

Let $$S = avg(expertise_talent_skill[Q1..Q7])$$ (booleans → 0/1)
$$Ex = 100 \times (0.55 \times avg(expertise_m) + 0.30 \times avg(content_quality_m) + 0.15 \times S)$$

If you want, I can update the Python code to include these four sections in a way that (a) avoids double-counting and (b) keeps YMYL Trust logic intact. Just tell me whether you prefer them as pillar inputs (E/Ex/T) or as final score modifiers/gates. 




