import time
import requests
import pandas as pd
from pathlib import Path

SPOTIFY_APP_STORE_ID = "324684580"

APP_STORE_COUNTRIES = [
    "us",
    "gb",
    "in",
    "au",
    "ca",
    "nz",
    "ie",
    "sg",
]

OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

session = requests.Session()


def fetch_country(country, max_pages=20):

    reviews = []

    print(f"\nFetching {country.upper()}")

    for page in range(1, max_pages + 1):

        url = (
            f"https://itunes.apple.com/{country}/rss/customerreviews/"
            f"page={page}/id={SPOTIFY_APP_STORE_ID}/sortby=mostrecent/json"
        )

        try:

            r = session.get(url, timeout=15)

            if r.status_code != 200:
                break

            feed = r.json().get("feed", {})
            entries = feed.get("entry", [])

            if not entries:
                break

            if page == 1:
                entries = entries[1:]

            if not entries:
                break

            for e in entries:

                reviews.append({

                    "source": "Apple App Store",

                    "country": country.upper(),

                    "reviewId": e["id"]["label"],

                    "userName": e["author"]["name"]["label"],

                    "rating": int(e["im:rating"]["label"]),

                    "review": e["content"]["label"].strip(),

                    "title": e["title"]["label"],

                    "date": e["updated"]["label"],

                    "version": e.get("im:version", {}).get("label"),

                    "voteCount": e.get("im:voteCount", {}).get("label"),

                })

            print(f"Page {page}: {len(entries)} reviews")

            time.sleep(0.25)

        except Exception as ex:

            print(ex)
            break

    return reviews


all_reviews = []

seen = set()

for country in APP_STORE_COUNTRIES:

    country_reviews = fetch_country(country)

    added = 0

    for review in country_reviews:

        if review["reviewId"] in seen:
            continue

        seen.add(review["reviewId"])
        all_reviews.append(review)
        added += 1

    print(f"Added {added}")

df = pd.DataFrame(all_reviews)

outfile = OUTPUT_DIR / "apple_reviews.csv"

df.to_csv(outfile, index=False)

print("\nDone")
print(outfile)
print(f"Total unique reviews: {len(df)}")
