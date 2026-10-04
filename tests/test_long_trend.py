from dataclasses import replace
import hashlib
import math
from pathlib import Path
import unittest

from roostoo_bot.backtest import Candle
from roostoo_bot.basket_research import PAIRS
from roostoo_bot.long_trend import (
    DAY_US, PLAN_SHA256, START, STRATEGIES, allocation, assess, block_intervals, periods, schedule_for, trial_data,
)
from roostoo_bot.portfolio_backtest import BAR_US, ScheduledTarget, research_settings, simulate_portfolio


class LongTrendTests(unittest.TestCase):
    def history(self, direction=1):
        return {p:[100*math.exp(direction*.001*i) for i in range(366)] for p in PAIRS}

    def test_three_horizons_up_down_and_flat(self):
        up=allocation(self.history())
        self.assertEqual(up['targets'],dict.fromkeys(PAIRS,.14))
        self.assertEqual(up['votes'][PAIRS[0]],[1,1,1])
        self.assertEqual(allocation(self.history(-1))['targets'],dict.fromkeys(PAIRS,0))
        self.assertEqual(allocation(self.history(0))['targets'],dict.fromkeys(PAIRS,0))
        self.assertEqual(allocation(self.history(0),timing=False)['targets'],dict.fromkeys(PAIRS,.14))

    def test_mixed_horizon_vote_and_covariance_budget(self):
        history=self.history(0)
        for p in PAIRS:
            history[p][-1]=110
            history[p][-31]=100
            history[p][-91]=120
            history[p][0]=100
        result=allocation(history)
        self.assertEqual(result['votes'][PAIRS[0]],[1,-1,1])
        self.assertAlmostEqual(result['preliminary'][PAIRS[0]],.14/3)
        history=self.history()
        for p in PAIRS:
            for i in range(345,366): history[p][i]=200*math.exp(.1*(i%2))
        result=allocation(history)
        self.assertLess(result['scale'],1)
        self.assertAlmostEqual(result['estimated_daily_volatility']*result['scale'],.0075)
        self.assertLessEqual(sum(result['targets'].values()),.7+1e-12)

    def test_bad_history_rejected(self):
        for mutate in (lambda h:h.pop(PAIRS[0]),lambda h:h[PAIRS[0]].pop(),lambda h:h[PAIRS[0]].__setitem__(-1,math.nan)):
            history=self.history();mutate(history)
            with self.assertRaises(ValueError): allocation(history)

    def days(self):
        return {p:{START-(366-i)*DAY_US:100*math.exp(.001*i) for i in range(368)} for p in PAIRS}

    def test_future_close_cannot_change_earlier_schedule(self):
        days=self.days()
        original,_=schedule_for(days,START,START+2*DAY_US)
        days[PAIRS[0]][START]=1
        changed,_=schedule_for(days,START,START+2*DAY_US)
        self.assertEqual(original[START+BAR_US],changed[START+BAR_US])
        self.assertNotEqual(original[START+DAY_US+BAR_US],changed[START+DAY_US+BAR_US])
        self.assertEqual(original[START+BAR_US].source_cutoff_us,START)

    def test_missing_required_daily_close_excludes_trial(self):
        days=self.days();days[PAIRS[0]][START-100*DAY_US]=None
        schedule,reason=schedule_for(days,START,START+DAY_US)
        self.assertIsNone(schedule)
        self.assertEqual(reason['reason'],'missing_required_daily_close')

    def test_missing_execution_bar_never_forward_filled(self):
        prices={p:{START+i*BAR_US:Candle(START+i*BAR_US,100,100) for i in range(4)} for p in PAIRS}
        self.assertIsNotNone(trial_data(prices,START,START+4*BAR_US))
        del prices[PAIRS[0]][START+BAR_US]
        self.assertIsNone(trial_data(prices,START,START+4*BAR_US))

    def test_fixed_calendar_and_plan(self):
        periods_=periods()
        self.assertEqual(len(periods_),78)
        self.assertTrue(all(b-a==14*DAY_US for _,a,b in periods_))
        self.assertTrue(all(a[2]==b[1] for a,b in zip(periods_,periods_[1:])))
        root=Path(__file__).resolve().parents[1]
        self.assertEqual(hashlib.sha256((root/'LONG_TREND_PLAN.md').read_bytes()).hexdigest(),PLAN_SHA256)

    def test_bootstrap_paired_gaps_and_reproducibility(self):
        a=[.01]*78;b=[0]*78;a[10]=b[10]=None
        result=block_intervals(a,b,repetitions=20)
        self.assertEqual(result,block_intervals(a,b,repetitions=20))
        self.assertEqual(result['return_interval'],[.01,.01])
        self.assertEqual(result['advantage_interval'],[.01,.01])
        b[10]=0
        with self.assertRaises(ValueError): block_intervals(a,b)

    def good_rows(self):
        return [dict(period=p,strategy=s,cost=c,total_return=.01 if s=='long_trend' else 0,
                     max_drawdown=.01,active_days_utc=10,active_days_hkt=10,turnover=1,start_us=first)
                for p,first,_ in periods() for s in STRATEGIES for c in ('base','stress')]

    def test_full_gates_do_not_approve_live_and_bad_inventory_rejected(self):
        rows=self.good_rows();result=assess(rows,[])
        self.assertTrue(result['screen_passed'])
        self.assertFalse(result['strategy_approved'])
        with self.assertRaises(ValueError): assess(rows[:-1],[])
        with self.assertRaises(ValueError): assess(rows+[rows[0]],[])
        missing={p for p,_,_ in periods()[:4]}
        reduced=[r for r in rows if r['period'] not in missing]
        result=assess(reduced,[dict(period=p) for p in missing])
        self.assertFalse(result['costs']['base']['gates']['coverage'])
        for row in rows:
            if row['strategy']=='long_trend': row['active_days_utc']=7
        self.assertFalse(assess(rows,[])['screen_passed'])


