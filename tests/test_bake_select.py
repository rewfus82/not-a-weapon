from resolver.bake.schema import combo_id
from resolver.bake.select import (
    PINNED_BUILDS, chassis_eligible, load_selection, select_combos, write_selection,
)
from resolver.harness import PROBE_BUILDS
from resolver.items import CATALOG

N, SEED = 120, 1


def _ids(builds):
    return [combo_id(b) for b in builds]


def test_selection_is_deterministic_for_a_seed():
    assert _ids(select_combos(N, SEED)) == _ids(select_combos(N, SEED))
    assert _ids(select_combos(N, SEED)) != _ids(select_combos(N, SEED + 1))


def test_selection_size_and_uniqueness():
    ids = _ids(select_combos(N, SEED))
    assert len(ids) == N == len(set(ids))


def test_all_pinned_builds_are_selected():
    assert set(PROBE_BUILDS) <= set(PINNED_BUILDS)
    assert "pinned_extinguisher" in PINNED_BUILDS
    selected = set(_ids(select_combos(N, SEED)))
    assert {combo_id(b) for b in PINNED_BUILDS.values()} <= selected


def test_every_catalog_item_is_covered():
    covered = set()
    for build in select_combos(N, SEED):
        covered |= {item.name for _, item in build.slots() if item is not None}
    assert covered == set(CATALOG)


def test_every_delivery_slot_is_chassis_eligible():
    for build in select_combos(N, SEED):
        assert chassis_eligible(build.delivery_item)
        build.delivery  # must not raise


def test_shape_strata_are_roughly_40_40_20():
    builds = select_combos(300, SEED)
    shapes = [sum(1 for _, i in b.slots() if i is not None) for b in builds]
    assert abs(shapes.count(2) - 120) <= 45
    assert abs(shapes.count(3) - 120) <= 45
    assert abs(shapes.count(4) - 60) <= 45


def test_selection_round_trips_through_json(tmp_path):
    builds = select_combos(N, SEED)
    path = tmp_path / "combos.json"
    write_selection(builds, path, SEED)
    loaded = load_selection(path)
    assert list(loaded) == _ids(builds)
    assert all(combo_id(b) == cid for cid, b in loaded.items())
