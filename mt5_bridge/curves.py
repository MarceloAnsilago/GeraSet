"""Read bounded pages of completed, genuine optimization curves."""
import json
import math
from .errors import BridgeError


def read_curves(path, offset=0, limit=200):
    curves=[]
    if not path.is_file():return {'curves':curves,'offset':0,'available':False,'more':False}
    with path.open('rb') as stream:
        incomplete=False
        if offset>path.stat().st_size:raise BridgeError('INVALID_OFFSET','Posição de leitura inválida.')
        if offset:
            stream.seek(offset-1)
            if stream.read(1)!=b'\n':raise BridgeError('INVALID_OFFSET','Use a posição retornada pela leitura anterior.')
        stream.seek(offset)
        for _ in range(limit):
            start=stream.tell();line=stream.readline(16385)
            if not line:break
            # The terminal may still be writing the last line; retry next poll.
            if not line.endswith(b'\n'):
                if len(line)>16384:raise BridgeError('INVALID_CURVES','Curva excede o limite de tamanho.')
                stream.seek(start);incomplete=True;break
            if len(line)>16384:raise BridgeError('INVALID_CURVES','Curva excede o limite de tamanho.')
            try:
                curve=json.loads(line)
                points=curve['points']
                valid=(isinstance(curve['pass'],str) and curve['pass'].isdigit() and 2<=len(points)<=128
                       and all(isinstance(p,list) and len(p)==2 and all(type(v) in (int,float) and math.isfinite(v) for v in p) for p in points)
                       and all(a[0]<=b[0] for a,b in zip(points,points[1:])))
                if not valid:raise ValueError()
            except (ValueError,KeyError,TypeError) as exc:
                raise BridgeError('INVALID_CURVES','Arquivo de curvas inválido.') from exc
            curves.append(curve)
        offset=stream.tell()
    return {'curves':curves,'offset':offset,'available':True,'more':not incomplete and offset<path.stat().st_size}
