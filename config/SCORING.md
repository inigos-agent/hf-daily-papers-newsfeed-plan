# Scoring Profile (Easy Edit)

Edit this file:

- `config/scoring_profile.json`

## What to change

### 1) Category weights
Higher weight => papers matching this category rank higher.

```json
"healthcare": { "weight": 1.5, "keywords": [...] }
```

### 2) Keywords per category
Add/remove terms that should count as matches.

### 3) Global scoring controls
- `base_per_hit`: score contribution per matched keyword
- `cap_per_category`: max contribution from one category before weighting

## Example custom categories

```json
"categories": {
  "popularity": { "weight": 1.4, "keywords": ["benchmark", "sota", "leaderboard"] },
  "generative_ai": { "weight": 1.8, "keywords": ["llm", "diffusion", "multimodal"] },
  "healthcare": { "weight": 2.0, "keywords": ["clinical", "patient", "medical"] }
}
```

After editing, rerun:

```bash
PYTHONPATH=src python3 run.py
```
