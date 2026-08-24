from recllm_fairness.data.catalog import Item
from recllm_fairness.personas.population_v2 import (
    PopulationProfile,
    audit_candidate_pools,
    audit_population,
    build_population_candidate_pools,
)


def test_population_audit_detects_leakage_and_insufficient_opportunity() -> None:
    profile = PopulationProfile("p1", "movie", "likes films", ["a"], ["a"], "low/low/low")
    result = audit_population([profile], expected_count=1, minimum_relevant=1)
    assert result["passed"] is False
    assert result["leakage_profile_ids"] == ["p1"]


def test_population_audit_passes_valid_profiles() -> None:
    profile = PopulationProfile("p1", "music", "likes artists", ["a"], ["b", "c"], "low/mid/high")
    result = audit_population([profile], expected_count=1, minimum_relevant=2)
    assert result["passed"] is True


def test_population_candidate_pools_pass_exact_audit() -> None:
    catalog = [
        Item(
            item_id=str(index),
            domain="movie",
            title=f"Film {index}",
            genres=["Drama"],
            provider_or_studio=None,
            popularity_rank=index,
            popularity_tier="head" if index <= 80 else "mid" if index <= 160 else "tail",
            interaction_count=241 - index,
            release_year=2000,
        )
        for index in range(1, 241)
    ]
    profile = PopulationProfile(
        "p1",
        "movie",
        "likes films",
        ["201"],
        [str(index) for index in range(1, 31)],
        "low/mid/high",
    )
    pools = build_population_candidate_pools([profile], catalog)
    result = audit_candidate_pools([profile], pools, catalog)
    assert result["passed"] is True
    pool = pools["p1"]
    assert len(pool.item_ids) == 120
