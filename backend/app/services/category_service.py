"""Category hierarchy and guided search service.

Provides the category tree for guided browsing and smart
category matching from partial user input.
"""

import re
import unicodedata
from dataclasses import dataclass, field


@dataclass
class Category:
    id: str
    name: str
    name_de: str
    icon: str
    parent_id: str | None = None
    keywords: list[str] = field(default_factory=list)
    children: list["Category"] = field(default_factory=list)
    browse_params: dict = field(default_factory=dict)


CATEGORY_TREE: list[Category] = [
    Category(
        id="electronics", name="Electronics", name_de="Elektronik", icon="monitor",
        keywords=["elektronik", "electronics", "tech", "gadgets", "geraet", "gerat"],
        browse_params={"category": "electronics"},
        children=[
            Category(
                id="smartphone", name="Smartphones", name_de="Handys & Smartphones", icon="smartphone",
                parent_id="electronics",
                keywords=[
                    "handy", "smartphone", "phone", "telefon", "mobil", "mobile",
                    "iphone", "iphon", "ipone", "samsung", "galaxy", "pixel",
                    "huawei", "xiaomi", "oneplus",
                ],
                browse_params={"category": "smartphone"},
                children=[
                    Category(
                        id="iphone", name="Apple iPhone", name_de="Apple iPhone", icon="smartphone",
                        parent_id="smartphone",
                        keywords=["iphone", "iphon", "ipone", "apple phone"],
                        browse_params={"category": "smartphone", "brand": "Apple", "product_line": "iPhone"},
                    ),
                    Category(
                        id="samsung-galaxy", name="Samsung Galaxy", name_de="Samsung Galaxy", icon="smartphone",
                        parent_id="smartphone",
                        keywords=["samsung", "galaxy", "samung", "galxy"],
                        browse_params={"category": "smartphone", "brand": "Samsung", "product_line": "Galaxy"},
                    ),
                    Category(
                        id="google-pixel", name="Google Pixel", name_de="Google Pixel", icon="smartphone",
                        parent_id="smartphone",
                        keywords=["google", "pixel", "pixl"],
                        browse_params={"category": "smartphone", "brand": "Google", "product_line": "Pixel"},
                    ),
                ],
            ),
            Category(
                id="tablet", name="Tablets", name_de="Tablets", icon="tablet",
                parent_id="electronics",
                keywords=["tablet", "ipad", "tab", "pad"],
                browse_params={"category": "tablet"},
            ),
            Category(
                id="laptop", name="Laptops", name_de="Laptops & Notebooks", icon="laptop",
                parent_id="electronics",
                keywords=["laptop", "notebook", "macbook", "thinkpad", "chromebook", "computer", "pc"],
                browse_params={"category": "laptop"},
            ),
            Category(
                id="headphones", name="Headphones", name_de="Kopfhörer", icon="headphones",
                parent_id="electronics",
                keywords=["kopfhorer", "kopfhoerer", "headphone", "earbuds", "airpods", "earphone", "in-ear"],
                browse_params={"category": "headphones"},
            ),
            Category(
                id="tv", name="TVs & Displays", name_de="Fernseher & Displays", icon="tv",
                parent_id="electronics",
                keywords=["fernseher", "tv", "television", "monitor", "display", "bildschirm", "screen"],
                browse_params={"category": "tv"},
            ),
            Category(
                id="camera", name="Cameras", name_de="Kameras", icon="camera",
                parent_id="electronics",
                keywords=["kamera", "camera", "foto", "photo", "dslr", "mirrorless"],
                browse_params={"category": "camera"},
            ),
        ],
    ),
    Category(
        id="home", name="Home & Living", name_de="Wohnen & Haushalt", icon="home",
        keywords=["wohnen", "haushalt", "home", "living", "haus", "zuhause", "wohnung"],
        browse_params={"category": "home"},
        children=[
            Category(
                id="furniture", name="Furniture", name_de="Möbel", icon="sofa",
                parent_id="home",
                keywords=["mobel", "moebel", "furniture", "sofa", "couch", "tisch", "table", "stuhl", "chair", "schrank", "regal", "bett", "bed"],
                browse_params={"category": "furniture"},
                children=[
                    Category(
                        id="sofas", name="Sofas & Couches", name_de="Sofas & Couches", icon="sofa",
                        parent_id="furniture",
                        keywords=["sofa", "couch", "ecksofa", "schlafsofa"],
                        browse_params={"category": "furniture", "q": "sofa"},
                    ),
                ],
            ),
            Category(
                id="appliances", name="Appliances", name_de="Haushaltsgeräte", icon="zap",
                parent_id="home",
                keywords=["haushaltsgerat", "haushaltsgeraet", "appliance", "gerat", "geraet"],
                browse_params={"category": "appliances"},
                children=[
                    Category(
                        id="vacuum", name="Vacuum Cleaners", name_de="Staubsauger", icon="wind",
                        parent_id="appliances",
                        keywords=["staubsauger", "vacuum", "sauger", "dyson", "roomba"],
                        browse_params={"category": "appliances", "q": "staubsauger"},
                        children=[
                            Category(
                                id="handheld-vacuum", name="Handheld Vacuums", name_de="Handstaubsauger", icon="wind",
                                parent_id="vacuum",
                                keywords=["handstaubsauger", "handheld", "akku-staubsauger", "akkusauger"],
                                browse_params={"category": "appliances", "q": "handstaubsauger"},
                            ),
                        ],
                    ),
                ],
            ),
        ],
    ),
    Category(
        id="sports", name="Sports & Outdoors", name_de="Sport & Outdoor", icon="dumbbell",
        keywords=["sport", "outdoor", "fitness", "training"],
        browse_params={"category": "sports"},
    ),
    Category(
        id="fashion", name="Fashion", name_de="Mode & Kleidung", icon="shirt",
        keywords=["mode", "fashion", "kleidung", "clothing", "schuhe", "shoes"],
        browse_params={"category": "fashion"},
    ),
]


