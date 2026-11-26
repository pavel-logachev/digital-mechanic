from eval.quality_eval import classify_failure, validate_judgment, summarize


def test_wrong_answer_without_gold_in_tools_is_retrieval_failure():
    assert classify_failure({'expected_pages': ['manual#1'], 'retrieved_pages': ['manual#2']},
                            {'verdict': 'wrong'}) == 'search'


def test_correct_alternative_citation_is_not_search_failure():
    assert classify_failure({'expected_pages': ['manual#1'], 'retrieved_pages': ['manual#2']},
                            {'verdict': 'correct', 'citation_supported': True}) is None


def test_absence_success_is_not_correct_on_answerable_questions():
    rows = [{'answerable': False, 'judgment': {'verdict': 'refused_ok'}, 'seconds': 1},
            {'answerable': True, 'judgment': {'verdict': 'partially'}, 'seconds': 3}]
    out = summarize(rows)
    assert out['correct_pct'] == 0
    assert out['correct_plus_partially_pct'] == 100
    assert out['strict_task_success_pct'] == 50
    assert out['refused_ok'] == 1


def test_judge_does_not_accept_string_as_boolean():
    import pytest
    with pytest.raises(ValueError):
        validate_judgment({'verdict': 'correct', 'citation_supported': 'false', 'reason': 'test'})
