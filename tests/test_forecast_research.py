from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from roostoo_bot.basket_research import PAIRS
from roostoo_bot.forecast_research import (
    AMENDMENT_SHA256, BAR_US, BREAK_EVEN, DAY_US, PLAN_SHA256, START, Day, assess, describe,
    features, fit, forecast, load_month, main, observations, periods, solve, stamp, training_rows,
)


class ForecastResearchTests(unittest.TestCase):
    def history(self, cutoff=START):
        return [Day(cutoff-(31-i)*DAY_US, 100*math.exp(.01*i), 100, 1000, 600, 0) for i in range(31)]

    def test_feature_values_and_weighting(self):
        x=features(self.history(), START)
        for actual, expected in zip(x, [.01, .07, .30, 0, 0, .2]):
            self.assertAlmostEqual(actual, expected)
        history=self.history()
        history[-1]=replace(history[-1], quote=2000, bought=1000)
        self.assertAlmostEqual(features(history, START)[4], math.log(2))

    def test_gap_zero_volume_and_future_day_handling(self):
        history=self.history()
        history[-10]=replace(history[-10], missing_bars=1)
        self.assertIsNone(features(history, START))
        history=self.history()
        history[-10]=replace(history[-10], quote=0)
        self.assertIsNone(features(history, START))
        for data in (history[:-1], list(reversed(history)), history[1:]+[replace(history[-1], start_us=START)]):
            with self.assertRaises(ValueError): features(data, START)

    def write_archive(self, directory, month, raw):
        path=Path(directory)/f'BTCUSDT-5m-{month}.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr(path.stem+'.csv', '\n'.join(','.join(row) for row in raw)+'\n')
        path.with_name(path.name+'.CHECKSUM').write_text(hashlib.sha256(path.read_bytes()).hexdigest())
        return path

    def raw(self, timestamp, unit=1000):
        return [str(timestamp//unit), '100', '101', '99', '100', '10',
                str((timestamp+BAR_US-unit)//unit), '1000', '2', '6', '600', '0']

    def test_archive_missing_bar_calendar_and_checksum(self):
        first=stamp('2021-01-01')
        with tempfile.TemporaryDirectory() as folder:
            path=self.write_archive(folder,'2021-01',[self.raw(first+i*BAR_US) for i in range(288) if i!=17])
            days=load_month(path)
            self.assertEqual(len(days),31)
            self.assertEqual(days[0].missing_bars,1)
            self.assertEqual(days[0].entry,100)
            self.assertEqual(days[1].missing_bars,288)
            self.assertIsNone(days[1].entry)
            path.with_name(path.name+'.CHECKSUM').write_text('0'*64)
            with self.assertRaises(ValueError): load_month(path)

    def test_archive_month_order_duplicate_and_schema(self):
        first=stamp('2021-01-01')
        with tempfile.TemporaryDirectory() as folder:
            bad_cases=([self.raw(first),self.raw(first)], [self.raw(first+BAR_US),self.raw(first)],
                       [self.raw(first-DAY_US)], [self.raw(first)[:-1]])
            for rows in bad_cases:
                path=self.write_archive(folder,'2021-01',rows)
                with self.assertRaises(ValueError): load_month(path)
            path=self.write_archive(folder,'2025-04',[self.raw(stamp('2025-04-01'),1)])
            with self.assertRaisesRegex(ValueError,'outside frozen'): load_month(path)

    def test_rejected_close_timestamp_is_missing_not_repaired(self):
        first=stamp('2021-01-01')
        raw=[self.raw(first+i*BAR_US) for i in range(288)]
        raw[1][6]=str((first-1)//1000)
        with tempfile.TemporaryDirectory() as folder:
            path=self.write_archive(folder,'2021-01',raw)
            day=load_month(path)[0]
            self.assertEqual(day.rejected_bars,1)
            self.assertEqual(day.missing_bars,1)
            self.assertIsNone(day.entry)
            self.assertEqual(day.quote,287000)
            path=self.write_archive(folder,'2021-01',[raw[1],raw[1]])
            with self.assertRaises(ValueError): load_month(path)
            raw[1][10]='nan'
            path=self.write_archive(folder,'2021-01',[raw[1]])
            with self.assertRaises(ValueError): load_month(path)

    def test_current_and_future_daily_data_do_not_change_features(self):
        days=self.history()+[Day(START+i*DAY_US,100,100,1000,600,0) for i in range(3)]
        data={p:days[:] for p in PAIRS}
        original=observations(data)
        data[PAIRS[0]][31]=replace(data[PAIRS[0]][31],close=200,quote=1e9,bought=0)
        changed=observations(data)
        self.assertEqual(original[0]['x'],changed[0]['x'])
        self.assertNotEqual(original[5]['x'],changed[5]['x'])
        self.assertEqual(original[0]['entry_us'],START+BAR_US)
        self.assertEqual(original[0]['exit_us'],START+DAY_US+BAR_US)
        data[PAIRS[0]][32]=replace(data[PAIRS[0]][32],entry=50)
        future=observations(data)
        self.assertEqual(changed[0]['x'],future[0]['x'])
        self.assertNotEqual(changed[0]['gross_return'],future[0]['gross_return'])

    def test_missing_exit_preserves_features_and_marks_basket_unscorable(self):
        days=self.history()+[Day(START+i*DAY_US,100,100,1000,600,0) for i in range(2)]
        data={p:days[:] for p in PAIRS}
        data[PAIRS[0]][-1]=replace(data[PAIRS[0]][-1],entry=None)
        rows=observations(data)
        self.assertTrue(all(not r['basket_covered'] for r in rows))
        self.assertTrue(all(r['x'] is not None for r in rows))
        self.assertIsNone(rows[0]['gross_return'])
        self.assertEqual(rows[1]['gross_return'],0)

    def test_solver_and_singular_nonfinite_rejection(self):
        answer=solve([[2,1],[1,3]],[4,7])
        self.assertAlmostEqual(answer[0],1)
        self.assertAlmostEqual(answer[1],2)
        for matrix in ([[0,0],[0,0]],[[math.nan,0],[0,1]]):
            with self.assertRaises(ValueError): solve(matrix,[1,1])

    def test_ridge_solution_and_unpenalized_intercept(self):
        xs=[[-1,0,0,0,0,0],[1,0,0,0,0,0]]
        model=fit(xs,[.01,.03])
        self.assertAlmostEqual(model.intercept,.02)
        self.assertAlmostEqual(model.coefficients[0],.01/1.1)
        self.assertEqual(model.scales[1:], [1]*5)
        self.assertAlmostEqual(model.predict([0]*6),.02)
        self.assertAlmostEqual(model.training_mean,.02)

    def test_training_clips_labels_and_standardized_features(self):
        xs=[[0]*6 for _ in range(100)]+[[1000]*6]
        ys=[0]*100+[1]
        model=fit(xs,ys)
        self.assertEqual(model.standardized([1e12]*6),[5]*6)
        self.assertEqual(model.standardized([-1e12]*6),[-5]*6)
        predictions=[model.predict(x) for x in xs]
        self.assertAlmostEqual(sum(predictions)/101,.2/101)
        self.assertAlmostEqual(model.training_mean,1/101)
        with self.assertRaises(ValueError): fit([[0]*5],[0])
        with self.assertRaises(ValueError): fit([[math.nan]*6],[0])

    def rows(self, count=368):
        output=[]
        first=stamp('2021-01-01')
        for i in range(count):
            t=first+i*DAY_US
            for p in PAIRS:
                output.append(dict(pair=p,entry_us=t+BAR_US,exit_us=t+DAY_US+BAR_US,
                    date_utc=datetime.fromtimestamp(t/1e6,timezone.utc).date().isoformat(),
                    x=[.001*(i%7)]*6,gross_return=.01,base_return=.007,stress_return=.005,
                    gross_advantage=0,base_advantage=0,stress_advantage=0,basket_covered=True))
        return output

    def test_strict_label_embargo(self):
        rows=self.rows()
        rows.append(dict(rows[0],entry_us=START-DAY_US,exit_us=START))
        train=training_rows(rows,START)
        self.assertTrue(all(r['exit_us']<START for r in train))
        self.assertEqual(len(train),364*5)

    def test_future_labels_and_features_do_not_change_earlier_model(self):
        rows=self.rows()
        original, models=forecast(rows,START,START+3*DAY_US)
        changed=[dict(r,x=[100]*6,gross_return=-.9) if r['entry_us']>=START+DAY_US else dict(r) for r in rows]
        later, later_models=forecast(changed,START,START+3*DAY_US)
        self.assertEqual(models,later_models)
        self.assertEqual(original[:5],later[:5])
        self.assertTrue(all(r['signal'] for r in original))
        self.assertTrue(all(r['fit_us']==START for r in original))
        self.assertLess(models['2022-01']['max_training_exit_us'],START)

    def test_cost_threshold_equality_and_missing_labels(self):
        rows=self.rows()
        for row in rows:
            row['x']=[0]*6
            row['gross_return']=BREAK_EVEN
        with patch('roostoo_bot.forecast_research.Model.predict',return_value=BREAK_EVEN):
            predicted,_=forecast(rows,START,START+3*DAY_US)
            self.assertTrue(all(not r['signal'] for r in predicted))
        for row in rows:
            row['gross_return']=.01
        rows[-15]['basket_covered']=False
        predicted,_=forecast(rows,START,START+3*DAY_US)
        self.assertTrue(predicted[0]['signal'])
        self.assertFalse(predicted[0]['selected'])
        self.assertLess(describe(predicted)['coverage'],1)

    def test_monthly_refit_uses_only_matured_labels(self):
        rows=self.rows(405)
        end=stamp('2022-02-05')
        _,original=forecast(rows,START,end)
        changed=[dict(r,gross_return=-.1) if START <= r['entry_us'] < stamp('2022-02-01') else dict(r) for r in rows]
        _,later=forecast(changed,START,end)
        self.assertEqual(original['2022-01'],later['2022-01'])
        self.assertNotEqual(original['2022-02']['model'],later['2022-02']['model'])
        self.assertLess(later['2022-02']['max_training_exit_us'],stamp('2022-02-01'))

    def test_insufficient_training_and_period_boundaries(self):
        rows=self.rows()[-30:]
        predicted, models=forecast(rows,START,START+3*DAY_US)
        self.assertTrue(all(r['forecast'] is None and not r['selected'] for r in predicted))
        self.assertTrue(all(v['model'] is None for v in models.values()))
        self.assertEqual(len(periods()),112)
        windows=[(a,b) for name,a,b in periods() if '_' in name]
        self.assertEqual(len(windows),72)
        self.assertTrue(all(b-a==14*DAY_US for a,b in windows))
        self.assertTrue(all(r['exit_us']<START+3*DAY_US for r in predicted))

    def good_reports(self):
        return {name:dict(coverage=1,coverage_by_pair=dict.fromkeys(PAIRS,1),selected=500,dates=200,
                          selected_by_pair=dict.fromkeys(PAIRS,100),stress=dict(mean=.01,advantage=.005),
                          mse=dict(forecast=.1,training_mean=.2)) for name,_,_ in periods()}

    def test_complete_gates_and_no_automatic_live_approval(self):
        reports=self.good_reports()
        uncertainty=dict(valid_replicates=2000,repetitions=2000,stress_mean_interval=[.001,.01],stress_advantage_interval=[.001,.01])
        self.assertTrue(assess(reports,uncertainty)['signal_passed'])
        self.assertFalse(assess(reports,uncertainty)['strategy_approved'])
        for key,value in [('coverage',.9),('selected',1),('dates',1),('stress',dict(mean=-1,advantage=.005))]:
            bad=json.loads(json.dumps(reports));bad['full'][key]=value
            self.assertFalse(assess(bad,uncertainty)['signal_passed'])
        for label in ('years_and_months','activity','forecast_error'):
            bad=json.loads(json.dumps(reports))
            for name in bad:
                if label=='years_and_months': bad[name]['stress']['mean']=-1
                if label=='activity': bad[name]['dates']=0
                if label=='forecast_error': bad[name]['mse']['forecast']=.3
            self.assertFalse(assess(bad,uncertainty)['gates'][label])
        reports.pop('2022')
        with self.assertRaises(ValueError): assess(reports,uncertainty)

    def test_frozen_plan_and_output_guard(self):
        root=Path(__file__).resolve().parents[1]
        self.assertEqual(hashlib.sha256((root/'FORECAST_PLAN.md').read_bytes()).hexdigest(),PLAN_SHA256)
        self.assertEqual(hashlib.sha256((root/'FORECAST_DATA_AMENDMENT.md').read_bytes()).hexdigest(),AMENDMENT_SHA256)
        with tempfile.TemporaryDirectory() as folder:
            with patch('sys.argv',['forecast','--market','nonexistent','--output',folder]), patch('roostoo_bot.forecast_research.verified_payload') as loader:
                with self.assertRaisesRegex(ValueError,'new output'): main()
                loader.assert_not_called()
