# Spotify AI Review Discovery Engine

This folder contains the review-analysis workflow used for the Spotify product-management assignment in `project-task.txt`, focused on Step 1 and Step 3:

- Step 1: build an AI-powered review discovery engine.
- Step 3: define the problem, target segment, business reason, and MVP direction.

The implementation combines a deterministic Python review-selection pipeline with a local n8n workflow that sends only relevant discovery reviews to Gemini. This keeps the AI step focused on reviews that matter for the assignment question instead of spending tokens on unrelated app feedback.

## What is in this folder

```text
scripts/
  google_play_review_scraper.py      Fetches Spotify Google Play reviews.
  apple_app_store_scraper.py         Fetches Spotify Apple App Store reviews.
  create_master_dataset.py           Merges Google Play and App Store reviews.
  discovery_filter.py                Scores and filters discovery-related reviews.
  review_selection.py                Selects the final review sample for AI analysis.

n8n-workflow/
  Wokflow.json                       n8n workflow export.
  n8n-workflow.png                   Workflow screenshot.

reports/
  final_summary.json                 Final Gemini-generated product strategy summary.
  spotify_product_strategy.json      Same strategy output in JSON form.
  spotify_product_strategy.html      HTML report output.

project-task.txt                     Assignment brief.
Deck_Slides.key                      Final deck source.
```

The raw and processed CSV data files are expected under `data/raw/` and `data/processed/` when the pipeline is run.

## Execution Flow



### 1. Collect app review data

Google Play reviews are collected with:

```bash
python scripts/google_play_review_scraper.py
```

The script fetches Spotify reviews for the configured countries and writes one raw CSV per country under `data/raw/`.

Apple App Store reviews are collected with:

```bash
python scripts/apple_app_store_scraper.py
```

The script uses the Apple customer-review RSS endpoint for Spotify and writes `data/raw/apple_reviews.csv`.

Why this step matters: the assignment asks for review analysis at scale. Pulling reviews from both stores gives a broader input set than relying on one channel.

### 2. Create the master review dataset

```bash
python scripts/create_master_dataset.py
```

This merges Google Play and Apple App Store reviews into:

```text
data/processed/master_reviews.csv
```

It also normalizes shared columns such as source, country, review ID, username, rating, review text, title, date, and app version.

Why this step matters: a single master dataset makes later scoring and audit easier. Each review keeps its source and country metadata, so analysis can still trace where feedback came from.

### 3. Score reviews using the discovery taxonomy

```bash
python scripts/discovery_filter.py
```

This script applies a weighted taxonomy across six categories:

- discovery
- recommendation
- repetition
- playlist
- personalization
- artist

It creates:

```text
data/processed/scored_reviews.csv
data/processed/discovery_candidates.csv
data/processed/final_discovery_reviews.csv
```

The script also removes generic praise and infrastructure-only reviews such as login, billing, crash, offline, or download issues when they do not mention discovery.

Why this step matters: the assignment is about meaningful music discovery and repetitive listening. A taxonomy filter prevents unrelated app-store complaints from polluting the AI research synthesis.

### 4. Select the final AI input sample

```bash
python scripts/review_selection.py
```

This creates:

```text
data/processed/gpt_input_reviews.csv
```

The selection logic prioritizes high-priority reviews, then adds coverage by category, rating, and named Spotify discovery features such as Discover Weekly, Smart Shuffle, Daily Mix, Release Radar, AI DJ, and Radio.

Why this step matters: the final input is smaller and more balanced. Gemini receives reviews that are relevant, high-signal, and diverse enough to answer the assignment questions.

### 5. Run n8n locally

The n8n workflow was run locally using Docker:

```bash
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -e N8N_RESTRICT_FILE_ACCESS_TO="/workspace" \
  -v ~/.n8n:/home/node/.n8n \
  -v <path where you keep file gpt_input_reviews.csv>:/workspace \
  n8nio/n8n
```

Open n8n at:

```text
http://localhost:5678
```

Import:

```text
n8n-workflow/Wokflow.json
```

The workflow reads(you can change thsi path depends on what volume you ar emounting in docker):

```text
/workspace/data/processed/gpt_input_reviews.csv
```

Why this step matters: n8n acts as the AI orchestration layer. It reads the filtered review file, batches the reviews, builds structured prompts, calls Gemini, waits between batches, and writes the final analysis output.

### 6. n8n workflow logic

The workflow does the following:

