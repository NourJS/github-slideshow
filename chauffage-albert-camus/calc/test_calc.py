"""Tests unitaires du moteur : python3 -m unittest calc/test_calc.py"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import calc_chauffage as c  # noqa: E402

H = json.load(open(os.path.join(c.DATA, "hypotheses.json"), encoding="utf-8"))


class TestCalc(unittest.TestCase):
    def test_lmtd_nominal_en442(self):
        self.assertAlmostEqual(c.lmtd(75, 65, 20), 49.83, places=2)

    def test_facteur_nominal_egal_1(self):
        h = dict(H, t_aller_C=75, t_retour_C=65, t_ambiante_C=20)
        self.assertAlmostEqual(c.facteur_regime(h, 1.3), 1.0, places=6)

    def test_table_methode_retrouvee(self):
        # la colonne ΔT=20 °C imprimée doit être retrouvée à 1 % près
        h = dict(H, t_aller_C=70, t_retour_C=50)
        dn = {d["dn"]: d["p_max_kW_projet"] for d in c.table_dn(h)}
        self.assertAlmostEqual(dn[15], 5.78, delta=0.06)
        self.assertAlmostEqual(dn[80], 446.24, delta=4.5)

    def test_selection_dn(self):
        h = dict(H, t_aller_C=55, t_retour_C=45)
        tab = c.table_dn(h)
        qv = 3.71 / (1.163 * 10)
        self.assertEqual(next(d["dn"] for d in tab if d["qv_max_m3h"] >= qv), 20)

    def test_colebrook(self):
        self.assertAlmostEqual(c.colebrook(1e5, 1e-4), 0.0185, delta=0.0005)
        self.assertAlmostEqual(c.colebrook(1000, 1e-4), 0.064, places=6)


if __name__ == "__main__":
    unittest.main()
