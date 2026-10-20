from pathlib import Path
import re


class LogMonitor:
    """Incremental bounded reads. Never scans full journals on every tick."""
    def __init__(self,data_dir):
        self.roots=[data_dir/'logs',data_dir/'Tester/logs']
        self.offsets={str(p):p.stat().st_size for p in self.paths()}
        self.passes=set();self.messages=[];self.error=None

    def paths(self):
        result=[]
        for root in self.roots:
            if root.exists():result.extend(sorted(root.glob('*.log'),key=lambda p:p.stat().st_mtime)[-2:])
        return result

    def poll(self):
        fresh=[]
        for path in self.paths():
            key=str(path);start=self.offsets.get(key,0)
            size=path.stat().st_size
            if size<start:start=0
            with path.open('rb') as f:
                f.seek(start);raw=f.read(65536)
            self.offsets[key]=start+len(raw)
            if not raw:continue
            text=raw.decode('utf-16-le',errors='replace')
            for line in text.splitlines():
                if re.search(r'password|token|authorization|login=',line,re.I):continue
                message=line.strip()[-700:]
                if not message:continue
                fresh.append(message)
                match=re.search(r'pass\s+(\d+)\s+(?:tested|returned|finished)',message,re.I)
                if match:self.passes.add(int(match[1]))
                for pattern,code in [(r'(?:cannot|failed to) load.*\.ex5','EA_LOAD_FAILED'),
                                     (r'symbol.*(?:not found|unknown)','SYMBOL_UNAVAILABLE'),
                                     (r'no history data|not enough histor|no data for testing','HISTORY_UNAVAILABLE'),
                                     (r'account is not specified|no account specified','ACCOUNT_REQUIRED'),
                                     (r'initialization.*failed|test failed','TEST_FAILED')]:
                    if re.search(pattern,message,re.I):self.error={'code':code,'message':message}
        self.messages=(self.messages+fresh)[-30:]
        return self.messages
