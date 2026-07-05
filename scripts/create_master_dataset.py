import pandas as pd
from pathlib import Path

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
PROCESSED.mkdir(parents=True, exist_ok=True)

google = pd.concat([
    pd.read_csv(f)
    for f in RAW.glob("google_*.csv")
], ignore_index=True)

google = google.drop_duplicates(subset=["reviewId"])

apple = pd.read_csv(RAW / "apple_reviews.csv")

# Ensure same columns
columns = [
    "source",
    "country",
    "reviewId",
    "userName",
    "rating",
    "review",
    "title",
    "date",
    "version",
]

for c in columns:
    if c not in google.columns:
        google[c] = None
    if c not in apple.columns:
        apple[c] = None

master = pd.concat([
    google[columns],
    apple[columns]
], ignore_index=True)

master.to_csv(PROCESSED / "master_reviews.csv", index=False)

print(master.shape)
