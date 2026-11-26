"""Подтвержденные противоречия руководств доходят до агента вместе со ссылками обеих сторон."""
from app.conflicts import CONFLICTS, conflicts_for


def test_conflict_found_by_any_side():
    for side in CONFLICTS[0].pages:
        found = conflicts_for({side})
        assert len(found) == 1 and len(found[0]["refs"]) == 3 and "холодном" in found[0]["rule"]


def test_no_conflict_for_unrelated_page():
    assert conflicts_for({("yamz-236_re_2010", 19)}) == []
