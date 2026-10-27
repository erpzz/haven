"""URL slugs for article titles."""
import re


def slugify(title: str, max_length: int = 40) -> str:
    """Lowercase, ASCII words joined by single hyphens, trimmed to max_length without a trailing hyphen."""
    words = re.findall(r"[a-z0-9]+", title)
    slug = "-".join(words)
    return slug[:max_length]
