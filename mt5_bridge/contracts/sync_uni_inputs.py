"""Build/check the transport contract against MQL5, without compiling or running MT5.

Run from the repository: python -m mt5_bridge.contracts.sync_uni_inputs
    --uni-root PATH --check
Omit --check to regenerate the JSON. Semantic limits below are reviewed against
the configuration/indicator validators; declarations supply types/enums/defaults.
"""
import argparse
import json
from pathlib import Path
import re


def build_contract(root):
    root = Path(root)
    paths = [root/'UniEA.mq5', root/'Include/Configuration/UniTypes.mqh',
             root/'Include/Configuration/UniInputOptions.mqh']
    sources = [p.read_text(encoding='utf-8-sig') for p in paths]
    enums, constants = {}, {'clrWhite': 16777215}
    for source in sources:
        source = re.sub(r'//[^\n]*|/\*.*?\*/', '', source, flags=re.S)
        for name, body in re.findall(r'enum\s+(\w+)\s*\{([^}]+)\}', source):
            entries, current = {}, -1
            for item in body.split(','):
                if not item.strip():
                    continue
                parts = item.strip().split('=')
                current = int(parts[1].strip()) if len(parts) == 2 else current + 1
                entries[parts[0].strip()] = current
            enums[name] = entries
            constants.update(entries)
    contract = {}
    for storage, kind, key, literal in re.findall(
            r'^\s*(s?input)\s+(\w+)\s+(Inp\w+)\s*=\s*([^;]+);', sources[0], re.M):
        literal = literal.strip()
        if kind == 'string':
            default = json.loads(literal)
        elif kind == 'bool':
            default = {'true': True, 'false': False}[literal]
        elif literal in constants:
            default = constants[literal]
        elif literal.startswith("C'"):
            rgb = [int(n) for n in literal[2:-1].split(',')]
            default = sum(n << (8*i) for i, n in enumerate(rgb))
        else:
            default = float(literal) if kind == 'double' else int(literal)
        entry = dict(kind='enum' if kind in enums else kind, source_type=kind,
                     default=default, optimizable=storage == 'input' and kind != 'string')
        if kind == 'int':
            entry.update(min=-2147483648, max=2147483647)
        if kind in enums:
            entry['enum_values'] = enums[kind]
        if kind == 'bool':
            entry['values'] = [0, 1]
        if key == 'InpCurveSession':
            entry['internal'] = True
        if key == 'InpName':
            entry.update(min_length=1, max_length=48)
        if key == 'InpMagic':
            entry.update(min=1, max=2147483647)
        if key == 'InpLot':
            entry.update(exclusive_min=0, unit='lots', dynamic_limits='symbol volume min/max/step')
        if key in ('InpEntryStart', 'InpEntryEnd'):
            entry.update(min=0, max=1435, multiple_of=5, unit='server_minutes_since_midnight')
        if key == 'InpPendingCandle':
            entry.update(min=1, max=100000, unit='closed_bars')
        if key == 'InpStopCandle':
            entry.update(min=1, max=3, unit='closed_bars')
        if key == 'InpHistogramasBarras':
            entry.update(min=1, max=5000, unit='bars')
        if key == 'InpMarkerFontSize':
            entry.update(unit='font_size', runtime_clamp=[10, 20])
        if key.endswith('Period'):
            entry.update(min=1, max=100000, unit='bars')
        if key.endswith('MaShift'):
            entry.update(min=-100000, max=100000, unit='bars')
        if re.fullmatch(r'InpRsi(?:Entry|Exit)(?:Upper|Middle|Lower)', key):
            entry.update(min=0, max=100, unit='oscillator_level')
        if kind == 'double' and key != 'InpLot' and 'min' not in entry:
            entry.update(min=0, max=100000000)
            if key in ('InpStopLoss', 'InpTakeProfit'):
                entry['unit'] = 'InpTargetUnit: points or percent_of_entry_price'
            elif key in ('InpStopCandleMultiplier', 'InpTakeStopMultiplier'):
                entry['unit'] = 'multiplier'
            else:
                mode = ('Breakeven' if 'Breakeven' in key else
                        'MovingStop' if 'MovingStop' in key else 'Trailing')
                entry['unit'] = f'Inp{mode}Mode: points or percent_of_entry_price'
        contract[key] = entry
    if not contract or not enums:
        raise ValueError('Declarações MQL5 não encontradas.')
    return contract


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uni-root', required=True, type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    target = Path(__file__).with_name('uni_inputs.json')
    expected = build_contract(args.uni_root)
    if args.check:
        actual = json.loads(target.read_text(encoding='utf-8'))
        changed = sorted(k for k in actual.keys() | expected.keys() if actual.get(k) != expected.get(k))
        if changed:
            parser.exit(1, 'Contrato divergente: '+', '.join(changed)+'\n')
        print(f'Contrato conferido: {len(expected)} inputs; nomes, tipos, enums, padrões e limites.')
    else:
        target.write_text(json.dumps(expected, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(f'Contrato atualizado: {len(expected)} inputs.')


if __name__ == '__main__':
    main()
