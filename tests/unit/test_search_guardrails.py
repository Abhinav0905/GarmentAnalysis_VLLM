from app.guardrails.search_guardrails import sanitize_search_interpretation


def test_search_interpretation_is_normalized_against_available_filters():
    raw_output = {
        "full_text_query": "neckline detail",
        "garment_type": "dress",
        "designer": "taylor",
        "city": "milan",
        "year": 2026,
    }
    available_filters = {
        "garment_type": ["dress", "jacket"],
        "designer": ["Taylor", "Jordan"],
        "city": ["Milan"],
        "year": ["2026"],
    }

    interpretation = sanitize_search_interpretation(
        raw_output=raw_output,
        original_query="Taylor dress with neckline detail",
        available_filters=available_filters,
    )

    assert interpretation.full_text_query == "neckline detail"
    assert interpretation.garment_type == "dress"
    assert interpretation.designer == "Taylor"
    assert interpretation.city == "Milan"
    assert interpretation.year == 2026


def test_search_interpretation_drops_conversational_filler_text():
    interpretation = sanitize_search_interpretation(
        raw_output={
            "full_text_query": "show me some images of some nice",
            "garment_type": "dress",
        },
        original_query="Show me some images of some nice dress",
        available_filters={"garment_type": ["dress"]},
    )

    assert interpretation.garment_type == "dress"
    assert interpretation.full_text_query is None

