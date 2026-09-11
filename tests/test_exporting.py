from kindle2notion.exporting import _prepare_aggregated_text_for_one_book

HIGHLIGHTS = [
    (
        "This is an example highlight.",
        "1",
        "100",
        "Thursday, 29 April 2021 12:31:29 AM",
        False,
    ),
    (
        "This is a second example highlight.",
        "2",
        "200",
        "Friday, 30 April 2021 12:31:29 AM",
        False,
    ),
]


def test_prepare_aggregated_text_for_one_book_should_return_the_aggregated_text_when_highlight_date_is_disabled():
    # Given
    expected = (
        "This is an example highlight.\n(Page: 1  Location: 100)\n\n"
        "This is a second example highlight.\n(Page: 2  Location: 200)\n\n",
        "Friday, 30 April 2021 12:31:29 AM",
    )

    # When
    actual = _prepare_aggregated_text_for_one_book(
        HIGHLIGHTS, enable_highlight_date=False
    )

    # Then
    assert expected == actual


def test_prepare_aggregated_text_for_one_book_should_return_the_aggregated_text_when_highlight_date_is_enabled():
    # Given
    expected = (
        "This is an example highlight.\n"
        "(Page: 1  Location: 100  Date Added: Thursday, 29 April 2021 12:31:29 AM)\n\n"
        "This is a second example highlight.\n"
        "(Page: 2  Location: 200  Date Added: Friday, 30 April 2021 12:31:29 AM)\n\n",
        "Friday, 30 April 2021 12:31:29 AM",
    )

    # When
    actual = _prepare_aggregated_text_for_one_book(
        HIGHLIGHTS, enable_highlight_date=True
    )

    # Then
    assert expected == actual


def test_prepare_aggregated_text_for_one_book_should_prefix_notes_with_a_bold_label():
    # Given
    highlights = [("This is a note.", "1", "100", "Thursday, 29 April 2021 12:31:29 AM", True)]

    # When
    aggregated_text, _ = _prepare_aggregated_text_for_one_book(
        highlights, enable_highlight_date=False
    )

    # Then
    assert aggregated_text.startswith("**Note: **This is a note.")


def test_prepare_aggregated_text_for_one_book_should_return_the_latest_date_when_the_highlights_are_out_of_order():
    # Given the most recent highlight is not the last one in the file
    highlights = [
        ("Later highlight.", "2", "200", "Friday, 30 April 2021 12:31:29 AM", False),
        ("Earlier highlight.", "1", "100", "Thursday, 29 April 2021 12:31:29 AM", False),
    ]

    # When
    _, last_date = _prepare_aggregated_text_for_one_book(
        highlights, enable_highlight_date=False
    )

    # Then
    assert last_date == "Friday, 30 April 2021 12:31:29 AM"


def test_prepare_aggregated_text_for_one_book_should_return_empty_values_when_there_are_no_highlights():
    # When
    actual = _prepare_aggregated_text_for_one_book([], enable_highlight_date=True)

    # Then
    assert actual == ("", "")
