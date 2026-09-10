import os
import tempfile
import unittest
import importlib.util
import types

try:
    import pandas as pd
    from openpyxl import load_workbook
except Exception:
    pd = None


def load_app_module():
    repo_root = os.path.dirname(os.path.dirname(__file__))
    module_path = os.path.join(repo_root, 'Golf_Calculator_copilot_v12.py')
    spec = importlib.util.spec_from_file_location('golf_app', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DummyVar:
    def __init__(self, value):
        self._v = value

    def get(self):
        return self._v


class DummyBool(DummyVar):
    pass


@unittest.skipIf(pd is None or 'openpyxl' not in globals(), "pandas/openpyxl not installed; skipping export tests")
class ExportSummaryTests(unittest.TestCase):
    def test_per_skin_rounding_and_format(self):
        m = load_app_module()

        inst = object.__new__(m.BigBoySkinsApp)

        # Minimal attributes used by _compute_skins_and_payouts and export_to_excel
        inst.use_net_scores = DummyBool(False)
        inst.stroke_index_vars = [DummyVar(str(i + 1)) for i in range(m.HOLES)]
        inst.carryover_var = DummyBool(True)
        inst.per_skin_var = DummyVar("1.234567")
        inst.total_purse_var = DummyVar("")
        inst.bonus_enabled_var = DummyBool(True)
        inst.split_ties = DummyBool(False)
        inst.course_var = DummyVar("UnitTest Course")
        inst.date_var = DummyVar("")
        inst.buy_in_var = DummyVar("0")

        # collect_data should return pars and a list of player dicts
        def collect_data(self):
            pars = [4] * m.HOLES
            players = [
                {f'H{i+1}': '' for i in range(m.HOLES)} | {'Name': 'Alice', 'Included': True, 'Handicap': 0},
                {f'H{i+1}': '' for i in range(m.HOLES)} | {'Name': 'Bob', 'Included': True, 'Handicap': 0}
            ]
            return pars, players

        inst.collect_data = types.MethodType(collect_data, inst)

        # Patch dialogs and messages in the module to avoid UI interaction
        m.filedialog.asksaveasfilename = lambda **kw: tempfile.mktemp(suffix='.xlsx')
        m.messagebox.showinfo = lambda *a, **kw: None
        m.messagebox.showwarning = lambda *a, **kw: None
        m.messagebox.showerror = lambda *a, **kw: None

        # Call export_to_excel (should save to the temp file path)
        outpath = m.filedialog.asksaveasfilename()
        # ensure the path is used by export_to_excel by patching asksaveasfilename to return same path
        m.filedialog.asksaveasfilename = lambda **kw: outpath

        # Run export
        inst._compute_skins_and_payouts  # ensure method exists
        inst.export_to_excel = types.MethodType(m.BigBoySkinsApp.export_to_excel, inst)
        inst.export_to_excel()

        # Load the workbook and inspect Export Summary
        wb = load_workbook(outpath, data_only=True)
        self.assertIn('Export Summary', wb.sheetnames)
        summary = wb['Export Summary']

        per_skin_val = None
        per_skin_cell = None
        for row in summary.iter_rows(min_row=1, max_col=2):
            k = row[0].value
            vcell = row[1]
            if k is None:
                continue
            if 'per-skin' in str(k).strip().lower():
                per_skin_val = vcell.value
                per_skin_cell = vcell
                break

        self.assertIsNotNone(per_skin_val, 'Per-skin entry not found in Export Summary')
        # numeric value should be rounded to 2 decimals
        self.assertAlmostEqual(float(per_skin_val), round(1.234567, 2), places=2)
        # and Excel number format should be currency with two decimals
        self.assertTrue(hasattr(per_skin_cell, 'number_format'))
        self.assertIn('0.00', per_skin_cell.number_format)


if __name__ == '__main__':
    unittest.main()