class ScheduledPortfolioTests(unittest.TestCase):
    def setUp(self):
        self.cfg=research_settings(api_key='',secret_key='',signal_source='offline',strategy='cash',fast_window=1,slow_window=2)
        self.data={p:[Candle(START+i*BAR_US,100,100) for i in range(10)] for p in self.cfg.pairs}
        self.schedule={START+BAR_US:ScheduledTarget(START,dict.fromkeys(self.cfg.pairs,.35))}

    def test_schedule_buys_once_and_does_not_force_repeated_orders(self):
        _,curve,trades=simulate_portfolio(self.data,self.cfg,target_schedule=self.schedule,liquidate=False)
        self.assertEqual(len(trades),2)
        self.assertTrue(all(t['timestamp_us']==START+BAR_US for t in trades))
        self.assertGreaterEqual(min(r['cash'] for r in curve),0)
        empty,_,orders=simulate_portfolio(self.data,self.cfg,target_schedule={})
        self.assertEqual(empty['total_return'],0)
        self.assertFalse(orders)

    def test_normal_path_is_unchanged_when_schedule_omitted(self):
        self.assertEqual(simulate_portfolio(self.data,self.cfg),simulate_portfolio(self.data,self.cfg,target_schedule=None))

    def test_schedule_rejects_nonoffline_benchmark_future_and_bad_weights(self):
        with self.assertRaises(ValueError): simulate_portfolio(self.data,replace(self.cfg,signal_source='binance'),target_schedule=self.schedule)
        with self.assertRaises(ValueError): simulate_portfolio(self.data,self.cfg,target_schedule=self.schedule,benchmark='cash')
        for target in (ScheduledTarget(START+1,dict.fromkeys(self.cfg.pairs,.35)),
                       ScheduledTarget(START,dict.fromkeys(self.cfg.pairs,.36)),
                       ScheduledTarget(START,{'BTC/USD':.35}),
                       ScheduledTarget(START,dict.fromkeys(self.cfg.pairs,math.nan))):
            with self.assertRaises(ValueError): simulate_portfolio(self.data,self.cfg,target_schedule={START+BAR_US:target})
        with self.assertRaises(ValueError): simulate_portfolio(self.data,self.cfg,target_schedule={START+20*BAR_US:next(iter(self.schedule.values()))})

    def test_risk_exit_overrides_and_latches_against_later_schedule(self):
        data={p:[replace(c,open=50,close=50) if i>=4 else c for i,c in enumerate(rows)] for p,rows in self.data.items()}
        schedule={**self.schedule,START+7*BAR_US:ScheduledTarget(START+6*BAR_US,dict.fromkeys(self.cfg.pairs,.35))}
        result,_,trades=simulate_portfolio(data,self.cfg,target_schedule=schedule)
        self.assertTrue(result['drawdown_halted'])
        self.assertTrue(any(t['side']=='SELL' and t['reason']=='drawdown_limit' for t in trades))
        self.assertFalse(any(t['side']=='BUY' and t['timestamp_us']>=START+4*BAR_US for t in trades))

    def test_future_execution_prices_cannot_change_prior_fills(self):
        _,_,first=simulate_portfolio(self.data,self.cfg,target_schedule=self.schedule)
        changed={p:[replace(c,open=200,close=200) if i>=5 else c for i,c in enumerate(rows)] for p,rows in self.data.items()}
        _,_,second=simulate_portfolio(changed,self.cfg,target_schedule=self.schedule)
        prior=lambda rows:[t for t in rows if t['timestamp_us']<START+5*BAR_US]
        self.assertEqual(prior(first),prior(second))