def _normalize(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^\w\s]", "", text).strip()


def _flatten_categories(cats: list[Category], depth: int = 0) -> list[tuple[Category, int, str]]:
    """Flatten tree into list of (category, depth, breadcrumb)."""
    results: list[tuple[Category, int, str]] = []
    for cat in cats:
        results.append((cat, depth, ""))
        for child_result in _flatten_categories(cat.children, depth + 1):
            results.append(child_result)
    return results


def _build_breadcrumb(cat: Category, all_cats: dict[str, Category]) -> str:
    parts = [cat.name_de]
    current = cat
    while current.parent_id and current.parent_id in all_cats:
        current = all_cats[current.parent_id]
        parts.insert(0, current.name_de)
    return " > ".join(parts)


def _build_cat_map(cats: list[Category]) -> dict[str, Category]:
    result: dict[str, Category] = {}
    for cat in cats:
        result[cat.id] = cat
        result.update(_build_cat_map(cat.children))
    return result


CAT_MAP = _build_cat_map(CATEGORY_TREE)


@dataclass
class CategorySuggestion:
    id: str
    name: str
    name_de: str
    icon: str
    breadcrumb: str
    depth: int
    browse_params: dict
    match_score: float


def search_categories(query: str, limit: int = 8) -> list[CategorySuggestion]:
    """Search categories by partial text, returning matches sorted by relevance."""
    if not query or len(query) < 1:
        return [
            CategorySuggestion(
                id=cat.id, name=cat.name, name_de=cat.name_de, icon=cat.icon,
                breadcrumb=_build_breadcrumb(cat, CAT_MAP),
                depth=0, browse_params=cat.browse_params, match_score=1.0,
            )
            for cat in CATEGORY_TREE
        ]

    normalized = _normalize(query)
    results: list[CategorySuggestion] = []

    def _score_category(cat: Category, depth: int) -> float | None:
        name_norm = _normalize(cat.name_de)
        name_en_norm = _normalize(cat.name)

        if name_norm.startswith(normalized) or name_en_norm.startswith(normalized):
            return 1.0 - depth * 0.1

        for kw in cat.keywords:
            if kw.startswith(normalized) or normalized.startswith(kw):
                return 0.9 - depth * 0.1
            if normalized in kw or kw in normalized:
                return 0.7 - depth * 0.1

        if normalized in name_norm or normalized in name_en_norm:
            return 0.6 - depth * 0.1

        return None

    def _search_tree(cats: list[Category], depth: int = 0):
        for cat in cats:
            score = _score_category(cat, depth)
            if score is not None and score > 0:
                results.append(CategorySuggestion(
                    id=cat.id, name=cat.name, name_de=cat.name_de, icon=cat.icon,
                    breadcrumb=_build_breadcrumb(cat, CAT_MAP),
                    depth=depth, browse_params=cat.browse_params, match_score=score,
                ))
            _search_tree(cat.children, depth + 1)

    _search_tree(CATEGORY_TREE)

    results.sort(key=lambda r: (-r.match_score, r.depth, r.name_de))
    return results[:limit]


def get_category_children(category_id: str) -> list[CategorySuggestion]:
    """Get direct children of a category for drill-down."""
    cat = CAT_MAP.get(category_id)
    if not cat:
        return []

    return [
        CategorySuggestion(
            id=child.id, name=child.name, name_de=child.name_de, icon=child.icon,
            breadcrumb=_build_breadcrumb(child, CAT_MAP),
            depth=0, browse_params=child.browse_params, match_score=1.0,
        )
        for child in cat.children
    ]


def get_top_categories() -> list[CategorySuggestion]:
    """Get top-level categories for the homepage."""
    return [
        CategorySuggestion(
            id=cat.id, name=cat.name, name_de=cat.name_de, icon=cat.icon,
            breadcrumb=cat.name_de, depth=0, browse_params=cat.browse_params,
            match_score=1.0,
        )
        for cat in CATEGORY_TREE
    ]
