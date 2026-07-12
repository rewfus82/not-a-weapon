import pytest

from resolver.contract import Tier
from resolver.items import DEFAULT_BUILDS
from resolver.router import route
from resolver import fallback, harness


def test_tier_schedule_repeats_only_the_high_tiers():
    schedule = harness.tier_schedule(repeats=3)
    assert schedule.count(Tier.DUD) == 1
    assert schedule.count(Tier.COMMON) == 1
    assert schedule.count(Tier.UNCOMMON) == 1
    assert schedule.count(Tier.RARE) == 3
    assert schedule.count(Tier.EPIC) == 3
    assert schedule.count(Tier.LEGENDARY) == 3


def test_run_produces_one_result_per_scheduled_tier_per_build():
    results = harness.run(fallback.resolve, build_keys=["broom_bat"], repeats=3)
    # 3 singles (DUD/COMMON/UNCOMMON) + 3*3 high-tier = 12
    assert len(results) == 12
    assert all(r.build_key == "broom_bat" for r in results)
    # high-tier instances are labelled 1..3
    leg = [r for r in results if r.resolved.tier is Tier.LEGENDARY]
    assert sorted(r.run_index for r in leg) == [1, 2, 3]
    assert all(r.run_total == 3 for r in leg)


def test_main_runs_the_fallback_path_and_prints(capsys):
    exit_code = harness.main(["--fallback", "--build", "broom_bat", "--repeats", "2"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "BUILD: broom_bat" in out
    assert "deterministic fallback" in out.lower()
    assert "LEGENDARY" in out


def test_build_model_list_escalates_final_attempt():
    assert harness.build_model_list("claude-sonnet-5", 3, "claude-opus-4-8") == [
        "claude-sonnet-5", "claude-sonnet-5", "claude-opus-4-8",
    ]


def test_build_model_list_without_escalation():
    assert harness.build_model_list("claude-sonnet-5", 3, None) == ["claude-sonnet-5"] * 3


def test_build_model_list_single_attempt_has_no_room_to_escalate():
    assert harness.build_model_list("claude-sonnet-5", 1, "claude-opus-4-8") == ["claude-sonnet-5"]


def test_run_falls_back_on_resolver_refusal():
    def flaky(build, tier):
        if tier is Tier.LEGENDARY:
            raise RuntimeError("no GadgetDraft (stop_reason='refusal')")
        return fallback.resolve(build, tier)

    results = harness.run(flaky, build_keys=["broom_bat"], repeats=3)
    leg = [r for r in results if r.resolved.tier is Tier.LEGENDARY]
    assert len(leg) == 3
    assert all(r.source == "fallback" for r in leg)
    assert all(r.resolved.draft.stages for r in leg)          # valid, non-empty instance
    assert all("RuntimeError" in (r.reason or "") for r in leg)
    non_leg = [r for r in results if r.resolved.tier is not Tier.LEGENDARY]
    assert non_leg and all(r.source == "llm" for r in non_leg)


def test_run_survives_total_refusal_with_all_fallbacks():
    def always_refuse(build, tier):
        raise RuntimeError("no GadgetDraft")

    results = harness.run(always_refuse, build_keys=["broom_bat"], repeats=3)
    assert len(results) == 12
    assert all(r.source == "fallback" for r in results)


def test_fallback_resolve_failure_propagates(monkeypatch):
    # Only the live call is wrapped; a bug in the deterministic fallback must
    # surface, not be silently swallowed into another fallback attempt.
    def always_refuse(build, tier):
        raise RuntimeError("refused")

    def broken_fallback(build, tier):
        raise ValueError("deterministic bug")

    monkeypatch.setattr(harness, "fallback_resolve", broken_fallback)
    with pytest.raises(ValueError, match="deterministic bug"):
        harness.run(always_refuse, build_keys=["broom_bat"], repeats=1)


def test_main_prints_fallback_summary(capsys):
    exit_code = harness.main(["--fallback", "--build", "broom_bat", "--repeats", "2"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "fallbacks:" in out
    assert "broom_bat 0/" in out   # the deterministic resolver never "refuses"


def test_routing_summary_reports_the_deterministic_llm_split():
    results = harness.run(fallback.resolve, build_keys=["broom_bat"], repeats=3)
    build = DEFAULT_BUILDS["broom_bat"]
    expected_d = sum(1 for r in results if route(build, r.resolved.tier) == "deterministic")
    expected_l = len(results) - expected_d

    summary = harness.routing_summary(results)

    assert summary == f"routing: deterministic {expected_d} / llm {expected_l}"


def test_main_prints_the_routing_split(capsys):
    exit_code = harness.main(["--fallback", "--build", "broom_bat", "--repeats", "2"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "routing: deterministic " in out
    assert " / llm " in out
