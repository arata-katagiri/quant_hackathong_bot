import unittest

from roostoo_bot.activity_audit import DAY_US, event_calendar, portfolio_windows, stamp, summarize_windows


class ActivityAuditTests(unittest.TestCase):
    def event(self, entry, exit, selected=True):
        return dict(entry_us=entry, exit_us=exit, selected=selected)

    def test_exit_on_another_date_and_duplicate_events(self):
        first=stamp('2024-01-01')
        rows=[self.event(first+1, first+DAY_US+1)]*3
        counts=event_calendar(rows, first, first+14*DAY_US)
        self.assertEqual(counts['selected_observations'],3)
        self.assertEqual(counts['utc']['entry_dates'],1)
        self.assertEqual(counts['utc']['unnetted_entry_exit_dates'],2)
        self.assertFalse(counts['executable_portfolio'])
        self.assertFalse(counts['qualification_verified'])

    def test_timezone_can_change_calendar_dates(self):
        first=stamp('2024-01-01')
        rows=[self.event(first+15*DAY_US//24,first+17*DAY_US//24)]
        counts=event_calendar(rows,first,first+14*DAY_US)
        self.assertEqual(counts['utc']['unnetted_entry_exit_dates'],1)
        self.assertEqual(counts['hkt']['unnetted_entry_exit_dates'],2)

    def test_only_selected_self_contained_labels_count(self):
        first=stamp('2024-01-01');last=first+14*DAY_US
        rows=[self.event(first-1,first+1),self.event(first+1,last),self.event(first+1,first+2,False)]
        self.assertEqual(event_calendar(rows,first,last)['selected_observations'],0)
        with self.assertRaises(ValueError): event_calendar([self.event(first,first)],first,last)
        with self.assertRaises(ValueError): event_calendar([],last,first)

    def row(self, **overrides):
        values=dict(strategy='candidate',cost='base',start_us=0,end_us=14*DAY_US-1,period='a',
                    total_return=.01,max_drawdown=.02,active_days_utc=8,active_days_hkt=7,
                    turnover=2,fees=200,trades=16)
        return {**values,**overrides}

    def test_duplicate_period_aliases_collapse_without_hiding_conflicts(self):
        rows=portfolio_windows([self.row(),self.row(period='b'),self.row(strategy='control'),self.row(end_us=DAY_US-1)],{'candidate'})
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['aliases'],['a','b'])
        with self.assertRaises(ValueError): portfolio_windows([self.row(),self.row(period='b',total_return=.02)],{'candidate'})

    def test_joint_profit_activity_and_drawdown_counts(self):
        rows=[self.row(),self.row(total_return=-.1),self.row(active_days_utc=3),self.row(max_drawdown=.09)]
        result=summarize_windows(rows)[0]
        self.assertEqual(result['windows'],4)
        self.assertEqual(result['positive'],3)
        self.assertEqual(result['utc']['activity'],3)
        self.assertEqual(result['utc']['positive_and_active'],2)
        self.assertEqual(result['utc']['positive_active_and_drawdown'],1)
        self.assertEqual(result['hkt']['activity'],0)
