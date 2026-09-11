"""Tests for the Notion API 2025-09-03 data source contract and the row index.

Note: stub ``has_more``/``next_cursor`` on every query response. ``collect_paginated_api``
reads both, and a bare MagicMock returns truthy for them, so the helper paginates forever
and the test hangs instead of failing.
"""
from unittest.mock import MagicMock, patch

from kindle2notion.exporting import export_to_notion

DATABASE_ID = "db-id"
DATA_SOURCE_ID = "ds-id"


def _row(title, highlight_count, page_id="page-id"):
    return {
        "id": page_id,
        "properties": {
            "Title": {"title": [{"plain_text": title}]},
            "Highlights": {"number": highlight_count},
        },
    }


def _build_client(existing_rows):
    client = MagicMock()
    client.databases.retrieve.return_value = {
        "id": DATABASE_ID,
        "data_sources": [{"id": DATA_SOURCE_ID, "name": "Kindle Highlights & Notes"}],
    }
    client.data_sources.query.return_value = {
        "results": existing_rows,
        "has_more": False,
        "next_cursor": None,
    }
    client.pages.create.return_value = _row("created", 0, page_id="new-page-id")
    client.pages.retrieve.return_value = {"id": "page-id"}
    client.blocks.children.list.return_value = {"results": []}
    return client


def _book(title, author="Albert Einstein", count=1):
    return {
        title: {
            "author": author,
            "highlights": [
                (
                    f"Highlight {i}.",
                    "1",
                    "100",
                    "Friday, 30 April 2021 12:31:29 AM",
                    False,
                )
                for i in range(count)
            ],
        }
    }


def _export(books, client):
    with patch("kindle2notion.exporting.Client", return_value=client):
        export_to_notion(
            books,
            enable_highlight_date=True,
            notion_token="token",
            notion_table_id=DATABASE_ID,
        )


def test_export_to_notion_queries_the_data_source_not_the_database():
    # Given
    client = _build_client(existing_rows=[])

    # When
    _export(_book("Relativity"), client)

    # Then
    client.data_sources.query.assert_called_once()
    assert client.data_sources.query.call_args.kwargs["data_source_id"] == DATA_SOURCE_ID


def test_export_to_notion_fetches_the_existing_rows_once_for_the_whole_run():
    # Given three books to sync
    client = _build_client(existing_rows=[])
    books = {}
    for title in ["Book A", "Book B", "Book C"]:
        books.update(_book(title))

    # When
    _export(books, client)

    # Then the database is scanned once, not once per book
    assert client.data_sources.query.call_count == 1
    assert client.databases.retrieve.call_count == 1


def test_export_to_notion_skips_a_book_whose_highlight_count_is_unchanged():
    # Given
    client = _build_client(existing_rows=[_row("Relativity", 2)])

    # When
    _export(_book("Relativity", count=2), client)

    # Then
    client.pages.create.assert_not_called()
    client.pages.update.assert_not_called()


def test_export_to_notion_updates_a_book_whose_highlight_count_grew():
    # Given
    client = _build_client(existing_rows=[_row("Relativity", 1)])

    # When
    _export(_book("Relativity", count=3), client)

    # Then
    client.pages.create.assert_not_called()
    client.pages.update.assert_called_once()
    assert (
        client.pages.update.call_args.kwargs["properties"]["Highlights"]["number"] == 3
    )


def test_export_to_notion_ignores_existing_rows_that_have_an_empty_title():
    # Given a row with no title, which used to raise IndexError
    untitled = {"id": "untitled", "properties": {"Title": {"title": []}, "Highlights": {"number": 0}}}
    client = _build_client(existing_rows=[untitled, _row("Relativity", 1)])

    # When
    _export(_book("Relativity", count=1), client)

    # Then the untitled row is skipped and the matching book is left alone
    client.pages.create.assert_not_called()


def test_export_to_notion_does_not_set_last_highlighted_when_there_is_no_date():
    # Given a book whose highlights carry no date, and a count that changed so
    # the book is not skipped before it reaches pages.update
    client = _build_client(existing_rows=[_row("Relativity", 0)])
    books = {
        "Relativity": {
            "author": "Albert Einstein",
            "highlights": [("A highlight.", "1", "100", "", False)],
        }
    }

    # When
    _export(books, client)

    # Then
    properties = client.pages.update.call_args.kwargs["properties"]
    assert "Last Highlighted" not in properties
    assert "Last Synced" in properties