1. Manual trigger starts the workflow.
2. Reads `gpt_input_reviews.csv` from disk.
3. Extracts CSV rows into JSON.
4. Keeps only LLM-relevant fields: review ID, source, country, rating, discovery score, categories, and review text.
5. Splits reviews into batches of 30.
6. Builds a batch prompt asking Gemini to extract evidence, not solutions.
7. Calls Gemini with low temperature.
8. Parses each batch response.
9. Waits 30 seconds between batches to avoid exceeding Gemini API request limits.
10. Writes batch analysis JSON files to cache.
11. Reads batch analysis files.
12. Builds a final synthesis prompt asking Gemini to answer the Step 1 questions, rank problems, define the root cause, identify segments, make the business case, and evaluate MVP directions.
13. Writes the final strategy output to `reports/final_summary.json`.

Why this step matters: batch analysis keeps prompts manageable, and the second synthesis pass turns many review-level findings into one product-management answer.

## Why the Pipeline Is Useful

- Lower AI cost: Gemini only analyzes selected discovery reviews, not every raw review.
- Higher signal: taxonomy scoring removes generic praise and unrelated technical complaints.
- Better auditability: each selected review keeps its original review ID, rating, source, country, matched terms, and categories.
- Better coverage: the final sample includes high-priority reviews, rating spread, category spread, and feature mentions.
- Repeatable workflow: Python handles deterministic filtering; n8n handles repeatable AI orchestration.
- Assignment fit: the workflow directly answers the Step 1 research questions before moving into Step 3 problem definition.



## Final Analysis

The final analysis in `reports/final_summary.json` answered the assignment research questions as follows.

### Why users struggle to discover new music

Users struggle because recommendations often feel repetitive, too close to existing listening history, or not relevant to their current mood or activity. This creates a listening bubble around familiar artists, tracks, and genres.

### What frustrates users about recommendations

The main frustration is that recommendations feel too safe. Users want more variety, more surprise, and more control over how recommendations adapt when their intent changes.

### What listening behavior users want

Users want effortless discovery of genuinely new music that still feels relevant. They want to expand taste without spending too much time searching, skipping, or manually curating playlists.

### Why users repeat the same content

Users repeat the same songs because familiar music is reliable, while discovery often has a high effort-to-success ratio. When recommendation tools disappoint, users fall back to known favorites.

### User segments identified

The analysis identified three major discovery segments:

- Explorers: actively seek new music but get frustrated by repetitive recommendations.
- Casual Listeners: mostly listen to familiar music and need lower-friction discovery entry points.
- Niche Enthusiasts: seek deep cuts, sub-genres, emerging artists, and more granular discovery.

The selected focus segment is Explorers because they have high discovery intent, high frustration, and are more likely to engage with a new discovery product.

### Primary problem

Spotify recommendations can become repetitive and stale because the recommendation system over-relies on historical listening behavior. This creates an exploitation bias: the system is good at recommending more of what a user already likes, but weaker at understanding when the user wants to explore.

### Business reason to solve it

Solving repetitive discovery can increase engagement, improve retention, make Premium feel more valuable, broaden catalog consumption, and strengthen Spotify's differentiation through better discovery.

## MVP Direction

The first draft idea was a Discovery Dial: a control for shifting recommendations between familiar and exploratory modes.

The final MVP direction was changed to an Intent Discovery Agent, or IDA. IDA runs between search and Spotify-style recommendation output. Instead of adding a separate dial, it lets users express intent directly through natural language and choose an exploration mode.

The implemented MVP direction from the related project is:

- Spotify-inspired home/search experience.
- Search mode for standard catalog-style results.
- IDA mode for intent-based recommendations.
- Dual mode for comparing standard search and IDA recommendations side by side.
- IDA exploration modes: Auto, Familiar, Balanced, Expand, and Deep dive.
- Gemini intent extraction when available.
- Rule-based fallback when no API key is available.
- Deterministic recommendation scoring over a local real-song reference catalog.

Why AI is suited here: traditional recommendation systems mainly infer taste from past behavior. IDA adds current intent: mood, activity, novelty appetite, constraints, and desired discovery depth. This lets recommendations respond to what the user is trying to do now, not only what they listened to before.

## Recommended Problem Statement

Explorer users who want fresh music discovery get trapped in repetitive recommendation loops because Spotify-style recommendations mostly optimize from historical listening behavior, not current discovery intent. This makes discovery feel effortful and pushes users back to familiar songs, reducing discovery satisfaction and long-term engagement.

## Suggested Success Metrics

- Discovery success rate: share of IDA recommendations saved, added, or listened to beyond a threshold.
- New artists followed per user per month.
- Reduction in listening share from the user's top repeated tracks.
- Weekly active discovery users.
- Recommendation acceptance rate.
- Discovery satisfaction from follow-up survey or interview validation.

