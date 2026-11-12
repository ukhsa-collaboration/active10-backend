ONE_YEAR_IN_SECONDS = 31536000


def validate_date_filters(date: int | None, start_date: int | None, end_date: int | None) -> None:
    """Raises ValueError with a client-facing message when the filters do not combine."""
    if date and (start_date or end_date):
        raise ValueError("Cannot use date filter with start_date or end_date filters")

    if (start_date and not end_date) or (end_date and not start_date):
        raise ValueError("Both start_date and end_date filters must be used together")

    if start_date and end_date:
        if start_date > end_date:
            raise ValueError("Start date cannot be greater than end date")
        if end_date - start_date > ONE_YEAR_IN_SECONDS:
            raise ValueError("Date range cannot be greater than 1 year")
