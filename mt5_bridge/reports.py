from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
import re
import unicodedata
import xml.etree.ElementTree as ET
from .errors import BridgeError


def normalized(value):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', value).encode('ascii','ignore').decode().lower())


ALIASES = {
    'net_profit': ['Total Net Profit','Lucro Liquido Total','Lucro Liquido'],
    'gross_profit': ['Gross Profit','Lucro Bruto'],
    'gross_loss': ['Gross Loss','Perda Bruta','Prejuizo Bruto'],
    'profit_factor': ['Profit Factor','Fator de Lucro'],
    'expected_payoff': ['Expected Payoff','Retorno Esperado','Payoff Esperado'],
    'sharpe_ratio': ['Sharpe Ratio','Indice de Sharpe'],
    'recovery_factor': ['Recovery Factor','Fator de Recuperacao'],
    'drawdown_absolute': ['Balance Drawdown Absolute','Rebaixamento Absoluto do Saldo'],
    'drawdown_maximal': ['Balance Drawdown Maximal','Rebaixamento Maximo do Saldo'],
    'drawdown_relative': ['Balance Drawdown Relative','Rebaixamento Relativo do Saldo'],
    'total_trades': ['Total Trades','Total de Negociacoes'],
    'profit_trades': ['Profit Trades (% of total)','Negociacoes com Lucro (% do total)'],
}
LABELS = {normalized(label):key for key,labels in ALIASES.items() for label in labels}

PASS_LABELS = dict(LABELS, profit='net_profit', lucro='net_profit',
                   trades='total_trades', negociacoes='total_trades',
                   drawdownpercent='drawdown_relative',
                   equityddpercent='equity_drawdown_percent')


def pass_metrics(values):
    metrics={key:None for key in (*ALIASES,'equity_drawdown_percent')}
    for label,raw in values.items():
        key=PASS_LABELS.get(normalized(label))
        if key:metrics[key]={'value':decimal_text(raw),'raw':raw}
    return metrics


def decimal_text(raw):
    match = re.match(r'\s*([-+]?\d[\d\s\u00a0.,]*)',raw)
    if not match:
        return None
    value=re.sub(r'[\s\u00a0]','',match[1]).rstrip('.,')
    if ',' in value and '.' in value:
        value=value.replace(',','') if value.rfind('.')>value.rfind(',') else value.replace('.','').replace(',','.')
    elif ',' in value:
        value=value.replace(',','.')
    try:
        result=Decimal(value)
        return str(result) if result.is_finite() else None
    except InvalidOperation:
        return None


class TableReader(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=[]; self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        if tag in ('td','th'):self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()));self.cell=None
        if tag=='tr' and self.row:self.rows.append(self.row)


def read_report(path: Path):
    raw=path.read_bytes()
    if len(raw)>50*1024*1024:
        raise BridgeError('REPORT_TOO_LARGE','Relatório excede 50 MB.')
    if raw.startswith((b'\xff\xfe',b'\xfe\xff')):
        text=raw.decode('utf-16')
    else:
        try:text=raw.decode('utf-8-sig')
        except UnicodeError:text=raw.decode('cp1252')
    if path.suffix.lower()=='.xml':
        return read_optimization(text)
    if '</html>' not in text.lower():
        raise BridgeError('INCOMPLETE_REPORT','Relatório HTML incompleto.')
    parser=TableReader();parser.feed(text)
    metrics={key:None for key in ALIASES}
    inputs=[]
    for row in parser.rows:
        for i,label in enumerate(row[:-1]):
            key=LABELS.get(normalized(label))
            if key:
                raw_value=row[i+1]
                metrics[key]={'value':decimal_text(raw_value),'raw':raw_value}
            if normalized(label) in ('inputs','parametrosdeentrada','entradas'):
                inputs.append(row[i+1:])
    if metrics['net_profit'] is None and metrics['total_trades'] is None:
        raise BridgeError('UNRECOGNIZED_REPORT','Relatório sem métricas reconhecidas; original preservado.')
    win_rate=None
    if metrics['profit_trades']:
        match=re.search(r'\(([-\d.,]+)\s*%\)',metrics['profit_trades']['raw'])
        if match:win_rate=decimal_text(match[1])
    return {'kind':'backtest','metrics':metrics,'win_rate_percent':win_rate,'reported_inputs':inputs,'precision':'decimal strings','partial':False}


def read_optimization(text):
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise BridgeError('INVALID_REPORT','Entidades XML não permitidas.')
    try:root=ET.fromstring(text)
    except ET.ParseError as exc:raise BridgeError('INCOMPLETE_REPORT','Relatório XML incompleto.') from exc
    worksheets=[]
    for sheet in root.iter():
        if sheet.tag.split('}')[-1] not in ('Worksheet','Table'):continue
        if sheet.tag.split('}')[-1]=='Worksheet':continue
        rows=[]
        for row in sheet:
            if row.tag.split('}')[-1]!='Row':continue
            cells=[]
            for cell in row:
                if cell.tag.split('}')[-1]!='Cell':continue
                index=next((int(v) for k,v in cell.attrib.items() if k.split('}')[-1]=='Index'),len(cells)+1)
                if index<1 or index>512 or len(cells)>=512:
                    raise BridgeError('INVALID_REPORT','Limite de colunas XML excedido.')
                cells.extend(['']*max(0,index-1-len(cells)))
                cells.append(''.join(cell.itertext()).strip())
            if cells:rows.append(cells)
        header_index=next((i for i,row in enumerate(rows) if any(normalized(c) in ('pass','passe','passagem') for c in row)),None)
        if header_index is not None:
            headers=rows[header_index]
            passes=[dict(zip(headers,row)) for row in rows[header_index+1:] if row and row[0].strip()]
            worksheets.append({'columns':headers,'passes':passes,
                               'normalized_passes':[{'values':p,'metrics':pass_metrics(p)} for p in passes]})
    if not worksheets or not any(sheet['passes'] for sheet in worksheets):
        raise BridgeError('EMPTY_OPTIMIZATION','Nenhum passe reconhecido no XML; original preservado.')
    return {'kind':'optimize','worksheets':worksheets,'pass_count':sum(len(s['passes']) for s in worksheets),'precision':'original strings','partial':False}
