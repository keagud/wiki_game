"""
Download a local cache of the most viewed wikipedia pages,
with their associated links.
"""
# 2023-05-23


from typing import Optional

import requests
from requests import Response


def get_top_articles(year: int, month: int, day: Optional[int] = None) -> Response:
    request_url_base = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia.org/all-access/"
    day_str = f"{day:02d}" if day is not None else "all-days"
    request_timespan = f"{year:02d}/{month:02d}/{day_str}"
    request_url = request_url_base + request_timespan

    reply = requests.get(request_url, headers={"Content-Type": "application/json"})

    reply.raise_for_status()
    return reply


def get_year_top_article_titles(year: int):
    pass


def main():
    get_top_articles(2022, 2)


if __name__ == "__main__":
    main()
