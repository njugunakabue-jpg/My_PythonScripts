import os
import unittest
import importlib.util

try:
    import pandas as pd
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


@unittest.skipIf(pd is None, "pandas not installed; skipping compute tests")
class ComputeTests(unittest.TestCase):
    def test_simple_payouts_and_bonuses(self):
        m = load_app_module()

        # create dummy instance without running __init__
        inst = object.__new__(m.BigBoySkinsApp)

        # attach minimal attributes used by the method
        inst.use_net_scores = DummyBool(False)
        inst.stroke_index_vars = [DummyVar(str(i + 1)) for i in range(m.HOLES)]
        inst.carryover_var = DummyBool(True)
        inst.per_skin_var = DummyVar("1")
        inst.total_purse_var = DummyVar("")
        inst.bonus_enabled_var = DummyBool(True)
        inst.split_ties = DummyBool(False)

        # Build a small DataFrame with two players
        pars = [4] * m.HOLES
        rows = []
        # Player A: all pars
        pa = {f'H{i+1}': 4 for i in range(m.HOLES)}
        pa.update({'Name': 'Alice', 'Included': True, 'Handicap': 0})
        rows.append(pa)
        # Player B: birdie on hole 1, pars elsewhere
        pb = {f'H{i+1}': 4 for i in range(m.HOLES)}
        pb['H1'] = 3
        pb.update({'Name': 'Bob', 'Included': True, 'Handicap': 0})
        rows.append(pb)

        df = pd.DataFrame(rows)

        res = inst._compute_skins_and_payouts(pars, df)

        self.assertIn('payout_map_units', res)
        units = res['payout_map_units']
        # Bob should receive at least the birdie bonus (1 unit)
        self.assertGreaterEqual(units.get('Bob', 0), 1)


if __name__ == '__main__':
    unittest.main()
