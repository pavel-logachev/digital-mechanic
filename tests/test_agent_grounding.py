from app import agent, verify


def test_search_exposes_full_manual_page_beyond_old_2200_limit(monkeypatch):
    mid = 'yamz-236_re_2010'
    text = 'Шапка ' + 'заполнитель ' * 195 + 'Норматив испытания 37 мм.'
    class Searcher:
        rerank_stats = {}
        def search(self, *_args, **_kwargs):
            return [{'manual_id': mid, 'page': 19, 'text': text}]
    monkeypatch.setattr(agent, 'searcher', Searcher)
    a = object.__new__(agent.Agent)
    a.engine, a.allowed, a.c = 'ЯМЗ-236М2', {mid}, agent.Conversation('test', 'test', None)
    response = a.t_search_manual(['норматив испытания'])
    assert '37 мм' in response['pages'][0]['text']


def test_verifier_does_not_accept_number_that_only_occurs_on_unrelated_read_page():
    mid = 'yamz-236_re_2010'
    pages = {(mid, 1): 'Указан уровень масла', (mid, 2): 'Посторонний размер 55 мм'}
    result = verify.check(f'Номинальный зазор 55 мм {{{mid}#1}}', {mid}, set(pages),
                          lambda m, p: pages[m, p], set())
    assert result.problems


def test_verifier_recognizes_decimal_range_in_ocr_text():
    mid = 'yamz-236_re_2010'
    pages = {(mid, 1): 'Номинальный зазор 0,35…0,40 мм'}
    result = verify.check(f'Номинальный зазор 0.35–0.4 мм {{{mid}#1}}', {mid}, set(pages),
                          lambda m, p: pages[m, p], set())
    assert not result.problems


def test_verifier_uses_same_tokenization_for_grouped_norms_and_part_ids():
    mid = 'yamz-536_re_2016'
    pages = {(mid, 114): 'Фильтр W 11 102; интервал 10 000 км.'}
    checked = verify.check(f'Фильтр W 11 102, интервал 10\u202f000 км {{{mid}#114}}.', {mid}, set(pages),
                           lambda m, p: pages[m, p], set())
    assert not checked.problems


def test_displayed_quote_prefers_exact_source_excerpt_over_page_heading():
    mid = 'yamz-536_re_2016'
    warning = 'Запрещается отсоединять топливопроводы при работающем двигателе'
    source = ('Другие правила безопасности ремонта и технического осмотра, ' * 25
              + warning + ', учтите это в первую очередь; ' + 'текст другой операции ' * 19)
    answer = f'В книге прямо указано: «{warning}» {{{mid}#152}}.'
    assert warning in verify.quote_for(answer, mid, 152, source)


def test_quote_does_not_start_with_broken_word():
    from app.verify import quote_for
    page = "4. Замените фильтр.\nПри засорении эле-\nмента фильтра грубой очистки заменить его\nи промыть корпус."
    q = quote_for("Засорение фильтра грубой очистки – заменить элемент {m#5}.", "m", 5, page)
    assert not q.startswith("мента") and "элемента фильтра грубой очистки" in q
