import click

from decouple import UndefinedValueError, config

from kindle2notion.exporting import export_to_notion
from kindle2notion.parsing import parse_raw_clippings_text
from kindle2notion.reading import read_raw_clippings

from notion_client import Client


def _resolve(value: str, env_name: str, label: str) -> str:
    """Fall back to a .env file or the environment when the argument is omitted."""
    if value:
        return value
    try:
        return config(env_name)
    except UndefinedValueError:
        raise click.UsageError(
            f"Missing {label}. Pass it as an argument or set {env_name} "
            f"in your environment or in a .env file.")


@click.command()
@click.argument("notion_token", required=False)
@click.argument("notion_table_id", required=False)
@click.argument("clippings_file_path", required=False)
@click.option(
    "--enable_highlight_date",
    default=True,
    help='Set to False if you don\'t want to see the "Date Added" information in Notion.',
)
def main(
    notion_token,
    notion_table_id,
    clippings_file_path,
    enable_highlight_date,
):

    notion_token = _resolve(notion_token, "NOTION_TOKEN", "Notion token")
    notion_table_id = _resolve(notion_table_id, "NOTION_TABLE_ID",
                               "Notion database id")
    clippings_file_path = _resolve(clippings_file_path,
                                   "KINDLE_CLIPPINGS_PATH",
                                   "clippings file path")

    notion_client = Client(auth=notion_token)
    notion_collection_view = notion_client.databases.retrieve(notion_table_id)

    if len(notion_collection_view) > 0:
        print("Notion page is found. Analyzing clippings file...")
        all_clippings = read_raw_clippings(clippings_file_path)
        books = parse_raw_clippings_text(all_clippings)
        export_to_notion(
            books,
            enable_highlight_date,
            notion_token,
            notion_table_id,
        )
        print("Transfer complete... Exiting script...")


if __name__ == "__main__":
    main()
