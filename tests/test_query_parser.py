from app.ai.query_parser import extract_search_spec


def test_extract_2bhk_gurugram():
    parsed = extract_search_spec(
        "Find a 2BHK for sale under ₹80 lakh in Gurugram or Noida, with a hospital and metro nearby."
    )
    spec = parsed["search_specification"]
    assert spec["purpose"] == "buy"
    assert spec["bedrooms"] == 2
    assert spec["max_price"] == "8000000"
    assert "Gurugram" in spec["geographic_areas"]
    assert "Noida" in spec["geographic_areas"]
    assert "metro" in spec["amenity_preferences"]
    assert "hospital" in spec["amenity_preferences"]
