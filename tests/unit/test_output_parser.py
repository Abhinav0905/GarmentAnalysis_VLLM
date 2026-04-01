from app.utils.helpers import extract_json_object


def test_extract_json_object_from_wrapped_text():
    raw_text = """
    The model returned:
    {"description":"Black dress","garment_type":"dress"}
    """
    parsed = extract_json_object(raw_text)
    assert parsed["description"] == "Black dress"
    assert parsed["garment_type"] == "dress"

