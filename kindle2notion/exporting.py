from datetime import datetime
from typing import Dict, List, Optional, Tuple

from dateparser import parse
from dateutil.tz import tzlocal

from notion_client import Client
from notion_client.helpers import collect_paginated_api

ITALIC = "*"
BOLD = "**"

# The format parsing.py writes dates in, e.g. "Friday, 30 April 2021 12:31:29 AM".
HIGHLIGHT_DATE_FORMAT = "%A, %d %B %Y %I:%M:%S %p"

# Notion rejects a rich_text element longer than this.
RICH_TEXT_CHUNK_SIZE = 2000


def export_to_notion(
    books: Dict,
    enable_highlight_date: bool,
    notion_token: str,
    notion_table_id: str,
) -> None:
    print("Initiating transfer...\n")

    notion_client = Client(auth=notion_token)
    data_source_id = _resolve_data_source_id(notion_client, notion_table_id)
    # Read the whole database once up front. Querying per book turns a sync into
    # O(books x rows) requests, which dominates the runtime on a real library.
    rows_by_title = _fetch_rows_by_title(notion_client, data_source_id)

    for title in books:
        print("Checking book: " + title)

        book = books[title]
        author = book["author"]
        highlights = book["highlights"]
        highlight_count = len(highlights)
        (
            aggregated_text_from_highlights,
            last_date,
        ) = _prepare_aggregated_text_for_one_book(highlights,
                                                  enable_highlight_date)
        message = _add_book_to_notion(
            notion_client,
            rows_by_title,
            title,
            author,
            highlight_count,
            aggregated_text_from_highlights,
            last_date,
            notion_table_id,
        )
        if message != "None to add":
            print("✓", message)


def _resolve_data_source_id(notion_client: Client, notion_table_id: str) -> str:
    # Notion API 2025-09-03 put data sources between a database and its rows;
    # databases.query no longer exists in notion-sdk-py >= 3.0.
    database = notion_client.databases.retrieve(notion_table_id)
    return database["data_sources"][0]["id"]


def _fetch_rows_by_title(notion_client: Client, data_source_id: str) -> Dict:
    rows = collect_paginated_api(notion_client.data_sources.query,
                                 data_source_id=data_source_id)
    rows_by_title = {}
    for row in rows:
        title_property = row["properties"].get("Title", {}).get("title")
        if not title_property:
            # A row with an empty Title cannot match a book; skipping it also
            # keeps the lookup below from raising IndexError.
            continue
        rows_by_title[title_property[0]["plain_text"]] = row
    return rows_by_title


def _parse_highlight_date(date: str) -> Optional[datetime]:
    try:
        return datetime.strptime(date, HIGHLIGHT_DATE_FORMAT)
    except ValueError:
        return parse(date)


def _prepare_aggregated_text_for_one_book(
        highlights: List, enable_highlight_date: bool) -> Tuple[str, str]:
    aggregated_text = ""
    dates = []

    for highlight in highlights:
        text, page, location, date, isNote = highlight
        if isNote is True:
            aggregated_text += BOLD + "Note: " + BOLD

        aggregated_text += text + "\n("
        if page != "":
            aggregated_text += "Page: " + page + "  "
        if location != "":
            aggregated_text += "Location: " + location + "  "
        if enable_highlight_date and (date != ""):
            aggregated_text += "Date Added: " + date

        aggregated_text = aggregated_text.strip() + ")\n\n"

        if date != "":
            dates.append(date)

    # The clippings file is not guaranteed to be in chronological order, so take
    # the latest date rather than whichever highlight happens to come last.
    last_date = max(dates, key=lambda d: _parse_highlight_date(d) or datetime.min,
                    default="")
    return aggregated_text, last_date


def _add_book_to_notion(
    notion_client: Client,
    rows_by_title: Dict,
    title: str,
    author: str,
    highlight_count: int,
    aggregated_text: str,
    last_date: str,
    notion_table_id: str,
) -> str:
    row = rows_by_title.get(title)
    current_highlight_count = 0

    if row is not None:
        current_highlight_count = (row["properties"].get("Highlights",
                                                         {}).get("number") or 0)
        if current_highlight_count == highlight_count:
            return "None to add"

    title_and_author = title + " (" + str(author) + ")"
    print(title_and_author)
    print("-" * len(title_and_author))

    if row is None:
        new_page = {
            "Title": {
                "title": [{
                    "text": {
                        "content": title
                    }
                }]
            },
            "Author": {
                "type": "rich_text",
                "rich_text": [{
                    "type": "text",
                    "text": {
                        "content": author
                    },
                }],
            },
            "Highlights": {
                "type": "number",
                "number": 0
            },
        }
        row = notion_client.pages.create(
            parent={"database_id": notion_table_id}, properties=new_page)
        rows_by_title[title] = row

    parent_page = notion_client.pages.retrieve(row['id'])

    for all_blocks in notion_client.blocks.children.list(
            parent_page['id'])['results']:
        notion_client.blocks.delete(all_blocks['id'])

    # Split aggregated_text into paragraphs
    chunks = [{
        'type': 'text',
        'text': {
            'content': aggregated_text[i:i + RICH_TEXT_CHUNK_SIZE]
        }
    } for i in range(0, len(aggregated_text), RICH_TEXT_CHUNK_SIZE)]

    new_block = {
        'object': 'block',
        'type': 'paragraph',
        'paragraph': {
            'rich_text': chunks,
        }
    }
    notion_client.blocks.children.append(block_id=parent_page['id'],
                                         children=[new_block])

    diff_count = highlight_count - current_highlight_count
    updated_info = {
        "Highlights": {
            "type": "number",
            "number": highlight_count
        },
        "Last Synced": {
            "type": "date",
            "date": {
                'start': datetime.now(tzlocal()).isoformat()
            }
        },
    }

    parsed_last_date = _parse_highlight_date(last_date) if last_date else None
    if parsed_last_date is not None:
        updated_info["Last Highlighted"] = {
            "type": "date",
            "date": {
                'start': parsed_last_date.replace(tzinfo=tzlocal()).isoformat()
            }
        }

    notion_client.pages.update(page_id=row['id'], properties=updated_info)

    message = str(diff_count) + " notes / highlights added successfully\n"
    return message
