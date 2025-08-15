from typing import Any


def to_bool(value: Any) -> bool:
    """
    Convert various value types to boolean.

    Args:
        value: Value to convert to boolean

    Returns:
        Boolean representation of the value

    Examples:
        - "true", "True", "TRUE", "1", 1 -> True
        - "false", "False", "FALSE", "0", 0, "", None -> False
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        return value.lower() in ["true", "1", "yes", "on", "y"]

    # For None, empty collections, etc.
    return bool(value)
