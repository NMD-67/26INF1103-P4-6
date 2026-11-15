# Hybrid score review

CLI and Telegram use RecommendationService and the shared ScoringPipeline.
The secondary MatchingService delegates scoring and saving to that same pipeline.
The existing secondary route keeps its five-candidate batch limit; the normal
Find Matches route still processes all eligible candidates.

Order: eligibility filtering, AI response validation, independent category review,
weighted overall calculation, ranking, persistence, then display.
Review preserves the original reason and uses the existing tolerance (25), MBTI,
goal rules and local interest similarity. These checks are heuristics, not proven
compatibility probabilities. Malformed reviewer output is logged and valid scores
are retained. Dry-run review still logs corrections without applying them.

## Docker

Build with `docker build -t sitogether .`. The build installs CPU PyTorch and
sentence-transformers and downloads all-MiniLM-L6-v2 into /app/embedding-model.
This makes the image larger and requires internet during the build. The local
review model needs no network at runtime; Groq/database/email still need network.
CI runs the unit suite without networking and separately loads and runs the real
packaged model with networking disabled. Do not claim the Docker check passed
until that CI step succeeds.

## Running directly with Python

Install requirements, then download the model once in a separate Python process:

```powershell
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2').save('embedding-model')"
$env:LOCAL_EMBEDDING_MODEL = "$PWD/embedding-model"
```

Keep downloaded model files outside Git (or use an external model directory).
If the model is unavailable, the existing fallback logs a warning and retains
MBTI/goals review. Full interest review requires that local model.

## Tests

`python -B ci/offline_tests.py` uses fake AI/repositories and does not contact
production services. Reviewer tests cover correction, dry-run, invalid values,
invalid counts/categories, fallback, ranking, persistence and the batch route.
The heavyweight local model is mocked in unit tests and exercised separately
by Docker CI.
