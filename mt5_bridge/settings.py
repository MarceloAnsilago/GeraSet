from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    token: str = field(repr=False)
    terminal: Path
    data_dir: Path
    expert: Path
    work_dir: Path
    symbols: tuple[str, ...] = ('EURUSD',)
    currencies: tuple[str, ...] = ('USD', 'BRL', 'EUR')
    portable: bool = True
    server: str = ''
    login: int | None = None
    poll_seconds: float = 2
    timeout_seconds: float = 1800
    max_queue: int = 10
    max_passes: int = 10000
    max_set_bytes: int = 1024 * 1024

    def __post_init__(self):
        if len(self.token) < 32 or self.token.startswith('replace-'):
            raise ValueError('Configure BRIDGE_TOKEN com pelo menos 32 caracteres aleatórios.')
        for name in ('terminal', 'data_dir', 'expert', 'work_dir'):
            object.__setattr__(self, name, Path(getattr(self, name)).resolve())
        if any(c in self.server for c in '\r\n[]') or self.poll_seconds < 0.1:
            raise ValueError('Configuração do servidor inválida.')
        if self.max_queue < 1 or self.max_passes < 1 or self.timeout_seconds <= 0:
            raise ValueError('Limites do bridge inválidos.')

    @classmethod
    def from_env(cls):
        terminal = Path(os.getenv('MT5_TERMINAL_PATH', 'C:/Program Files/MetaTrader 5/terminal64.exe'))
        data = Path(os.getenv('MT5_DATA_DIR', str(terminal.parent)))
        return cls(token=os.getenv('BRIDGE_TOKEN', ''), terminal=terminal, data_dir=data,
                   expert=Path(os.getenv('MT5_EA_PATH', str(data / 'MQL5/Experts/Uni/UniEA.ex5'))),
                   work_dir=Path(os.getenv('BRIDGE_DATA_DIR', str(Path(__file__).parent / 'data'))),
                   portable=os.getenv('MT5_PORTABLE', 'true').lower() == 'true',
                   symbols=tuple(x.strip() for x in os.getenv('MT5_ALLOWED_SYMBOLS', 'EURUSD').split(',') if x.strip()),
                   currencies=tuple(x.strip() for x in os.getenv('MT5_ALLOWED_CURRENCIES', 'USD,BRL,EUR').split(',') if x.strip()),
                   server=os.getenv('MT5_SERVER', ''), login=int(os.environ['MT5_LOGIN']) if os.getenv('MT5_LOGIN') else None,
                   poll_seconds=float(os.getenv('BRIDGE_POLL_SECONDS', '2')),
                   timeout_seconds=float(os.getenv('BRIDGE_TIMEOUT_SECONDS', '1800')),
                   max_queue=int(os.getenv('BRIDGE_MAX_QUEUE', '10')),
                   max_passes=int(os.getenv('BRIDGE_MAX_PASSES', '10000')))
