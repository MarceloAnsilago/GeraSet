from html.parser import HTMLParser

from flask_version.app import app


class FormControls(HTMLParser):
    def __init__(self):
        super().__init__()
        self.names = []
        self.management = []
        self.summaries = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('input', 'select') and 'name' in attrs:
            self.names.append(attrs['name'])
        if 'data-management' in attrs:
            self.management.append(attrs['data-management'])
        if 'data-management-summary' in attrs:
            self.summaries.append(attrs['data-management-summary'])


def test_management_page_renders_all_standard_fields_with_stable_unique_names():
    with app.test_client() as client:
        response = client.get('/gestao')
    assert response.status_code == 200
    form = FormControls()
    form.feed(response.get_data(as_text=True))
    assert form.management == ['breakeven', 'trailing', 'moving-stop']
    assert form.summaries == form.management
    for key in ('trailing', 'moving-stop'):
        for field in ('mode', 'trigger', 'distance', 'step'):
            assert form.names.count(f'{key}-{field}') == 1
        for field in ('activate', 'distance', 'step'):
            for bound in ('start', 'step', 'end'):
                assert form.names.count(f'{key}-{field}-{bound}') == 1
