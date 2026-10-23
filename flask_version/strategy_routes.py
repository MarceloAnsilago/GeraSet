"""HTTP adapters for offline domain services. No MT5/Bridge transport calls."""
import base64
import hmac
import io
import secrets

from flask import Blueprint, jsonify, request, send_file, session

from geraset_domain.schema import strategy_schema
from geraset_domain.services import (Issue, StrategyServiceError, compare_legacy_set,
                                     configure_strategy, export_preserving_legacy, export_strategy)


strategies = Blueprint('strategies', __name__, url_prefix='/strategies')


@strategies.before_request
def protect_strategy_requests():
    if request.method == 'POST':
        token = session.get('strategy_csrf', '')
        if not token or not hmac.compare_digest(request.headers.get('X-GeraSet-Strategy-CSRF', ''), token):
            return jsonify(error={'category': 'security', 'code': 'CSRF', 'message': 'Atualize a página antes de continuar.'}), 403


@strategies.after_request
def private_response(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


@strategies.errorhandler(StrategyServiceError)
def invalid_configuration(exc):
    from dataclasses import asdict
    return jsonify(data={'valid': False, 'errors': [asdict(e) for e in exc.errors], 'financial_state': 'not_tested'}), 422


def decode_set(value):
    try:
        if not isinstance(value, str) or len(value) > 1400000:
            raise ValueError()
        return base64.b64decode(value, validate=True)
    except ValueError as exc:
        raise StrategyServiceError((Issue('structural', 'INVALID_SET_ENCODING', 'Envie um .set em base64 válido de até 1 MB.'),)) from exc


def body(allowed):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.keys() - allowed:
        raise StrategyServiceError((Issue('structural', 'INVALID_REQUEST', 'Envie JSON com os campos suportados.'),))
    return data


@strategies.get('/session')
def strategy_session():
    if 'strategy_csrf' not in session:
        session['strategy_csrf'] = secrets.token_urlsafe(32)
    return jsonify(data={'csrf': session['strategy_csrf']})


@strategies.get('/schema')
def schema():
    return jsonify(strategy_schema())


@strategies.post('/validate')
def validate():
    result = configure_strategy(request.get_json(silent=True))
    return jsonify(data=result.as_dict()), 200 if result.valid else 422


@strategies.post('/export')
def export():
    data = body({'strategy', 'options', 'legacy_set_base64'})
    if 'legacy_set_base64' in data:
        artifact = export_preserving_legacy(data.get('strategy'), decode_set(data['legacy_set_base64']), data.get('options'))
    else:
        artifact = export_strategy(data.get('strategy'), data.get('options'))
    response = send_file(io.BytesIO(artifact.contents), mimetype='application/octet-stream',
                         as_attachment=True, download_name=artifact.filename)
    response.headers['X-GeraSet-SHA256'] = artifact.sha256
    response.headers['X-GeraSet-Financial-State'] = 'not_tested'
    response.headers['X-GeraSet-Warnings'] = ','.join(w.code for w in artifact.warnings)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@strategies.post('/compare')
def compare():
    data = body({'set_base64'})
    result, artifact = compare_legacy_set(decode_set(data.get('set_base64')))
    return jsonify(data={**result, 'python_set_base64': base64.b64encode(artifact.contents).decode(),
                         'python_filename': artifact.filename})
