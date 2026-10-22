from html.parser import HTMLParser

from flask_version.app import app


class SelectOptions(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = None
        self.options = {}
        self.in_option = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'select':
            self.active = attrs.get('name')
            self.options[self.active] = []
        if tag == 'option':
            self.in_option = True

    def handle_endtag(self, tag):
        if tag == 'select':
            self.active = None
        if tag == 'option':
            self.in_option = False

    def handle_data(self, data):
        if self.active and self.in_option and data.strip():
            self.options[self.active].append(data.strip())


def test_strategy_and_test_pages_explain_and_separate_execution_context():
    with app.test_client() as client:
        start = client.get('/inicio').get_data(as_text=True)
        review = client.get('/revisao').get_data(as_text=True)
        indicators = client.get('/indicadores').get_data(as_text=True)
    assert 'Selecionar Forex ou B3 não escolhe um ativo' in start
    assert 'name="bridge-symbol"' not in start
    assert 'Ele não define o ativo nem o timeframe base' in review
    assert 'Ativo do teste (símbolo autorizado no Bridge)' in review
    assert 'Timeframe base do teste' in review
    assert 'data-bridge-execution-context' in review
    test_options, slot_options = SelectOptions(), SelectOptions()
    test_options.feed(review)
    slot_options.feed(indicators)
    assert 'Tempo corrente' not in test_options.options['bridge-timeframe']
    assert slot_options.options['indicator-timeframe-1'][0] == 'Tempo corrente'
    assert slot_options.options['indicator-timeframe-1'][1:] == test_options.options['bridge-timeframe']
