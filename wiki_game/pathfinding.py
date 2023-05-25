from __future__ import annotations

from typing import FrozenSet

from common import debug_print
from database import DbWriter
from wikicache import PageLinks, get_page_links_http, slugify_wiki_title


def get_db_or_http_links(page_title: str, db: DbWriter) -> FrozenSet[str]:
    title_slug = slugify_wiki_title(page_title)
    db_result = db.fetch_page_db_links(title_slug)

    if db_result is not None:
        return frozenset(db_result)

    http_result = get_page_links_http(title_slug)

    fetched_page_data = PageLinks(title_slug, http_result)

    db.write_page_data(fetched_page_data)

    debug_print(f"Wrote to database: {len(http_result)} links for {title_slug}")

    return http_result


class Page:
    def __init__(self, db_interface: DbWriter, title_slug: str):
        self.db_interface = db_interface
        self.title_slug = slugify_wiki_title(title_slug)
        self.links = self._get_links()

    def _get_links(self) -> FrozenSet[str]:
        return get_db_or_http_links(self.title_slug, self.db_interface)


def main():
    with DbWriter() as db:
        Page(db, "Major_Arcana")


if __name__ == "__main__":
    main()
