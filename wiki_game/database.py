import sqlite3
from pathlib import Path
from typing import Final, Optional

from wikicache import PageLinks, iter_page_links


class DbWriter:
    page_insert_query: Final = """
    INSERT INTO page_mapping
        (page_title, links_table_id)
        VALUES (?, ?);
        """

    new_link_table_query: Final = "CREATE TABLE _{table_id} (link TEXT)"

    def __init__(
        self,
        db_path: Optional[Path | str] = None,
        ignore_duplicate: bool = True,
    ) -> None:
        if db_path is None:
            db_path = Path(__file__).parent.joinpath("pages.db")
        else:
            db_path = Path(db_path)

        self.db_path = db_path
        self.ignore_duplicate = ignore_duplicate

        self.connection = sqlite3.connect(self.db_path)

        # in case of interruption: start assigining table ids starting
        # from the largest existing id at init time
        page_map_ids = [
            int(table_id_n)
            for table_id in self.tables
            if (table_id_n := table_id.strip("_")).isnumeric()
        ]
        self.current_id = max(page_map_ids) if page_map_ids else 0

    @property
    def tables(self) -> list[str]:
        cursor = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        )
        return [str(row[0]) for row in cursor.fetchall()]

    @property
    def next_id(self) -> int:
        self.current_id += 1
        return self.current_id

    def __enter__(self):
        self.cursor = self.connection.cursor()

        init_command = """
            CREATE TABLE IF NOT EXISTS page_mapping (
                page_title TEXT PRIMARY KEY,
                links_table_id INTEGER
            );
            """
        self.cursor.execute(init_command)

        self.connection.commit()
        return self

    def __exit__(self, exc_type: type, exc_value: BaseException, traceback):
        if self.ignore_duplicate and isinstance(exc_value, sqlite3.IntegrityError):
            return True

        self.connection.commit()
        self.connection.close()

        return False

    def write_page_data(self, page: PageLinks):
        new_table_id = self.next_id

        command = self.new_link_table_query.format(table_id=new_table_id)
        print(f"Fetching '{page.title}'", end="...")
        self.connection.execute(command)

        insert_data = [(link_str,) for link_str in page.links]

        self.connection.executemany(
            f"INSERT INTO _{new_table_id} (link) VALUES (?)", insert_data
        )

        print("\tOK")
        self.connection.execute(
            self.page_insert_query,
            (
                page.title,
                new_table_id,
            ),
        )

        self.connection.commit()
        print(f"Wrote to _{new_table_id}")


def main():
    with DbWriter() as db:
        for p in iter_page_links():
            db.write_page_data(p)


if __name__ == "__main__":
    main()
