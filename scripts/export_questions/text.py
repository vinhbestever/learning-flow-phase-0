import re


def strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    for entity, char in [
        ("&nbsp;", " "),
        ("&amp;", "&"),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&atilde;", "ã"),
        ("&aacute;", "á"),
        ("&agrave;", "à"),
        ("&acirc;", "â"),
        ("&#160;", " "),
    ]:
        text = text.replace(entity, char)
    return re.sub(r"\s+", " ", text).strip()


def has_media(html: str) -> bool:
    return bool(re.search(r"<(img|audio|source)\b", html or "", re.IGNORECASE))
