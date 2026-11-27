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


def test_main_bearing_conflict_prefers_assembly_section():
    found = conflicts_for({("yamz-236_rk_2014", 41)})
    assert len(found) == 1 and "248" in found[0]["rule"] and "{yamz-236_rk_2014#248}" in found[0]["refs"]
    by_topic = conflicts_for(set(), "момент затяжки болтов крышек коренных подшипников", {"yamz-236_rk_2014", "yamz-236_re_2010"})
    assert [c["topic"] for c in by_topic] == [found[0]["topic"]]


def test_oil_pressure_conflict_only_from_outlier_table():
    assert conflicts_for({("yamz-236_re_2010", 19)}) == []          # обычный ответ про давление масла без лишнего
    assert conflicts_for(set(), "какое давление масла на холостом", {"yamz-236_rk_2014", "yamz-236_re_2010"}) == []
    found = conflicts_for({("yamz-236_rk_2014", 12)})
    assert len(found) == 1 and "400–700" in found[0]["rule"]
    assert conflicts_for(set(), "в таблице 400-730 кПа, это норма?", {"yamz-236_rk_2014", "yamz-236_re_2010"})


def test_no_referral_to_specialist():
    from app import agent, conflicts
    assert "специалист" not in agent.SYSTEM.replace("Не отсылай «к специалисту»", "").replace("к «специалисту» не отсылай", "").replace("механик сам специалист", "")
    assert all("специалист" not in c.rule for c in conflicts.CONFLICTS)
