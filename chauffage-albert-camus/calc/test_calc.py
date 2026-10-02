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

    def test_cuivre_et_vmax(self):
        tab = c.table_dn(H)
        cu = c.table_cuivre(H, tab)
        self.assertAlmostEqual(c.vmax_interp(tab, 12.0), 0.32)  # palier DN15
        self.assertEqual(c.choisir(cu, c.qv_m3h(H, 2050))["designation"], "Cu 16x1")

    def test_repere_facade(self):
        # façade ouest au RDC et au R+1 : x ≈ 0 dans le repère commun
        rdc = {"tuile": "t1", "px": "175", "py": "415"}
        r1 = {"tuile": "c1", "px": "110", "py": "228"}
        self.assertLess(abs(c.position_m(H, rdc)[0]), 0.3)
        self.assertLess(abs(c.position_m(H, r1)[0]), 0.3)

    def test_couplage_R1_repli_meme_circuit(self):
        rads = [{"id_radiateur": "A", "niveau": "RDC", "circuit": "PERI", "x_m": 0, "y_m": 0},
                {"id_radiateur": "B", "niveau": "RDC", "circuit": "ELEM", "x_m": 5, "y_m": 0},
                {"id_radiateur": "C", "niveau": "R+1", "circuit": "ELEM", "x_m": 2, "y_m": 0},
                {"id_radiateur": "D", "niveau": "R+1", "circuit": "ELEM", "x_m": 0.5, "y_m": 0}]
        out = {r["id_radiateur"]: r for r in c.couplage_R1(H, rads)}
        self.assertEqual(out["C"]["parent_RDC"], "B")          # pas d'aplomb -> même circuit
        self.assertTrue(out["C"]["statut_aplomb"].startswith("FLAG"))
        self.assertEqual(out["D"]["parent_RDC"], "A")          # aplomb ≤ 1 m, quel que soit le circuit
        self.assertTrue(out["D"]["statut_aplomb"].startswith("OK"))

    def test_boucle_detectee(self):
        tr = [{"circuit": "X", "troncon_id": "S1", "amont_id": "SOURCE", "longueur_m": "1", "radiateurs": ""},
              {"circuit": "X", "troncon_id": "S2", "amont_id": "S3", "longueur_m": "1", "radiateurs": ""},
              {"circuit": "X", "troncon_id": "S3", "amont_id": "S2", "longueur_m": "1", "radiateurs": ""}]
        tab = c.table_dn(H)
        with self.assertRaisesRegex(ValueError, "non reliés"):
            c.dimensionner(H, tr, [], tab, c.table_cuivre(H, tab))


if __name__ == "__main__":
    unittest.main()
