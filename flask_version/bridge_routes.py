import hmac
import io
import re
import secrets
from uuid import UUID
from flask import Blueprint, current_app, jsonify, request, send_file, session
if __package__:
    from .bridge_client import HTTPBridgeClient, BridgeUnavailable
else:
    from bridge_client import HTTPBridgeClient, BridgeUnavailable

bridge=Blueprint('bridge',__name__,url_prefix='/bridge')


@bridge.before_request
def csrf():
    if request.method=='POST':
        expected=session.get('bridge_csrf','')
        if not expected or not hmac.compare_digest(request.headers.get('X-GeraSet-CSRF',''),expected):
            return jsonify(error={'code':'CSRF','message':'Atualize a página antes de executar tarefas.'}),403
    if request.content_length and request.content_length>1500000:
        return jsonify(error={'code':'BODY_TOO_LARGE','message':'Solicitação excede o limite.'}),413


@bridge.errorhandler(BridgeUnavailable)
def unavailable(exc):return jsonify(error={'code':exc.code,'message':exc.message}),exc.status


def client():return current_app.config.get('BRIDGE_CLIENT') or HTTPBridgeClient.from_env()


@bridge.get('/session')
def bridge_session():
    if 'bridge_csrf' not in session:session['bridge_csrf']=secrets.token_urlsafe(32)
    return jsonify(data={'csrf':session['bridge_csrf']})


@bridge.get('/status')
def bridge_status():
    transport=client()
    return jsonify(data={'health':transport.call('GET','/health')['data'],
                         'mt5':transport.call('GET','/mt5/status')['data'],
                         'capabilities':transport.call('GET','/mt5/capabilities')['data']})


@bridge.route('/jobs',methods=['GET','POST'])
def jobs():
    if request.method=='GET':return jsonify(client().call('GET','/jobs?limit=30'))
    body=request.get_json(silent=True)
    if not isinstance(body,dict):return jsonify(error={'code':'INVALID_REQUEST','message':'Envie JSON válido.'}),400
    operation=body.pop('operation',None)
    if operation not in ('backtest','optimize','visual'):return jsonify(error={'code':'INVALID_REQUEST','message':'Operação inválida.'}),400
    return jsonify(client().call('POST','/jobs/'+operation,body)),202


@bridge.get('/jobs/<uuid:job_id>')
def job(job_id):return jsonify(client().call('GET',f'/jobs/{job_id}'))


@bridge.get('/jobs/<uuid:job_id>/<part>')
def job_part(job_id,part):
    if part not in ('progress','results','artifacts'):return jsonify(error={'code':'NOT_FOUND','message':'Consulta desconhecida.'}),404
    return jsonify(client().call('GET',f'/jobs/{job_id}/{part}'))


@bridge.post('/jobs/<uuid:job_id>/cancel')
def cancel(job_id):return jsonify(client().call('POST',f'/jobs/{job_id}/cancel'))


@bridge.get('/jobs/<uuid:job_id>/artifacts/<artifact_id>')
def artifact(job_id,artifact_id):
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',artifact_id):return jsonify(error={'code':'NOT_FOUND','message':'Artefato inválido.'}),404
    body,mime=client().call('GET',f'/jobs/{job_id}/artifacts/{artifact_id}',raw=True)
    response=send_file(io.BytesIO(body),mimetype=mime,as_attachment=True,download_name=artifact_id)
    response.headers['X-Content-Type-Options']='nosniff'
    return response


@bridge.get('/jobs/<uuid:job_id>/preview/<artifact_id>')
def preview(job_id,artifact_id):
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',artifact_id):
        return jsonify(error={'code':'NOT_FOUND','message':'Artefato inválido.'}),404
    extension=artifact_id.rsplit('.',1)[-1].lower()
    types={'htm':'text/html','html':'text/html','png':'image/png','gif':'image/gif'}
    if extension not in types:
        return jsonify(error={'code':'PREVIEW_UNAVAILABLE','message':'Visualização indisponível para este arquivo.'}),415
    body,_=client().call('GET',f'/jobs/{job_id}/artifacts/{artifact_id}',raw=True)
    if extension in ('htm','html'):
        if body.startswith((b'\xff\xfe',b'\xfe\xff')):body=body.decode('utf-16').encode('utf-8')
        else:
            try:body=body.decode('utf-8-sig').encode('utf-8')
            except UnicodeError:body=body.decode('cp1252').encode('utf-8')
    response=send_file(io.BytesIO(body),mimetype=types[extension],as_attachment=False,download_name=artifact_id)
    if extension in ('htm','html'):response.headers['Content-Type']='text/html; charset=utf-8'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Content-Security-Policy']="sandbox; default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
    return response
