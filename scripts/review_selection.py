import pandas as pd
from pathlib import Path

INPUT = Path("data/processed/final_discovery_reviews.csv")
OUTPUT = Path("data/processed/gpt_input_reviews.csv")

TARGET_SIZE = 160

FEATURES = [
    "discover weekly",
    "smart shuffle",
    "daily mix",
    "release radar",
    "ai dj",
    "radio",
]

CATEGORIES = [
    "discovery",
    "recommendation",
    "repetition",
    "playlist",
    "artist",
    "personalization",
]


# ------------------------------------------------------------
# Load Data
# ------------------------------------------------------------
def load_data():
    df = pd.read_csv(INPUT)
    df["review"] = df["review"].fillna("")
    return df


# ------------------------------------------------------------
# Basic scoring helper for diversity selection
# ------------------------------------------------------------
def normalize(df):
    df["review_lower"] = df["review"].str.lower()
    return df


# ------------------------------------------------------------
# Step 1: Top priority reviews
# ------------------------------------------------------------
def top_priority(df, n=80):
    return df.sort_values("priority_score", ascending=False).head(n)


# ------------------------------------------------------------
# Step 2: Category coverage
# ------------------------------------------------------------
def category_sample(df, per_category=10):
    selected = []

    for cat in CATEGORIES:
        subset = df[df["categories"].str.contains(cat, na=False)]
        subset = subset.sort_values("priority_score", ascending=False)
        selected.append(subset.head(per_category))

    return pd.concat(selected).drop_duplicates()


# ------------------------------------------------------------
# Step 3: Rating balance
# ------------------------------------------------------------
def rating_balance(df, per_rating=8):
    selected = []

    for r in sorted(df["rating"].unique()):
        subset = df[df["rating"] == r]
        subset = subset.sort_values("priority_score", ascending=False)
        selected.append(subset.head(per_rating))

    return pd.concat(selected).drop_duplicates()


# ------------------------------------------------------------
# Step 4: Feature coverage
# ------------------------------------------------------------
def feature_coverage(df, per_feature=5):
    selected = []

    for feature in FEATURES:
        subset = df[df["review_lower"].str.contains(feature, na=False)]
        subset = subset.sort_values("priority_score", ascending=False)
        selected.append(subset.head(per_feature))

    return pd.concat(selected).drop_duplicates()


# ------------------------------------------------------------
# Step 5: Fill remaining slots
# ------------------------------------------------------------
def fill_remaining(df, selected):
    remaining = df[~df["original_review_id"].isin(selected["original_review_id"])]

    remaining = remaining.sort_values("priority_score", ascending=False)

    needed = TARGET_SIZE - len(selected)

    return remaining.head(max(needed, 0))


# ------------------------------------------------------------
# Main pipeline
# ------------------------------------------------------------
def main():

    df = load_data()
    df = normalize(df)

    print(f"Total discovery reviews: {len(df)}")

    selected_parts = []

    # 1. High priority
    selected_parts.append(top_priority(df))

    # 2. Category coverage
    selected_parts.append(category_sample(df))

    # 3. Rating balance
    selected_parts.append(rating_balance(df))

    # 4. Feature coverage
    selected_parts.append(feature_coverage(df))

    # Merge
    selected = pd.concat(selected_parts).drop_duplicates(
        subset=["original_review_id"]
    )

    # 5. Fill remaining
    fill = fill_remaining(df, selected)

    final = pd.concat([selected, fill]).drop_duplicates(
        subset=["original_review_id"]
    )

    final = final.sort_values(
        "priority_score",
        ascending=False
    ).head(TARGET_SIZE)

    # Save
    final.to_csv(OUTPUT, index=False)

    print("=" * 60)
    print("FINAL GPT INPUT DATASET CREATED")
    print("=" * 60)
    print(f"Selected reviews: {len(final)}")
    print(f"Saved to: {OUTPUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()
