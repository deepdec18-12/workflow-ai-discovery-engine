import re
from pathlib import Path

import pandas as pd

# ============================================================
# Configuration
# ============================================================

INPUT = Path("data/processed/master_reviews.csv")

SCORED_OUTPUT = Path("data/processed/scored_reviews.csv")
DISCOVERY_OUTPUT = Path("data/processed/discovery_candidates.csv")
FINAL_OUTPUT = Path("data/processed/final_discovery_reviews.csv")

DISCOVERY_THRESHOLD = 5

# ============================================================
# Discovery Taxonomy
# ============================================================

TAXONOMY = {

    "discovery": {
        "discover": 5,
        "discovery": 5,
        "explore": 4,
        "new music": 6,
        "new songs": 6,
        "new artist": 6,
        "new artists": 6,
        "hidden gem": 6,
        "hidden gems": 6,
        "genre": 3,
        "genres": 3,
        "variety": 5,
        "diverse": 5,
        "diversity": 5,
        "fresh": 5,
        "different music": 5,
        "music suggestions": 5,
        "find artists": 5,
        "find songs": 5,
        "music taste": 3,
        "expand my taste": 6,
        "broaden": 5,
    },

    "recommendation": {
        "recommend": 4,
        "recommended": 4,
        "recommendation": 5,
        "recommendations": 5,
        "suggest": 4,
        "suggestion": 4,
        "algorithm": 3,
        "personalized": 3,
        "personalization": 3,
    },

    "repetition": {
        "same songs": 7,
        "same song": 7,
        "same artists": 7,
        "same artist": 7,
        "repeat": 4,
        "repeats": 4,
        "repeating": 4,
        "repetitive": 7,
        "stale": 6,
        "boring": 4,
        "over and over": 7,
        "again and again": 7,
        "keeps playing": 6,
        "only plays": 6,
        "never changes": 7,
    },

    "playlist": {
        "discover weekly": 8,
        "daily mix": 7,
        "smart shuffle": 8,
        "shuffle": 4,
        "radio": 4,
        "playlist": 2,
        "playlists": 2,
        "release radar": 8,
        "ai dj": 8,
        "blend": 6,
    },

    "personalization": {
        "taste": 3,
        "preferences": 3,
        "mood": 3,
        "listening history": 5,
        "my music": 2,
    },

    "artist": {
        "artist": 2,
        "artists": 2,
        "indie": 4,
        "underground": 4,
        "similar artist": 5,
        "similar artists": 5,
        "related artists": 5,
    }
}

# ============================================================
# Ignore Generic Praise
# ============================================================

GENERIC_PRAISE = [
    "best app",
    "great app",
    "amazing app",
    "awesome app",
    "excellent app",
    "love spotify",
    "love this app",
    "five stars",
    "5 stars",
    "highly recommend",
]

# ============================================================
# Ignore Infrastructure-only Reviews
# ============================================================

TECHNICAL_ONLY = [
    "login",
    "log in",
    "password",
    "subscription",
    "billing",
    "payment",
    "crash",
    "crashes",
    "freeze",
    "frozen",
    "bug",
    "bluetooth",
    "offline",
    "download",
    "account",
]

# ============================================================
# Rating Bonus
# ============================================================

RATING_BONUS = {
    1: 4,
    2: 3,
    3: 2,
    4: 1,
    5: 0,
}

# ============================================================
# Helper Functions
# ============================================================

def contains_term(text: str, term: str) -> bool:
    """
    Match whole words/phrases.
    """

    return bool(
        re.search(
            r"\b" + re.escape(term) + r"\b",
            text,
        )
    )


def score_review(text: str):

    text = str(text).lower()

    discovery_score = 0

    categories = []

    matched_terms = []

    for category, words in TAXONOMY.items():

        category_score = 0

        for term, weight in words.items():

            if contains_term(text, term):

                category_score += weight
                matched_terms.append(term)

        if category_score > 0:

            categories.append(category)

            discovery_score += category_score

    return (
        discovery_score,
        ",".join(categories),
        ",".join(sorted(set(matched_terms))),
    )


def is_generic_praise(text: str) -> bool:

    text = text.lower()

    return any(
        phrase in text
        for phrase in GENERIC_PRAISE
    )


