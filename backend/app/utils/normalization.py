"""Text normalization utilities for product matching."""

import re
import unicodedata

BRAND_ALIASES: dict[str, str] = {
    "apple": "Apple",
    "samsung": "Samsung",
    "samsung electronics": "Samsung",
    "google": "Google",
    "sony": "Sony",
    "sony corporation": "Sony",
    "nvidia": "NVIDIA",
    "lg": "LG",
    "lg electronics": "LG",
    "huawei": "Huawei",
    "xiaomi": "Xiaomi",
    "oneplus": "OnePlus",
    "motorola": "Motorola",
    "bosch": "Bosch",
    "lego": "LEGO",
    "canon": "Canon",
    "nikon": "Nikon",
    "asus": "ASUS",
    "msi": "MSI",
    "evga": "EVGA",
    "gigabyte": "Gigabyte",
    "zotac": "Zotac",
}

CONDITION_MAP: dict[str, str] = {
    "new": "new",
    "neu": "new",
    "neuf": "new",
    "nuovo": "new",
    "refurbished": "refurbished",
    "refurb": "refurbished",
    "generalüberholt": "refurbished",
    "reconditionné": "refurbished",
    "ricondizionato": "refurbished",
    "renewed": "refurbished",
    "used": "used",
    "gebraucht": "used",
    "occasion": "used",
    "usato": "used",
    "open box": "open_box",
    "open-box": "open_box",
    "b-ware": "open_box",
    "b ware": "open_box",
    "like new": "open_box",
    "wie neu": "open_box",
}


def normalize_brand(raw: str) -> str:
    key = raw.strip().lower()
    return BRAND_ALIASES.get(key, raw.strip())


def normalize_condition(raw: str) -> str:
    key = raw.strip().lower()
    return CONDITION_MAP.get(key, "unknown")


def normalize_storage(raw: str) -> str:
    if not raw:
        return ""
    s = raw.strip().lower().replace(" ", "")
    if s.endswith("tb"):
        try:
            val = float(s[:-2]) * 1024
            return f"{int(val)}gb"
        except ValueError:
            return s
    if s.endswith("go"):
        s = s[:-2] + "gb"
    return s


def normalize_color(raw: str) -> str:
    if not raw:
        return ""
    return raw.strip().lower().replace(" ", "-").replace("_", "-")


def normalize_text(raw: str) -> str:
    text = raw.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\s+", " ", text)
    return text


def slugify(text: str) -> str:
    slug = normalize_text(text)
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")
