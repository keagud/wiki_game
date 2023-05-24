"""
Download a local cache of the most viewed wikipedia pages,
with their associated links.
"""
# 2023-05-23


from concurrent import futures
from typing import FrozenSet, Optional, Set

import requests
from common import USER_AGENT
from requests import Response
from requests.exceptions import HTTPError
from rich.progress import track


def get_top_articles(year: int, month: int, day: Optional[int] = None) -> Response:
    request_url_base = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia.org/all-access/"
    day_str = f"{day:02d}" if day is not None else "all-days"
    request_timespan = f"{year:02d}/{month:02d}/{day_str}"
    request_url = request_url_base + request_timespan

    reply = requests.get(
        request_url,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )

    try:
        reply.raise_for_status()

    except HTTPError as err:
        if reply.status_code == 404:
            err.add_note("404")
        raise err

    return reply


def parse_top_pages_response(response: Response) -> Set[str]:
    response_json = response.json()

    articles: list[dict] = response_json["items"][0]["articles"]
    page_names = [article_info.get("article") for article_info in articles]
    return set(
        [
            page
            for page in page_names
            if page is not None and page.lower() != "main_page"
        ]
    )


def get_year_top_article_titles(year: int) -> FrozenSet[str]:
    all_year_articles: Set[str] = set()

    for month_n in range(1, 13):
        try:
            month_response = get_top_articles(year, month_n)
            page_names = parse_top_pages_response(month_response)
            all_year_articles.update(page_names)

        except HTTPError as err:
            if "404" in err.__notes__:
                return frozenset(all_year_articles)

            continue

    return frozenset(all_year_articles)


def get_all_top_article_titles():
    all_articles: Set[str] = set()

    with futures.ThreadPoolExecutor() as executor:
        articles_dl = [
            executor.submit(get_year_top_article_titles, y) for y in range(2001, 2023)
        ]

        for article_future in track(
            futures.as_completed(articles_dl), total=len(articles_dl)
        ):
            all_articles.update(article_future.result())

    return all_articles


def main():
    articles_list = [article.strip() + "\n" for article in get_all_top_article_titles()]

    with open("article_titles.txt", "w") as outfile:
        outfile.writelines(sorted(articles_list))


if __name__ == "__main__":
    main()
