from resolver.contract import EffectKind
from resolver import interactions as I


def test_taxonomy_is_the_24_locked_tags():
    assert len(I.TAXONOMY) == 24
    assert "container" in I.TAXONOMY and "scatter" in I.TAXONOMY
    # dropped tags must be absent
    for gone in ("buoyant", "decoy", "swarm"):
        assert gone not in I.TAXONOMY


def test_all_table_tags_are_in_taxonomy():
    used = set(I.SINGLE_TAG_EFFECTS)
    for pair in I.PAIR_EFFECTS:
        used |= set(pair)
    assert used <= I.TAXONOMY


def test_known_pair_flammable_ignition_burns():
    assert I.PAIR_EFFECTS[frozenset({"flammable", "ignition"})] is EffectKind.BURN


def test_electrical_liquid_chains():
    assert I.PAIR_EFFECTS[frozenset({"electrical", "liquid"})] is EffectKind.CHAIN


def test_tags_interact_on_shared_tag():
    assert I.tags_interact(frozenset({"heavy", "blunt"}), frozenset({"blunt"})) is True


def test_tags_interact_on_pair_rule():
    assert I.tags_interact(frozenset({"flammable"}), frozenset({"ignition"})) is True


def test_tags_do_not_interact_when_unrelated():
    assert I.tags_interact(frozenset({"sharp"}), frozenset({"restorative"})) is False


def test_effects_for_prefers_pair_then_singles():
    effs = I.effects_for(frozenset({"flammable", "ignition", "sharp"}))
    assert EffectKind.BURN in effs      # from the pair
    assert EffectKind.PIERCE in effs    # sharp single, uncovered by the pair


def test_effects_for_deduplicates_across_overlapping_pairs():
    effs = I.effects_for(frozenset({"flammable", "ignition", "electrical"}))
    assert effs.count(EffectKind.BURN) == 1
