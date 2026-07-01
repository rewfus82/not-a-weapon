"""Item catalog invariants + the reveal-tier mechanic."""

from __future__ import annotations

from combine.items import CATALOG, SLOTS, build_catalog


def test_catalog_ids_unique_and_nonempty():
    cat = build_catalog()
    assert cat, "catalog should not be empty"
    assert len(cat) == len({i.id for i in cat.values()})


def test_every_item_has_a_tier_zero_reading():
    # asleep, the player must see *something* for every item, or it's invisible junk.
    for item in CATALOG.values():
        assert item.visible(0), f"{item.id} has nothing readable at insight 0"


def test_fit_keys_are_real_slots_and_in_range():
    for item in CATALOG.values():
        for slot, weight in item.fit.items():
            assert slot in SLOTS, f"{item.id} has bogus slot {slot!r}"
            assert 0.0 <= weight <= 1.0, f"{item.id}.{slot} out of range: {weight}"


def test_reveal_is_monotonic():
    # waking up never HIDES an association you could already see.
    for item in CATALOG.values():
        for lo in range(0, 3):
            seen_lo = set(item.visible_text(lo))
            seen_hi = set(item.visible_text(lo + 1))
            assert seen_lo <= seen_hi, f"{item.id} lost an association going {lo}->{lo+1}"


def test_hidden_count_teaser_shrinks_as_insight_rises():
    mop = CATALOG["mop"]
    counts = [mop.hidden_count(i) for i in range(0, 4)]
    assert counts == sorted(counts, reverse=True)
    assert counts[0] > 0, "mop should have redacted traits while asleep"


def test_mop_reads_as_junk_asleep_then_reveals_utility():
    mop = CATALOG["mop"]
    asleep = " ".join(mop.visible_text(0)).lower()
    awake = " ".join(mop.visible_text(3)).lower()
    assert "junk" in asleep
    assert "soaks up" not in asleep, "the useful trait must be hidden at first"
    assert "soaks up" in awake, "the useful trait must surface once awake"


def test_handgun_fits_damage_over_utility():
    gun = CATALOG["handgun"]
    assert gun.fit_for("damage") > gun.fit_for("utility")


def test_acceptance_case_items_exist():
    needed = ["bear_trap", "beehive", "fireworks", "dry_ice",
              "salami", "dish_soap", "handgun", "pencil", "mop", "gasoline"]
    for iid in needed:
        assert iid in CATALOG, f"missing acceptance-case item {iid!r}"
