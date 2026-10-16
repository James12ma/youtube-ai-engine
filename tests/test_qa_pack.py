from scripts.qa_pack import word_error_rate, _norm_words


def test_wer_ignores_case_accents_and_punctuation():
    assert word_error_rate('¿Qué es el ITIN? Información.', 'que es el itin informacion') == 0.0
    assert word_error_rate('uno dos tres cuatro', 'uno tres cuatro') == 0.25
    assert word_error_rate('', 'algo') == 1.0
    assert _norm_words('Año, niño') == ['ano', 'nino']
