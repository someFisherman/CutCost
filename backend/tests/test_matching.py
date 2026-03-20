"""Tests for the product matching service."""

from app.services.matching_service import _normalize_color, _normalize_storage, compute_attribute_similarity


def test_normalize_storage():
    assert _normalize_storage("256GB") == "256gb"
    assert _normalize_storage("256 GB") == "256gb"
    assert _normalize_storage("256Go") == "256gb"
    assert _normalize_storage("0.5TB") == "512gb"
    assert _normalize_storage("1TB") == "1024gb"
    assert _normalize_storage("") == ""


def test_normalize_color():
    assert _normalize_color("Natural Titanium") == "natural-titanium"
    assert _normalize_color("  Blue Titanium ") == "blue-titanium"
    assert _normalize_color("") == ""


def test_exact_attribute_match():
    result = compute_attribute_similarity(
        extracted={"storage": "256GB", "color": "Natural Titanium"},
        canonical_attrs={"storage": "256GB", "color": "Natural Titanium"},
        brand="Apple", model="15 Pro",
        canonical_brand="Apple", canonical_model="15 Pro",
    )
    assert result.confidence >= 0.40
    assert len(result.mismatch_flags) == 0


def test_storage_mismatch():
    result = compute_attribute_similarity(
        extracted={"storage": "128GB", "color": "Natural Titanium"},
        canonical_attrs={"storage": "256GB", "color": "Natural Titanium"},
        brand="Apple", model="15 Pro",
        canonical_brand="Apple", canonical_model="15 Pro",
    )
    assert any(f["code"] == "storage_mismatch" for f in result.mismatch_flags)


def test_model_variant_mismatch():
    """'15 Pro' vs '15 Pro Max' should not match."""
    result = compute_attribute_similarity(
        extracted={"storage": "256GB"},
        canonical_attrs={"storage": "256GB"},
        brand="Apple", model="15 Pro Max",
        canonical_brand="Apple", canonical_model="15 Pro",
    )
    # partial model match — should flag
    assert result.confidence < 0.40 or any(
        f["code"] in ("model_variant", "model_partial") for f in result.mismatch_flags
    )


def test_brand_mismatch_rejects():
    result = compute_attribute_similarity(
        extracted={"storage": "256GB"},
        canonical_attrs={"storage": "256GB"},
        brand="Samsung", model="S24",
        canonical_brand="Apple", canonical_model="15 Pro",
    )
    assert result.confidence == 0.0
