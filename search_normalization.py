import re
import unicodedata


BASE_SEARCH_CHAR_REPLACEMENTS = str.maketrans(
    {
        "ß": "ss",
        "Æ": "ae",
        "æ": "ae",
        "Œ": "oe",
        "œ": "oe",
        "Ø": "o",
        "ø": "o",
        "Ł": "l",
        "ł": "l",
        "Đ": "d",
        "đ": "d",
        "Ð": "d",
        "ð": "d",
        "Þ": "th",
        "þ": "th",
        "Ħ": "h",
        "ħ": "h",
        "ı": "i",
        "Ĳ": "ij",
        "ĳ": "ij",
        "Ə": "e",
        "ə": "e",
        "Α": "a",
        "α": "a",
        "Β": "b",
        "β": "b",
        "Γ": "g",
        "γ": "g",
        "Δ": "d",
        "δ": "d",
        "Ε": "e",
        "ε": "e",
        "Ζ": "z",
        "ζ": "z",
        "Η": "i",
        "η": "i",
        "Θ": "th",
        "θ": "th",
        "Ι": "i",
        "ι": "i",
        "Κ": "k",
        "κ": "k",
        "Λ": "l",
        "λ": "l",
        "Μ": "m",
        "μ": "m",
        "Ν": "n",
        "ν": "n",
        "Ξ": "x",
        "ξ": "x",
        "Ο": "o",
        "ο": "o",
        "Π": "p",
        "π": "p",
        "Ρ": "r",
        "ρ": "r",
        "Σ": "s",
        "σ": "s",
        "ς": "s",
        "Τ": "t",
        "τ": "t",
        "Υ": "y",
        "υ": "y",
        "Φ": "f",
        "φ": "f",
        "Χ": "ch",
        "χ": "ch",
        "Ψ": "ps",
        "ψ": "ps",
        "Ω": "o",
        "ω": "o",
    }
)

LOOSE_SEARCH_PRE_REPLACEMENTS = str.maketrans(
    {
        "Ä": "ae",
        "ä": "ae",
        "Ö": "oe",
        "ö": "oe",
        "Ü": "ue",
        "ü": "ue",
    }
)

SEARCH_SEPARATOR_RE = re.compile(r"[\s'’`.\-_/]+")
LOOSE_DIGRAPH_COLLAPSE_REPLACEMENTS = (
    ("ae", "a"),
    ("oe", "o"),
    ("ue", "u"),
)


def _normalize_search_text(
    value: str | None,
    *,
    pre_replacements: dict[int, str] | None = None,
    char_replacements: dict[int, str] | None = None,
) -> str:
    if value is None:
        return ""

    text = unicodedata.normalize("NFKC", str(value))
    if pre_replacements:
        text = text.translate(pre_replacements)
    text = unicodedata.normalize("NFKD", text)
    if char_replacements:
        text = text.translate(char_replacements)
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = unicodedata.normalize("NFKC", text).casefold()
    text = SEARCH_SEPARATOR_RE.sub("", text)
    return text.strip()


def normalize_search_text(value: str | None) -> str:
    return _normalize_search_text(value, char_replacements=BASE_SEARCH_CHAR_REPLACEMENTS)


def normalize_search_text_loose(value: str | None) -> str:
    return _normalize_search_text(
        value,
        pre_replacements=LOOSE_SEARCH_PRE_REPLACEMENTS,
        char_replacements=BASE_SEARCH_CHAR_REPLACEMENTS,
    )


def collapse_loose_search_text(value: str | None) -> str:
    collapsed = value or ""
    for source, target in LOOSE_DIGRAPH_COLLAPSE_REPLACEMENTS:
        collapsed = collapsed.replace(source, target)
    return collapsed


def build_search_normalized_keys(value: str | None) -> tuple[list[str], list[str]]:
    strict_keys: list[str] = []
    loose_keys: list[str] = []

    base_key = normalize_search_text(value)
    loose_key = normalize_search_text_loose(value)
    collapsed_loose_key = collapse_loose_search_text(loose_key)

    for key in (base_key, collapsed_loose_key):
        if key and key not in strict_keys:
            strict_keys.append(key)

    if loose_key and loose_key not in loose_keys:
        loose_keys.append(loose_key)

    return strict_keys, loose_keys
