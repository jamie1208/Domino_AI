"""EventParserSkill v2 regression checks without network or LLM calls."""
from app.schemas import Scenario
from app.skills.event_parser import EventParserSkill


def test_disaster_with_supply_interruption_retains_primary_disaster_type():
    input_value = Scenario(description="假設日本九州發生規模 7.2 地震，關鍵材料供應中斷 30 天")
    result = EventParserSkill().run(input_value)
    assert result.event_type == "natural_disaster"
    assert result.duration_days == 30
    assert result.severity is None


def test_magnitude_is_metadata_not_risk_severity():
    s = Scenario(description="假設九州規模 7.2 地震，造成材料供應中斷 30 天")
    detail = EventParserSkill().inspect(s)
    assert detail.earthquake_magnitude == 7.2
    assert "severity" in detail.missing_required
    assert "seed_nodes" in detail.missing_required


def test_existing_scenario_fields_are_preserved():
    s = Scenario(description="地震與關稅衝擊 30 天", event_type="economic_policy", duration_days=21,
                 severity=0.4, region="台灣", product="晶片", seed_nodes=["材料產業"])
    parsed = EventParserSkill().run(s)
    assert parsed.event_type == "economic_policy"
    assert parsed.duration_days == 21
    assert parsed.severity == 0.4
    assert parsed.seed_nodes == ["材料產業"]
    assert EventParserSkill().inspect(parsed).earthquake_magnitude is None


def test_overly_long_duration_does_not_break_pydantic_contract():
    s = Scenario(description="假設供應中斷9999天")
    parsed = EventParserSkill().run(s)
    assert parsed.duration_days is None
    assert parsed.event_type == "supply_chain"


def test_case_insensitive_english_parsing():
    s = Scenario(description="EARTHQUAKE caused disruption for 12 days")
    parsed = EventParserSkill().run(s)
    assert parsed.event_type == "natural_disaster"
    assert parsed.duration_days == 12


def test_unknown_event_type_stays_unknown():
    s = Scenario(description="有企業出現未明原因的異常")
    parsed = EventParserSkill().run(s)
    assert parsed.event_type == "unknown"
    assert "event_type" in EventParserSkill().inspect(s).missing_required


def test_no_unwarranted_region_product_or_seed_inference():
    s = Scenario(description="日本九州地震造成半導體關鍵材料中斷30天")
    parsed = EventParserSkill().run(s)
    assert parsed.region is None
    assert parsed.product is None
    assert parsed.seed_nodes == []


def test_parser_does_not_mutate_input():
    s = Scenario(description="假設颱風造成物流中斷3天")
    parsed = EventParserSkill().run(s)
    assert s.event_type == "unknown"
    assert s.duration_days is None
    assert parsed.event_type == "natural_disaster"
    assert parsed.duration_days == 3
