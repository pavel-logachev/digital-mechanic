"""Подтвержденные противоречия руководств доходят до агента вместе со ссылками обеих сторон."""
from app.conflicts import CONFLICTS, conflicts_for


def test_conflict_found_by_any_side():
    for side in CONFLICTS[0].pages:
        found = conflicts_for({side})
        assert len(found) == 1 and len(found[0]["refs"]) == 3 and "холодном" in found[0]["rule"]


def test_no_conflict_for_unrelated_page():
    assert conflicts_for({("yamz-236_re_2010", 19)}) == []


def test_conflict_found_by_topic_only_for_its_engine():
    yamz = {"yamz-236_re_2010", "yamz-236_rk_2014"}
    assert conflicts_for(set(), "регулировка тепловых зазоров клапанов на холодном двигателе", yamz)
    assert not conflicts_for(set(), "регулировка тепловых зазоров клапанов", {"zmz-5234_rk_2025"})
    assert not conflicts_for(set(), "давление масла", yamz)
