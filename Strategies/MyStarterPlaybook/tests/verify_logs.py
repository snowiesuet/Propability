"""Validate harness output with the stdlib; also validate pandas ingestion when installed."""
import csv
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])


def load(name):
    folders = list((root / name).iterdir())
    assert len(folders) == 1, (name, folders)
    folder = folders[0]
    metadata = json.loads((folder / 'run_metadata.json').read_text(encoding='utf-8'))
    tables = {}
    for filename in ('executions', 'trades', 'equity', 'bars'):
        with (folder / (filename + '.csv')).open(encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            assert all(None not in row and None not in row.values() for row in rows)
            tables[filename] = rows
    return metadata, tables


def number(value):
    return float(value) if value else None


m, t = load('main')
e, trades = t['executions'], t['trades']
assert len(e) == 7 and len(trades) == 5
assert m['duplicate_execution_count'] == 1 and m['usable']
assert m['final_signed_position_quantity'] == 0
assert sum(float(row['realized_pnl']) for row in e) == -200
assert sum(float(row['gross_realized_pnl']) for row in trades) == -200
assert sum(float(row['commission']) for row in e) == 7
assert sum(float(row['commissions']) for row in trades) == 7
assert sum(float(row['net_realized_pnl']) for row in trades) == -207
assert trades[0]['entry_execution_id'] == 'b'  # associated exit skips FIFO A
assert trades[1]['entry_execution_id'] == 'a'
assert trades[2]['exit_reason'] == 'Reversal'
assert e[4]['signed_position_quantity_after_execution'] == '-2'
assert e[4]['position_id'] != e[4]['previous_position_id']
assert e[0]['strategy_name'] == 'Cont, Rev\n"test"'
assert e[0]['timestamp'].endswith('-04:00')
assert t['bars'][0]['trading_day'] == '2026-10-22'  # provided exchange day, not calendar date
assert t['equity'][-1]['net_equity_change'] == '-207'
assert trades[1]['maximum_favorable_excursion'] == '1200'
assert trades[1]['maximum_adverse_excursion'] == '600'
assert len({row['trade_id'] for row in trades}) == len(trades)

m, t = load('unknown')
assert m['final_signed_position_quantity'] == -1 and not m['commissions_complete']
assert t['trades'][0]['commissions'] == t['trades'][0]['net_realized_pnl'] == ''
assert t['executions'][0]['realized_pnl'] == '0'
assert m['final_open_lots'][0]['quantity'] == 1
m, t = load('platform')
assert t['executions'][0]['commission'] == '0'
assert t['trades'][0]['commissions'] == '2' and t['trades'][0]['net_realized_pnl'] == '38'
m, t = load('identity')
assert len(t['executions']) == 4 and m['final_signed_position_quantity'] == 0
assert 'ExecutionIdentityUnavailable' in t['executions'][0]['data_quality']
assert all(float(row['commission']) == 0 for row in t['executions'])
seq = [int(row['event_sequence']) for row in t['executions'] + t['equity']]
assert len(seq) == len(set(seq))
m, t = load('partials')
assert len(t['executions']) == 4 and len(t['trades']) == 3
assert t['executions'][0]['order_id'] == t['executions'][1]['order_id'] == 'entry'
assert sum(float(row['gross_realized_pnl']) for row in t['trades']) == -200
assert sum(float(row['commissions']) for row in t['trades']) == 1.5
assert t['trades'][0]['exit_reason'] == 'StopLoss'
assert all(row['exit_reason'] == 'SessionClose' for row in t['trades'][1:])
assert m['final_signed_position_quantity'] == 0
m, t = load('missing_platform_cost')
assert t['executions'][0]['commission'] == '' and not m['commissions_complete']
m, t = load('unresolved')
assert not m['usable'] and not m['accounting_complete']
assert all(row['realized_pnl'] == '' for row in t['executions'])
m, t = load('dst')
assert all('TimezoneUnresolved' in row['data_quality'] for row in t['equity'])
assert all(len(row['timestamp']) == 27 for row in t['equity'])
m, _ = load('failed')
assert m['completion_status'] == 'Failed' and not m['usable']
m, t = load('fallback')
assert 'SignalMatchFallbackFIFO' in t['executions'][-1]['data_quality']
m, _ = load('io')
assert m['completion_status'] == 'Running' and not m['usable']
assert len(list((root / 'concurrent').iterdir())) == 4

try:
    import pandas as pd
except ImportError:
    print('stdlib CSV/accounting checks passed; pandas unavailable')
else:
    for folder in root.glob('*/*'):
        for path in folder.glob('*.csv'):
            frame = pd.read_csv(path, keep_default_na=False)
            assert 'run_id' in frame.columns
            if 'execution_price' in frame and len(frame):
                assert pd.to_numeric(frame['execution_price']).notna().all()
    print('CSV/accounting and pandas ingestion checks passed')
