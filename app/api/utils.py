BOOL_LIKE_VALUES = [
    "true",
    "True",
    "1",
    "on",
    "yes",
    "false",
    "False",
    "0",
    "off",
    "no",
]


def is_bool_like(value: str) -> bool:
    return value in BOOL_LIKE_VALUES
