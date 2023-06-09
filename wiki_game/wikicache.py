"""
Download a local cache of the most viewed wikipedia pages,
with their associated links.
"""
# 2023-05-23


import re
from concurrent import futures
from functools import cache
from typing import FrozenSet, Iterator, NamedTuple, Optional, Set

import requests
from common import NAMESPACES_PATTERN, USER_AGENT, debug_print
from requests import Response
from requests.exceptions import HTTPError
from rich.progress import track


class PageLinks(NamedTuple):
    title: str
    links: FrozenSet[str]


def mediawiki_api_parse(page_title: str, prop: str) -> Response:
    request_url = "https://en.wikipedia.org/w/api.php"

    params = {"action": "parse", "page": page_title, "format": "json", "prop": prop}

    reply = requests.get(request_url, params=params)

    return reply


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


@cache
def slugify_wiki_title(title: str) -> str:
    return re.sub(r"\s+", "_", title)


def save_titles():
    articles_list = [article.strip() + "\n" for article in get_all_top_article_titles()]

    with open("article_titles.txt", "w") as outfile:
        outfile.writelines(sorted(articles_list))


@cache
def is_special_page_type(page_title: str) -> bool:
    return re.match(NAMESPACES_PATTERN, page_title) is not None


def get_page_links_http(page_title: str) -> FrozenSet[str]:
    reply = mediawiki_api_parse(slugify_wiki_title(page_title), "links")

    reply.raise_for_status()

    reply_json = reply.json()

    parse_reply = reply_json.get("parse")

    if parse_reply is None:
        debug_print(f"FAILED: {slugify_wiki_title(page_title)}")
        raise HTTPError

    link_data = parse_reply["links"]

    linked_page_titles: list[str] = [
        slugify_wiki_title(title)
        for datum in link_data
        if (title := datum.get("*")) is not None and not is_special_page_type(title)
    ]

    return frozenset(linked_page_titles)


def iter_page_links(
    input_filename: str = "./article_titles.txt", n: int | None = None
) -> Iterator[PageLinks]:
    with open(input_filename, "r") as infile:
        linked_pages = [line.strip() for line in infile.readlines()]

    if n is not None:
        linked_pages = linked_pages[:n]

    with futures.ProcessPoolExecutor() as executor:
        link_futures = {
            executor.submit(get_page_links_http, name): name for name in linked_pages
        }

        for completed_task in track(
            futures.as_completed(link_futures.keys()), total=len(link_futures)
        ):
            if completed_task.exception() is not None:
                print(completed_task.exception())
                continue

            link_key = link_futures[completed_task]

            yield (PageLinks(link_key, completed_task.result()))