def is_technical_only(text: str) -> bool:

    text = text.lower()

    technical = any(
        word in text
        for word in TECHNICAL_ONLY
    )

    discovery = any(
        word in text
        for group in TAXONOMY.values()
        for word in group.keys()
    )

    return technical and not discovery

# ============================================================
# Processing Functions
# ============================================================

def load_reviews() -> pd.DataFrame:
    """
    Load master dataset and add a stable review id.
    """

    df = pd.read_csv(INPUT)

    df["review"] = df["review"].fillna("").astype(str)

    # Stable identifier across all datasets
    df.insert(
        0,
        "original_review_id",
        range(1, len(df) + 1)
    )

    return df


def score_all_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """
    Score every review in the dataset.
    """

    scores = df["review"].apply(score_review)

    df["discovery_score"] = scores.str[0]
    df["categories"] = scores.str[1]
    df["matched_terms"] = scores.str[2]

    df["rating_bonus"] = (
        df["rating"]
        .map(RATING_BONUS)
        .fillna(0)
        .astype(int)
    )

    df["priority_score"] = (
        df["discovery_score"]
        + df["rating_bonus"]
    )

    df["is_discovery_review"] = (
        df["discovery_score"] >= DISCOVERY_THRESHOLD
    )

    df["selected_for_gpt"] = False

    return df


def remove_noise(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove generic praise and infrastructure-only reviews.
    """

    filtered = df[df["is_discovery_review"]].copy()

    filtered = filtered[
        ~filtered["review"].apply(is_generic_praise)
    ]

    filtered = filtered[
        ~filtered["review"].apply(is_technical_only)
    ]

    return filtered


def rank_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rank reviews by priority.
    """

    return df.sort_values(
        by=[
            "priority_score",
            "discovery_score",
            "rating"
        ],
        ascending=[
            False,
            False,
            True
        ]
    )


def mark_selected_reviews(
    master_df: pd.DataFrame,
    final_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Mark GPT selected reviews.
    """

    master_df.loc[
        final_df.index,
        "selected_for_gpt"
    ] = True

    return master_df


def save_scored_reviews(df: pd.DataFrame):

    scored = df.sort_values(
        by=[
            "priority_score",
            "discovery_score",
            "rating"
        ],
        ascending=[
            False,
            False,
            True
        ]
    )

    scored.to_csv(
        SCORED_OUTPUT,
        index=False
    )


def save_discovery_candidates(df: pd.DataFrame):

    df.to_csv(
        DISCOVERY_OUTPUT,
        index=False
    )


def save_final_dataset(df: pd.DataFrame):

    columns = [

        "original_review_id",

        "source",
        "country",

        "rating",

        "review",

        "discovery_score",
        "rating_bonus",
        "priority_score",

        "categories",
        "matched_terms",
    ]

    final = df[columns].copy()

    final.to_csv(
        FINAL_OUTPUT,
        index=False
    )


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 70)
    print("Loading reviews...")
    print("=" * 70)

    df = load_reviews()

    print(f"Loaded {len(df):,} reviews")

    print("\nScoring reviews...")

    df = score_all_reviews(df)

    save_scored_reviews(df)

    print("Saved scored_reviews.csv")

    print("\nFiltering discovery reviews...")

    discovery_df = remove_noise(df)

    discovery_df = rank_reviews(discovery_df)

    save_discovery_candidates(discovery_df)

    print(
        f"Discovery candidates: {len(discovery_df):,}"
    )

    df = mark_selected_reviews(
        df,
        discovery_df
    )

    # Save audit trail with selected_for_gpt updated
    save_scored_reviews(df)

    save_final_dataset(discovery_df)

    print("\nSaved:")
    print(f" • {SCORED_OUTPUT}")
    print(f" • {DISCOVERY_OUTPUT}")
    print(f" • {FINAL_OUTPUT}")

    print("\nSummary")

    print("-" * 70)

    print(
        f"Original Reviews        : {len(df):,}"
    )

    print(
        f"Discovery Reviews       : {len(discovery_df):,}"
    )

    print(
        f"Discovery Percentage    : "
        f"{100*len(discovery_df)/len(df):.2f}%"
    )

    print("-" * 70)


if __name__ == "__main__":
    main()
