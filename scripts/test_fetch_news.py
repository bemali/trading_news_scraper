import argparse
import json
import os
from pathlib import Path
import sys
from dotenv import load_dotenv

# Get the project root (one level up from 'scripts/')
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
from src.news_scrape import fetch_news



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test fetch_news with custom parameters")
    parser.add_argument("--categories", default="business,tech", help="Comma-separated categories")
    parser.add_argument("--limit", type=int, default=3, help="Number of articles to fetch")
    parser.add_argument("--out", default="", help="Optional path to write JSON output")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    api_key = os.getenv("NEWS_API_KEY", "")


    for page in range(5):
        articles = fetch_news(api_key, args.categories, args.limit, page=page+1)
        payload = [
            {
                "id": a.id,
                "title": a.title,
                "description": a.description,
                "url": a.url,
                "published_at": a.published_at,
                "source": a.source,
            }
            for a in articles
        ]

        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(f"Wrote {len(payload)} articles to {out_path}")
        else:
            print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
