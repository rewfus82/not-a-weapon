from resolver.contract import Tier
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
    results = harness.run(fallback.resolve, build_keys=["broom+oil"], repeats=3)
    # 3 singles (DUD/COMMON/UNCOMMON) + 3*3 high-tier = 12
    assert len(results) == 12
    assert all(r.build_key == "broom+oil" for r in results)
    # high-tier instances are labelled 1..3
    leg = [r for r in results if r.resolved.tier is Tier.LEGENDARY]
    assert sorted(r.run_index for r in leg) == [1, 2, 3]
    assert all(r.run_total == 3 for r in leg)


def test_main_runs_the_fallback_path_and_prints(capsys):
    exit_code = harness.main(["--fallback", "--build", "broom+oil", "--repeats", "2"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "BUILD: broom+oil" in out
    assert "deterministic fallback" in out.lower()
    assert "LEGENDARY" in out
