import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from roostoo_bot.attention import (
    PAIRS, PLAN_SHA256, STRATEGIES, assess, load_counts, parse_counts,
    requests, schedules, trial_data, verify_plan,
)
from roostoo_bot.backtest import Candle
from roostoo_bot.long_trend import DAY_US, periods
from roostoo_bot.portfolio_backtest import BAR_US, research_settings, simulate_portfolio
from roostoo_bot.research import stamp

START = stamp('2022-01-01')


class AttentionTests(unittest.TestCase):
    def row(self, **changes):
        return dict(dict(project='en.wikipedia', article='Bitcoin', granularity='daily',
            access='all-access', agent='user', timestamp='2021120100', views=123), **changes)

    def parse(self, rows):
        return parse_counts(json.dumps(dict(items=rows)).encode(), 'Bitcoin', '20211201', '20211231')

    def test_parser_preserves_missing_and_zero(self):
        values = self.parse([self.row(), self.row(timestamp='2021120300', views=0)])
        self.assertEqual(values, {stamp('2021-12-01'): 123, stamp('2021-12-03'): 0})
        self.assertNotIn(stamp('2021-12-02'), values)

    def test_parser_rejects_metadata_and_counts(self):
        for changes in ({'agent':'all-agents'}, {'article':'Ethereum'}, {'project':'other'},
                        {'views':True}, {'views':-1}, {'views':1.5}, {'views':'10'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.parse([self.row(**changes)])

    def test_parser_rejects_dates_duplicates_and_order(self):
        for rows in ([self.row(), self.row()], [self.row(timestamp='2021120300'), self.row()],
                     [self.row(timestamp='2022010100')], [self.row(timestamp='2021120101')],
                     [self.row(timestamp=2021120100)], [self.row(timestamp='2021130100')]):
            with self.assertRaises(ValueError): self.parse(rows)

    def test_snapshot_complete_inventory_and_checksum(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            manifest = dict(plan_sha256=PLAN_SHA256, inputs=[])
            for item in requests():
                payload = json.dumps(dict(items=[self.row(article=item['page'], timestamp=item['first']+'00')])).encode()
                (path/item['file']).write_bytes(payload)
                manifest['inputs'].append(dict(**item, sha256=hashlib.sha256(payload).hexdigest(), rows=1, zero_rows=0))
            (path/'manifest.json').write_text(json.dumps(manifest))
            values, _ = load_counts(path)
            self.assertEqual([len(v) for v in values.values()], [4,4])
            (path/'Bitcoin-2021.json').write_bytes(b'{}')
            with self.assertRaises(ValueError): load_counts(path)

    def inputs(self):
        counts = {p:{START+i*DAY_US: 100-i for i in range(-3, 3)} for p in PAIRS}
        days = {p:{START+i*DAY_US: 100+i for i in range(-3, 3)} for p in PAIRS}
        return counts, days

    def test_exact_direction_tie_and_publication_lag(self):
        counts, days = self.inputs()
        counts[PAIRS[1]][START-2*DAY_US] = counts[PAIRS[1]][START-3*DAY_US]
        targets, detail = schedules(counts, days, START, START+DAY_US)
        target = targets['attention'][START+BAR_US]
        self.assertEqual(target.weights, dict.fromkeys(PAIRS,.35))
        self.assertEqual(target.source_cutoff_us,START-DAY_US)
        self.assertEqual(START+BAR_US-target.source_cutoff_us,DAY_US+BAR_US)
        self.assertEqual(targets['price_contrarian'][START+BAR_US].weights,dict.fromkeys(PAIRS,0))
        counts[PAIRS[0]][START-2*DAY_US] = 999
        changed, _ = schedules(counts, days, START, START+DAY_US)
        self.assertEqual(changed['attention'][START+BAR_US].weights[PAIRS[0]],0)

    def test_future_attention_and_price_cannot_change_prior_decision(self):
        counts, days = self.inputs()
        original, _ = schedules(counts, days, START, START+2*DAY_US)
        counts[PAIRS[0]][START-DAY_US] = 999999
        days[PAIRS[0]][START-DAY_US] = .01
        changed, _ = schedules(counts, days, START, START+2*DAY_US)
        for strategy in STRATEGIES[:3]:
            self.assertEqual(original[strategy][START+BAR_US], changed[strategy][START+BAR_US])
        self.assertNotEqual(original['attention'][START+DAY_US+BAR_US],changed['attention'][START+DAY_US+BAR_US])

    def test_missing_zero_or_bad_signal_excludes_not_cashes_trial(self):
        for value in (None,0,True,-1,1.2):
            counts, days = self.inputs()
            counts[PAIRS[0]][START-2*DAY_US] = value
            targets, detail = schedules(counts, days, START, START+DAY_US)
            self.assertIsNone(targets)
            self.assertEqual(detail['reason'],'missing_or_zero_attention')
        counts, days = self.inputs()
        days[PAIRS[0]][START-2*DAY_US] = None
        self.assertIsNone(schedules(counts,days,START,START+DAY_US)[0])

    def test_execution_coverage_only_uses_traded_pairs(self):
        prices={p:{START+i*BAR_US:Candle(START+i*BAR_US,100,100) for i in range(4)} for p in PAIRS}
        prices['SOL/USD']={}
        self.assertEqual(set(trial_data(prices,START,START+4*BAR_US)),set(PAIRS))
        del prices[PAIRS[0]][START+BAR_US]
        self.assertIsNone(trial_data(prices,START,START+4*BAR_US))

    def test_constant_signal_does_not_force_roundtrips(self):
        counts, days = self.inputs()
        targets,_=schedules(counts,days,START,START+2*DAY_US)
        data={p:[Candle(START+i*BAR_US,100,100) for i in range(576)] for p in PAIRS}
        cfg=research_settings(api_key='',secret_key='',signal_source='offline',strategy='cash',
            pairs=PAIRS,fast_window=1,slow_window=2,max_asset_weight=.35,rebalance_band=.0025)
        _,_,trades=simulate_portfolio(data,cfg,target_schedule=targets['attention'],liquidate=False)
        self.assertEqual(len(trades),2)
        self.assertTrue(all(t['side']=='BUY' and t['timestamp_us']==START+BAR_US for t in trades))

    def good_rows(self):
        return [dict(period=p,strategy=s,cost=c,total_return=.01 if s=='attention' else 0,
            max_drawdown=.01,turnover=1,active_days_utc=10,active_days_hkt=10,start_us=first)
            for p,first,_ in periods() for s in STRATEGIES for c in ('base','stress')]

    def test_gates_and_historical_availability_never_approve_live(self):
        rows=self.good_rows()
        result=assess(rows,[])
        self.assertTrue(result['screen_passed'])
        self.assertFalse(result['strategy_approved'])
        self.assertFalse(result['historical_first_seen_verified'])
        for key,value in (('total_return',-.01),('max_drawdown',.081),('active_days_utc',7)):
            changed=copy.deepcopy(rows)
            for row in changed:
                if row['strategy']=='attention': row[key]=value
            self.assertFalse(assess(changed,[])['screen_passed'])

    def test_inventory_exclusions_and_denominator(self):
        rows=self.good_rows()
        for bad in (rows[:-1],rows+[rows[0]]):
            with self.assertRaises(ValueError): assess(bad,[])
        missing={p for p,_,_ in periods()[:4]}
        result=assess([r for r in rows if r['period'] not in missing],[dict(period=p) for p in missing])
        self.assertFalse(result['costs']['base']['gates']['coverage'])
        with self.assertRaises(ValueError): assess(rows,[dict(period='unknown')])

    def test_frozen_plan_and_exact_public_request_scope(self):
        verify_plan()
        self.assertEqual(len(list(requests())),8)
        self.assertTrue(all('/all-access/user/' in r['url'] for r in requests()))
        self.assertTrue(all(r['last'] <= '20241231' for r in requests()))


if __name__ == '__main__':
    unittest.main()
