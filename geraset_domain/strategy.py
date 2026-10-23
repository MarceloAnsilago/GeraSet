"""Version 1 strategy document. No Flask, terminal, provider or persistence imports."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator


Timeframe = Literal['M1','M2','M3','M4','M5','M6','M10','M12','M15','M20','M30',
                    'H1','H2','H3','H4','H6','H8','H12','D1','W1','MN1']
SlotTimeframe = Literal['current','M1','M2','M3','M4','M5','M6','M10','M12','M15','M20','M30',
                        'H1','H2','H3','H4','H6','H8','H12','D1','W1','MN1']
Price = Literal['close','open','high','low','median','typical','weighted']
Number = Annotated[Decimal, Field(max_digits=32, decimal_places=12)]
Amount = Annotated[Number, Field(ge=0, le=100000000)]
Period = Annotated[int, Field(strict=True, ge=1, le=100000)]
Clock = Annotated[str, Field(pattern=r'^(?:[01]\d|2[0-3]):[0-5][05]$')]


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False,
                              validate_default=True, frozen=True, revalidate_instances='always')


class ExecutionContext(Model):
    """A resolved execution context, never emitted as an EA input."""
    symbol: str = Field(min_length=1, max_length=40, pattern=r'^[A-Za-z0-9_.@#$-]+$')
    base_timeframe: Timeframe


class CreationMetadata(Model):
    origin: Literal['user','agent','import'] = 'user'
    created_at: AwareDatetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    author: str | None = Field(default=None, max_length=120)
    original_request: str | None = Field(default=None, max_length=10000)
    model_reference: str | None = Field(default=None, max_length=200)


class Operation(Model):
    market: Literal['forex','b3'] = 'forex'
    trade_mode: Literal['day_trade','swing_trade'] = 'day_trade'
    direction: Literal['both','buy','sell'] = 'both'
    lot: Number = Field(default=Decimal('0.01'), gt=0)


class Session(Model):
    entry_start: Clock = '00:00'
    entry_end: Clock = '23:55'
    clock_basis: Literal['broker_server'] = 'broker_server'


class MarketOrder(Model):
    type: Literal['market'] = 'market'


class PendingOrder(Model):
    type: Literal['pending'] = 'pending'
    reference: Literal['high','low','open','close'] = 'high'
    candle: Period = 1
    mirror_sell: bool = Field(default=False, strict=True)


class Indicator(Model):
    slot: int = Field(strict=True, ge=1, le=4)
    purpose: Literal['entry','exit'] = 'entry'
    timeframe: SlotTimeframe = 'current'
    period: Period = 14


class MovingAverage(Indicator):
    type: Literal['ma'] = 'ma'
    period: Period = 20
    method: Literal['sma','ema','smma','lwma'] = 'ema'
    price: Price = 'close'
    shift: int = Field(default=0, strict=True, ge=-100000, le=100000)


class RSI(Indicator):
    type: Literal['rsi'] = 'rsi'
    price: Price = 'close'
    lower: Number = Field(default=30, ge=0, le=100)
    middle: Number = Field(default=50, ge=0, le=100)
    upper: Number = Field(default=70, ge=0, le=100)


class ADX(Indicator):
    type: Literal['adx'] = 'adx'


class PriceOperand(Model):
    kind: Literal['price'] = 'price'
    source: Literal['close','open','high','low','day_open','day_high','day_low','previous_day_high','previous_day_low']
    candle: int = Field(default=1, strict=True, ge=0, le=3)


class IndicatorOperand(Model):
    kind: Literal['indicator'] = 'indicator'
    slot: int = Field(strict=True, ge=1, le=4)
    line: Literal['main','di_plus','di_minus','upper','middle','lower'] = 'main'
    candle: int = Field(default=1, strict=True, ge=0, le=3)


class FixedOperand(Model):
    kind: Literal['fixed'] = 'fixed'
    value: Number = Field(ge=-100000000000000000000, le=100000000000000000000)


LeftOperand = Annotated[PriceOperand | IndicatorOperand, Field(discriminator='kind')]
RightOperand = Annotated[PriceOperand | IndicatorOperand | FixedOperand, Field(discriminator='kind')]


class Rule(Model):
    operator: Literal['if','and','or'] = 'if'
    # Always the position acted on: exit/buy means close buys, unlike native side.
    side: Literal['buy','sell']
    left: LeftOperand
    comparison: Literal['gt','lt','gte','lte','eq','ne','touch','cross_up','cross_down','cross_close_up','cross_close_down']
    right: RightOperand
    distance: Amount = Decimal(0)
    distance_unit: Literal['none','points','percent'] = 'none'


class FixedStop(Model):
    type: Literal['fixed'] = 'fixed'
    distance: Amount = Decimal(0)


class CandleStop(Model):
    type: Literal['candle'] = 'candle'
    distance: Amount = Decimal(0)
    multiplier: Amount = Decimal(1)
    candle: int = Field(default=1, strict=True, ge=1, le=3)
    measure: Literal['total','body'] = 'total'


class FixedTake(Model):
    type: Literal['fixed'] = 'fixed'
    distance: Amount = Decimal(0)


class StopMultipleTake(Model):
    type: Literal['stop_multiple'] = 'stop_multiple'
    multiplier: Amount = Decimal(2)


class Breakeven(Model):
    mode: Literal['disabled','points','percent'] = 'disabled'
    trigger: Amount = Decimal(0)
    offset: Amount = Decimal(0)


class ManagedStop(Model):
    mode: Literal['disabled','points','percent'] = 'disabled'
    distance_policy: Literal['fixed'] = 'fixed'
    trigger: Amount = Decimal(0)
    distance: Amount = Decimal(0)
    adjustment_step: Amount = Decimal(0)


class Risk(Model):
    target_unit: Literal['points','percent'] = 'points'
    stop_loss: Annotated[FixedStop | CandleStop, Field(discriminator='type')] = Field(default_factory=CandleStop)
    take_profit: Annotated[FixedTake | StopMultipleTake, Field(discriminator='type')] = Field(default_factory=StopMultipleTake)
    breakeven: Breakeven = Field(default_factory=Breakeven)
    trailing: ManagedStop = Field(default_factory=ManagedStop)
    moving_stop: ManagedStop = Field(default_factory=ManagedStop)


class NumericRange(Model):
    kind: Literal['numeric'] = 'numeric'
    parameter: str = Field(min_length=1, max_length=100)
    start: Number
    step: Number = Field(gt=0)
    end: Number

    @model_validator(mode='after')
    def ascending(self):
        if self.end < self.start:
            raise ValueError('O fim deve ser maior ou igual ao início.')
        return self


class ChoiceRange(Model):
    kind: Literal['choice'] = 'choice'
    parameter: str = Field(min_length=1, max_length=100)
    start: str
    end: str


class TimeRange(Model):
    kind: Literal['time'] = 'time'
    parameter: Literal['session.entry_start','session.entry_end']
    start: Clock
    end: Clock


Optimization = Annotated[NumericRange | ChoiceRange | TimeRange, Field(discriminator='kind')]


class StrategySpec(Model):
    schema_version: Literal['1.0'] = '1.0'
    strategy_id: UUID = Field(default_factory=uuid4)
    revision: int = Field(default=1, strict=True, ge=1)
    parent_revision: int | None = Field(default=None, strict=True, ge=1)
    name: str = Field(min_length=1, max_length=48, pattern=r'^[^\x00-\x1f\x7f|]+$')
    magic: int = Field(strict=True, ge=1, le=2147483647)
    metadata: CreationMetadata = Field(default_factory=CreationMetadata)
    execution_hint: ExecutionContext | None = None
    operation: Operation = Field(default_factory=Operation)
    session: Session = Field(default_factory=Session)
    order: Annotated[MarketOrder | PendingOrder, Field(discriminator='type')] = Field(default_factory=MarketOrder)
    indicators: tuple[Annotated[MovingAverage | RSI | ADX, Field(discriminator='type')], ...] = Field(default=(), max_length=4)
    entry_rules: tuple[Rule, ...] = Field(default=(), max_length=10)
    exit_rules: tuple[Rule, ...] = Field(default=(), max_length=10)
    risk: Risk = Field(default_factory=Risk)
    optimization: tuple[Optimization, ...] = Field(default=(), max_length=100)

    @model_validator(mode='after')
    def compatible(self):
        if self.parent_revision is not None and self.parent_revision >= self.revision:
            raise ValueError('A revisão anterior deve ser menor que a revisão atual.')
        if len({i.slot for i in self.indicators}) != len(self.indicators):
            raise ValueError('Cada slot aceita apenas um indicador.')
        if not 1 <= len(self.entry_rules) + len(self.exit_rules) <= 10:
            raise ValueError('A estratégia exige de uma a dez condições no total.')
        from .uni_mapping import compile_strategy
        from .errors import UniValidationError
        try:
            compile_strategy(self)
        except UniValidationError as exc:
            raise ValueError(exc.message) from exc
        return self


class ValidationIssue(Model):
    path: tuple[str | int, ...]
    code: str
    message: str


class StrategyValidation(Model):
    state: Literal['invalid','structurally_valid']
    financial_state: Literal['not_tested'] = 'not_tested'
    contract_sha256: str
    issues: tuple[ValidationIssue, ...] = ()
    strategy: StrategySpec | None = None
    pending_checks: tuple[str, ...] = ('symbol_volume_limits','tick_and_stop_limits','margin','history','broker_execution')


def validate_strategy(payload) -> StrategyValidation:
    """Always computes validation state; input cannot approve itself."""
    from .uni_mapping import contract_hash
    try:
        strategy = StrategySpec.model_validate(payload)
    except ValidationError as exc:
        issues = tuple(ValidationIssue(path=e['loc'], code=e['type'], message=e['msg']) for e in exc.errors())
        return StrategyValidation(state='invalid', contract_sha256=contract_hash(), issues=issues)
    return StrategyValidation(state='structurally_valid', contract_sha256=contract_hash(), strategy=strategy)
