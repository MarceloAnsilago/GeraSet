from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class JobState(str, Enum):
    queued = 'queued'
    preparing = 'preparing'
    running = 'running'
    collecting_results = 'collecting_results'
    completed = 'completed'
    failed = 'failed'
    cancelled = 'cancelled'


TERMINAL_STATES = {'completed', 'failed', 'cancelled'}


class JobRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    setup_id: str = Field(min_length=1, max_length=80, pattern=r'^[\w .-]+$')
    set_name: str = Field(min_length=5, max_length=100, pattern=r'^[\w .-]+\.set$')
    set_base64: str = Field(min_length=4, max_length=1400000)
    installation_id: Literal['default'] = 'default'
    symbol: str = Field(min_length=1, max_length=40, pattern=r'^[A-Za-z0-9_.@#$-]+$')
    timeframe: Literal['M1','M2','M3','M4','M5','M6','M10','M12','M15','M20','M30','H1','H2','H3','H4','H6','H8','H12','D1','W1','MN1'] = 'M5'
    date_from: date
    date_to: date
    tick_model: Literal[0,1,2,4] = 1
    deposit: Decimal = Field(default=Decimal('10000'), gt=0, le=1000000000)
    currency: str = Field(default='USD', pattern=r'^[A-Z]{3}$')
    leverage: int = Field(default=100, ge=1, le=1000)
    execution_delay_ms: int = Field(default=0, ge=0, le=600000)
    optimization: Literal[1,2] = 1
    optimization_criterion: Literal[0,1,2,3,4,5,6,7] = 0
    forward_mode: Literal[0,1,2,3,4] = 0
    forward_date: date | None = None
    enable_test_entries: bool = True

    @model_validator(mode='after')
    def dates(self):
        if self.date_to <= self.date_from or (self.date_to-self.date_from).days > 3660:
            raise ValueError('Use datas crescentes, com intervalo máximo de dez anos.')
        if self.forward_mode == 4 and (self.forward_date is None or not self.date_from < self.forward_date < self.date_to):
            raise ValueError('Forward personalizado exige data dentro do intervalo.')
        if self.forward_mode != 4 and self.forward_date is not None:
            raise ValueError('ForwardDate só se aplica ao modo personalizado.')
        return self
