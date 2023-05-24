import re
from typing import Final

USER_AGENT: Final = (
    "wiki_game/0.1 (https://github.com/keagud/wiki_game/; keagud@protonmail.com)"
)


SUBJECT_NAMESPACES: Final = [
    "User",
    "Wikipedia",
    "File",
    "MediaWiki",
    "Template",
    "Help",
    "Category",
    "Portal",
    "Draft",
    "TimedText",
    "Module",
]


ALL_NAMESPACES: Final = SUBJECT_NAMESPACES + [
    f"{item} talk" for item in SUBJECT_NAMESPACES
]


NAMESPACES_PATTERN = re.compile("|".join(ALL_NAMESPACES))
