def mask_nhs_number(nhs_number: str) -> str:
    """Keeps the last three digits, so an NHS number never appears in full in logs."""
    return f"{'*' * max(len(nhs_number) - 3, 0)}{nhs_number[-3:]}"
