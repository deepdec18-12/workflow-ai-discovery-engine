from google_play_scraper import reviews, Sort
import pandas as pd
from pathlib import Path
import time

APP_ID = "com.spotify.music"

COUNTRIES = {
    "US": "us",
    "UK": "gb",
    "IN": "in"
}

REVIEWS_PER_COUNTRY = 5000

OUTPUT = Path("data/raw")
OUTPUT.mkdir(parents=True, exist_ok=True)


def fetch_country(country_name, country_code):

    print(f"\nFetching {country_name}")

    token = None
    all_reviews = []

    while len(all_reviews) < REVIEWS_PER_COUNTRY:

        result, token = reviews(
            APP_ID,
            lang="en",
            country=country_code,
            sort=Sort.NEWEST,
            count=200,
            continuation_token=token
        )

        if not result:
            break

        all_reviews.extend(result)

        print(f"Collected {len(all_reviews)}")

        if token is None:
            break

        time.sleep(0.3)

    rows = []

    for r in all_reviews:

        rows.append({

            "source": "Google Play",

            "country": country_name,

            "reviewId": r.get("reviewId"),

            "userName": r.get("userName"),

            "rating": r.get("score"),

            "review": r.get("content"),

            "likes": r.get("thumbsUpCount"),

            "version": r.get("reviewCreatedVersion"),

            "date": r.get("at")

        })

    df = pd.DataFrame(rows)

    outfile = OUTPUT / f"google_{country_code}.csv"

    df.to_csv(outfile,index=False)

    print(outfile)


for country,code in COUNTRIES.items():

    fetch_country(country,code)
