"""Server-to-server transport. No MT5 imports and no service token in the browser."""
import json
import os
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class BridgeUnavailable(Exception):
    def __init__(self,message,status=503,code='BRIDGE_UNAVAILABLE'):
        super().__init__(message);self.message,self.status,self.code=message,status,code


class BridgeTransport(Protocol):
    def call(self,method:str,path:str,payload:dict|None=None,raw:bool=False): ...


class HTTPBridgeClient:
    def __init__(self,url,token):
        parts=urlsplit(url)
        if parts.scheme!='http' or parts.hostname not in ('127.0.0.1','localhost') or parts.username or parts.password or parts.query or parts.fragment or parts.path not in ('','/'):
            raise BridgeUnavailable('A versão local exige URL HTTP de loopback configurada no servidor.',code='BRIDGE_CONFIGURATION')
        if not token:raise BridgeUnavailable('Configure GERASET_BRIDGE_TOKEN no servidor Flask.',code='BRIDGE_CONFIGURATION')
        self.url=url.rstrip('/');self.token=token

    @classmethod
    def from_env(cls):
        return cls(os.getenv('GERASET_BRIDGE_URL','http://127.0.0.1:8765'),os.getenv('GERASET_BRIDGE_TOKEN',''))

    def call(self,method,path,payload=None,raw=False):
        body=json.dumps(payload).encode() if payload is not None else None
        request=Request(self.url+'/api/v1'+path,data=body,method=method,headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'})
        try:
            with urlopen(request,timeout=5) as response:
                content=response.read(52*1024*1024+1)
                if len(content)>52*1024*1024:raise BridgeUnavailable('Resposta excede o limite.',502)
                if raw:return content,response.headers.get('Content-Type','application/octet-stream')
                return json.loads(content)
        except HTTPError as exc:
            try:error=json.loads(exc.read(65536)).get('error',{})
            except (ValueError,AttributeError):error={}
            raise BridgeUnavailable(error.get('message','Bridge recusou a solicitação.'),exc.code,error.get('code','BRIDGE_ERROR')) from exc
        except (URLError,TimeoutError,OSError,ValueError) as exc:
            raise BridgeUnavailable('Bridge desligado ou sem resposta. Configuração e exportação de sets continuam disponíveis.') from exc
