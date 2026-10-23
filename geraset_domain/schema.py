"""Generate/check the JSON Schema artifact: python -m geraset_domain.schema --check."""
import argparse
import json
from pathlib import Path

from .strategy import StrategySpec


def strategy_schema():
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema',
            '$id': 'urn:geraset:strategy:1.0', **StrategySpec.model_json_schema()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    target = Path(__file__).with_name('strategy-v1.schema.json')
    expected = strategy_schema()
    if args.check:
        if json.loads(target.read_text(encoding='utf-8')) != expected:
            parser.exit(1, 'Schema JSON divergente do modelo Python.\n')
        print('Schema 1.0 conferido.')
    else:
        target.write_text(json.dumps(expected, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print('Schema 1.0 gerado.')


if __name__ == '__main__':
    main()
