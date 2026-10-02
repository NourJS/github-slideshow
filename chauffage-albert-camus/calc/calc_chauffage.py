#!/usr/bin/env python3
"""Moteur de calcul chauffage eau chaude — Groupe scolaire Albert Camus (Talence).

Chaîne : bilan émetteurs EN 12831 par local -> ×1,20 -> part par radiateur -> puissance requise
au régime projet et équivalent NF EN 442 -> sélection catalogue (si fourni) -> raccordement des
radiateurs R+1 sur le radiateur RDC à l'aplomb (réservation dans la dalle) -> raccordements
cuivre -> départs acier (méthode « Dimensionnement réseau hydraulique ») -> réseau détaillé
(si tronçons exportés de Revit) -> modèle JSON pour le dessin Revit.

Usage :
    python3 calc/calc_chauffage.py
    python3 calc/calc_chauffage.py --troncons data/troncons_<circuit>.csv

Bibliothèque standard uniquement. Les hypothèses sont dans data/hypotheses.json.
"""
import argparse
import csv
import json
import math
import os
from collections import defaultdict
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "outputs")
MODEL = os.path.join(ROOT, "model", "modele_chauffage_albert_camus.json")

T_NOM = (75.0, 65.0, 20.0)  # conditions normales NF EN 442-2

# Rendus PDF ayant servi au relevé des positions : (x0_pt, y0_pt, dpi, plan)
TUILES = {"t1": (1500, 560, 150, "RDC"), "t2": (2300, 560, 150, "RDC"), "t3": (3100, 560, 150, "RDC"),
          "t4": (3900, 560, 150, "RDC"), "t5": (1500, 1220, 150, "RDC"), "t6": (2300, 1220, 150, "RDC"),
          "t7": (3100, 1220, 150, "RDC"), "c1": (330, 680, 220, "R+1"), "c2": (330, 1280, 220, "R+1"),
          # coordonnées vectorielles directes (points PDF) : CVPS_01 (RDC) et CVPS_02 (R+1)
          "pdf0": (0, 0, 72, "RDC"), "pdf1": (0, 0, 72, "R+1")}


def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def fnum(v):
    v = ("" if v is None else str(v)).strip().replace(",", ".")
    return float(v) if v else None


def r0(v):
    return "" if v is None else round(v)


def lmtd(t_in, t_out, t_air):
    """ΔT logarithmique de l'équation caractéristique NF EN 442-2."""
    a, b = t_in - t_air, t_out - t_air
    if a <= 0 or b <= 0:
        raise ValueError("régime incompatible avec la température ambiante")
    return a if abs(a - b) < 1e-9 else (a - b) / math.log(a / b)


def facteur_regime(h, n, t_air=None):
    """P_regime = P50 × facteur (NF EN 442-2 : Φ = Km·ΔT^n)."""
    t_air = h["t_ambiante_C"] if t_air is None else t_air
    return (lmtd(h["t_aller_C"], h["t_retour_C"], t_air) / lmtd(*T_NOM)) ** n


def water_props(t):
    """ρ [kg/m³] et ν [m²/s] de l'eau, interpolation linéaire (tables usuelles)."""
    tab = [(20, 998.2, 1.004e-6), (30, 995.7, 0.801e-6), (40, 992.2, 0.658e-6),
           (50, 988.0, 0.553e-6), (60, 983.2, 0.474e-6), (70, 977.8, 0.413e-6),
           (80, 971.8, 0.365e-6)]
    t = min(max(t, tab[0][0]), tab[-1][0])
    for (t0, r_0, n0), (t1, r_1, n1) in zip(tab, tab[1:]):
        if t0 <= t <= t1:
            k = (t - t0) / (t1 - t0)
            return r_0 + k * (r_1 - r_0), n0 + k * (n1 - n0)
    return tab[-1][1], tab[-1][2]


def colebrook(re, rel_rough):
    if re < 2300:
        return 64.0 / max(re, 1e-9)
    lam = 0.25 / (math.log10(rel_rough / 3.7 + 5.74 / re ** 0.9)) ** 2  # Swamee-Jain (amorce)
    for _ in range(30):
        lam_new = (-2.0 * math.log10(rel_rough / 3.7 + 2.51 / (re * math.sqrt(lam)))) ** -2
        if abs(lam_new - lam) < 1e-10:
            break
        lam = lam_new
    return lam


def qv_m3h(h, p_w):
    return p_w / 1000 / (h["coef_puissance_kWh_m3K"] * (h["t_aller_C"] - h["t_retour_C"]))


# ---------------------------------------------------------------- tables de diamètres
def table_dn(h):
    """Acier : tableau de la note de méthode, Qv_max = π/4·Øint²·V_max."""
    dt = h["t_aller_C"] - h["t_retour_C"]
    rows = []
    for t in read_csv(os.path.join(DATA, "table_dimensionnement_methode.csv")):
        d = fnum(t["d_int_mm"]) / 1000
        qv = math.pi / 4 * d * d * fnum(t["v_max_ms"]) * 3600
        rows.append({"materiau": "acier", "dn": int(t["dn_mm"]), "designation": t["designation"],
                     "d_int_mm": fnum(t["d_int_mm"]), "v_max": fnum(t["v_max_ms"]), "qv_max_m3h": round(qv, 3),
                     "p_max_kW_projet": round(h["coef_puissance_kWh_m3K"] * qv * dt, 2),
                     "p_dt10_manuscrit": t["p_dt10_manuscrit_kW"], "remarque": t["remarque"]})
    return rows


def vmax_interp(dn_tab, d_int):
    """H-15 : V_max transposée au cuivre par interpolation sur Øint (palier DN15 en dessous)."""
    pts = [(d["d_int_mm"], d["v_max"]) for d in dn_tab]
    if d_int <= pts[0][0]:
        return pts[0][1]
    for (d0, v0), (d1, v1) in zip(pts, pts[1:]):
        if d0 <= d_int <= d1:
            return v0 + (v1 - v0) * (d_int - d0) / (d1 - d0)
    return pts[-1][1]


def table_cuivre(h, dn_tab):
    dt = h["t_aller_C"] - h["t_retour_C"]
    rows = []
    for t in read_csv(os.path.join(DATA, "table_cuivre_NF_EN_1057.csv")):
        di = fnum(t["d_int_mm"])
        v = vmax_interp(dn_tab, di)
        qv = math.pi / 4 * (di / 1000) ** 2 * v * 3600
        rows.append({"materiau": "cuivre", "dn": int(fnum(t["d_ext_mm"])), "designation": t["designation"],
                     "d_int_mm": di, "v_max": round(v, 3), "qv_max_m3h": round(qv, 3),
                     "p_max_kW_projet": round(h["coef_puissance_kWh_m3K"] * qv * dt, 2)})
    return rows


def choisir(tab, qv, dn_min=0):
    return next((d for d in tab if d["dn"] >= dn_min and d["qv_max_m3h"] >= qv), None)


# ---------------------------------------------------------------- géométrie
def position_m(h, rad):
    x0, y0, dpi, plan = TUILES[rad["tuile"]]
    x = x0 + fnum(rad["px"]) * 72 / dpi
    y = y0 + fnum(rad["py"]) * 72 / dpi
    if plan == "R+1":
        dx, dy = h["repere"]["recalage_R1_vers_RDC_pt"]
        x, y = x + dx, y + dy
    ox, oy = h["repere"]["origine_pdf_pt"]
    s = h["repere"]["echelle_m_par_pt"]
    return round((x - ox) * s, 2), round((oy - y) * s, 2)


# ---------------------------------------------------------------- étapes 1-2
def puissances(h, locaux, rads):
    col = h["base_puissance_rapport"]
    par_local = defaultdict(list)
    for r in rads:
        par_local[r["id_local"]].append(r)
    loc_by_id = {l["id_local"]: l for l in locaux}
    for l in locaux:
        n = len(par_local[l["id_local"]])
        p_base = fnum(l[col])
        p_maj = p_base * h["majoration_securite"]
        l.update(nb_rad=n, P_base_W=r0(p_base), base=col, P_majoree_W=r0(p_maj),
                 P_majoree_sur_deperd_W=r0(fnum(l["deperd_total_W"]) * h["majoration_securite"]),
                 P_par_radiateur_W=r0(p_maj / n) if n else "",
                 statut="OK" if n else "FLAG local du bilan sans radiateur dessiné")
    for r in rads:
        l = loc_by_id.get(r["id_local"])
        if l is None:
            r.update(P_part_W=None, local="(absent du bilan)", ti_C=h["t_ambiante_C"],
                     origine_P="FLAG radiateur sans local au bilan")
        else:
            r.update(P_part_W=fnum(l["P_majoree_W"]) / l["nb_rad"], local=l["designation"],
                     ti_C=fnum(l["ti_C"]), origine_P=f"bilan émetteurs ({col}) × {h['majoration_securite']}")
        r["x_m"], r["y_m"] = position_m(h, r)
    return locaux, rads


# ---------------------------------------------------------------- étape 3
def selection(h, rads, catalogue):
    for r in rads:
        p = r["P_part_W"]
        n = h["exposant_n_defaut"]
        f = facteur_regime(h, n, r["ti_C"])
        r.update(facteur_regime=round(f, 3), P50_requise_W=r0(p / f) if p else "", modele="", P50_cat_W="",
                 P_regime_cat_W="")
        if p is None:
            r["statut_selection"] = "FLAG puissance inconnue"
            continue
        if not catalogue:
            r["statut_selection"] = "CATALOGUE REQUIS (P50 requise calculée)"
            continue
        typ, l_dispo = r["type_dessine"], fnum(r["L_dispo_mm"]) or 1e9
        candidats = []
        for c in catalogue:
            if typ == "PLINTHE" and c["type"].upper() != "PLINTHE":
                continue
            if typ == "V1500x750" and (c["type"].upper() != "VERTICAL" or fnum(c["hauteur_mm"]) != 1500):
                continue
            p_reg = fnum(c["P50_W"]) * facteur_regime(h, fnum(c["n"]) or n, r["ti_C"])
            candidats.append((fnum(c["longueur_mm"]), p_reg, c))
        ok = sorted([x for x in candidats if x[1] >= p and x[0] <= l_dispo], key=lambda x: (x[0], x[1]))
        if ok:
            _, preg, c = ok[0]
            r.update(modele=f"{c['fabricant']} {c['gamme']} {c['modele']}", P50_cat_W=c["P50_W"],
                     P_regime_cat_W=round(preg), statut_selection="OK")
        else:
            best = max(candidats, key=lambda x: x[1], default=None)
            r["statut_selection"] = ("FLAG ne rentre pas dans l'emplacement dessiné : voir alternatives"
                                     if best else "FLAG aucun modèle du type dessiné au catalogue")
            if best:
                r["modele"] = f"(max dispo) {best[2]['fabricant']} {best[2]['modele']} = {round(best[1])} W"
    return rads


# ---------------------------------------------------------------- étape 4 : R+1 sur radiateur RDC à l'aplomb
def couplage_R1(h, rads):
    rdc = [r for r in rads if r["niveau"] == "RDC"]
    tol = h["tolerance_aplomb_m"]
    for r in rads:
        r.update(parent_RDC="", ecart_aplomb_m="", enfants_R1=[], statut_aplomb="")
    for r in rads:
        if r["niveau"] != "R+1":
            continue
        def dist(q):
            return math.hypot(q["x_m"] - r["x_m"], q["y_m"] - r["y_m"])

        best = min(rdc, key=dist)
        if dist(best) > tol:  # pas d'aplomb : repli sur le radiateur du même circuit DCE le plus proche
            best = min([q for q in rdc if q["circuit"] == r["circuit"]] or rdc, key=dist)
        d = dist(best)
        r["parent_RDC"], r["ecart_aplomb_m"] = best["id_radiateur"], round(d, 2)
        best["enfants_R1"].append(r["id_radiateur"])
        if d <= tol:
            r["statut_aplomb"] = "OK radiateur RDC à l'aplomb"
        else:
            r["statut_aplomb"] = (f"FLAG aucun radiateur RDC à ≤ {tol} m - proposition provisoire = radiateur RDC "
                                  f"{r['circuit']} le plus proche + {round(d, 1)} m en plafond RDC (à valider)")
        if best["circuit"] != r["circuit"]:
            r["statut_aplomb"] += f" - circuit parent = {best['circuit']}"
    return rads


def raccordements(h, rads, cu_tab):
    """Cuivre apparent : lien vertical R+1 (P propre) et branche RDC (P propre + R+1 raccordés)."""
    by_id = {r["id_radiateur"]: r for r in rads}
    res = []
    for r in rads:
        p_propre = r["P_part_W"] or 0
        if r["niveau"] == "R+1":
            p, nature = p_propre, "lien vertical R+1 depuis radiateur RDC (traversée de dalle)"
            L = h["hauteur_etage_m"] + (r["ecart_aplomb_m"] or 0)
        else:
            p = p_propre + sum(by_id[c]["P_part_W"] or 0 for c in r["enfants_R1"])
            nature = "branche RDC piquée sur distribution acier" + (" + R+1 raccordé(s)" if r["enfants_R1"] else "")
            L = None  # connue après tracé Revit
        qv = qv_m3h(h, p)
        d = choisir(cu_tab, qv)
        r["raccord_P_W"], r["raccord_Qv_m3h"] = round(p), round(qv, 3)
        r["raccord_cuivre"] = d["designation"] if d else "hors table cuivre → acier"
        r["raccord_V_ms"] = round(qv / 3600 / (math.pi / 4 * (d["d_int_mm"] / 1000) ** 2), 2) if d and qv else ""
        r["raccord_nature"], r["raccord_longueur_m"] = nature, (round(L, 2) if L else "")
        res.append(r)
    return res


def reservations(h, rads):
    out = []
    for i, r in enumerate([r for r in rads if r["niveau"] == "R+1"], 1):
        rs = h["reservation_dalle"]
        out.append({"id": f"RES-R1-{i:02d}", "radiateur_R1": r["id_radiateur"], "radiateur_RDC": r["parent_RDC"],
                    "x_m": r["x_m"], "y_m": r["y_m"], "niveau_dalle": "plancher haut RDC / bas R+1",
                    "dimensions_mm": f"{rs['largeur_mm']}x{rs['profondeur_mm']}", "tubes": f"2 × {r['raccord_cuivre']}",
                    "calfeutrement": rs["calfeutrement"],
                    "statut": "OK" if r["statut_aplomb"].startswith("OK") else "A_VALIDER (pas d'aplomb RDC)"})
    return out


# ---------------------------------------------------------------- étape 5 : départs et réseau détaillé
def synthese_circuits(h, rads, dn_tab):
    by_id = {r["id_radiateur"]: r for r in rads}
    tot = defaultdict(lambda: [0.0, 0, 0])
    for r in rads:
        # un radiateur R+1 est porté par le circuit de son radiateur RDC parent
        c = by_id[r["parent_RDC"]]["circuit"] if r["niveau"] == "R+1" and r["parent_RDC"] else r["circuit"]
        tot[c][1] += 1
        if r["P_part_W"] is None:
            tot[c][2] += 1
        else:
            tot[c][0] += r["P_part_W"]
    rows = []
    for c, (p, n, nmiss) in sorted(tot.items()):
        qv = qv_m3h(h, p)
        d = choisir(dn_tab, qv)
        rows.append({"circuit": c, "nb_radiateurs": n, "nb_sans_puissance": nmiss, "P_kW": round(p / 1000, 2),
                     "Qv_m3h": round(qv, 2), "DN_depart_mini": d["dn"] if d else "hors tableau",
                     "designation": d["designation"] if d else ""})
    peri = [x for x in rows if x["circuit"].startswith("PERI")]
    if len(peri) > 1:  # départ Admin/Péri réel = PERI + sous-réseau restauration
        p = sum(x["P_kW"] for x in peri) * 1000
        d = choisir(dn_tab, qv_m3h(h, p))
        rows.append({"circuit": "PERI (départ total)", "nb_radiateurs": sum(x["nb_radiateurs"] for x in peri),
                     "nb_sans_puissance": sum(x["nb_sans_puissance"] for x in peri), "P_kW": round(p / 1000, 2),
                     "Qv_m3h": round(qv_m3h(h, p), 2), "DN_depart_mini": d["dn"], "designation": d["designation"]})
    return rows


def dimensionner(h, troncons, rads, dn_tab, cu_tab):
    """Tronçons exportés de Revit : circuit;troncon_id;amont_id;longueur_m;zeta_total;radiateurs;dn_impose;materiau"""
    rho, nu = water_props((h["t_aller_C"] + h["t_retour_C"]) / 2)
    p_rad = {r["id_radiateur"]: (r["P_part_W"] or 0) for r in rads}
    by_id = {t["troncon_id"]: t for t in troncons}
    enfants = defaultdict(list)
    for t in troncons:
        enfants[t["amont_id"]].append(t["troncon_id"])
    flags = []

    def cumul(tid, vus):  # du plus éloigné vers la source (post-ordre)
        if tid in vus:
            raise ValueError(f"boucle détectée au tronçon {tid}")
        vus.add(tid)
        t = by_id[tid]
        p = 0.0
        for rid in [x.strip() for x in t.get("radiateurs", "").split(",") if x.strip()]:
            if rid not in p_rad:
                flags.append(f"Tronçon {tid} : radiateur {rid} absent de l'inventaire")
            p += p_rad.get(rid, 0)
        for c in enfants[tid]:
            p += cumul(c, vus)
        t["P_cumul_W"] = p
        return p

    for t in troncons:
        if t["amont_id"] == "SOURCE":
            cumul(t["troncon_id"], set())
        elif t["amont_id"] not in by_id:
            raise ValueError(f"tronçon {t['troncon_id']} : amont {t['amont_id']} inconnu")
    orphelins = [t["troncon_id"] for t in troncons if "P_cumul_W" not in t]
    if orphelins:
        raise ValueError(f"tronçons non reliés à la source (boucle ou amont manquant) : {orphelins}")

    for t in troncons:
        cuivre = t.get("materiau", "acier").strip().lower() == "cuivre"
        tab = cu_tab if cuivre else dn_tab
        qv = qv_m3h(h, t["P_cumul_W"])
        impose = fnum(t.get("dn_impose"))
        d = next((x for x in tab if x["dn"] == int(impose)), None) if impose else \
            choisir(tab, qv, 0 if cuivre else h["dn_min_raccordement"])
        if not d:
            flags.append(f"Tronçon {t['troncon_id']} : débit {qv:.2f} m³/h hors tableau")
            continue
        di = d["d_int_mm"] / 1000
        v = qv / 3600 / (math.pi / 4 * di * di)
        re = v * di / nu
        eps = h["rugosite_cuivre_mm"] if cuivre else h["rugosite_mm"]
        lam = colebrook(re, eps / 1000 / di) if v > 0 else 0
        j = lam / di * rho * v * v / 2
        L = fnum(t["longueur_m"]) or 0
        dp_lin = j * L
        zeta = fnum(t.get("zeta_total"))
        dp_sing = zeta * rho * v * v / 2 if zeta is not None else dp_lin * h["forfait_singularites_pct"] / 100
        dp = (dp_lin + dp_sing) * h["coef_aller_retour"]
        alerte = "J > seuil H-10" if j > h["J_alerte_Pa_m"] else ""
        if impose and qv > d["qv_max_m3h"]:
            alerte = (alerte + " DN imposé sous-dimensionné").strip()
        t.update(materiau="cuivre" if cuivre else "acier", DN=d["dn"], designation=d["designation"],
                 P_cumul_kW=round(t["P_cumul_W"] / 1000, 2), Qv_m3h=round(qv, 3), V_ms=round(v, 2),
                 V_max_ms=d["v_max"], Re=round(re), J_Pa_m=round(j, 1), dP_lin_Pa=round(dp_lin),
                 dP_sing_Pa=round(dp_sing), dP_AR_Pa=round(dp), alerte=alerte)

    chemins = []
    for t in troncons:
        for rid in [x.strip() for x in t.get("radiateurs", "").split(",") if x.strip()]:
            path, cur = [], t["troncon_id"]
            while cur != "SOURCE":
                path.append(cur)
                cur = by_id[cur]["amont_id"]
            path.reverse()
            dp = sum(by_id[x].get("dP_AR_Pa", 0) for x in path) + h["dp_terminal_kPa"] * 1000
            L = sum(fnum(by_id[x]["longueur_m"]) or 0 for x in path)
            chemins.append({"circuit": t["circuit"], "id_radiateur": rid, "troncons": " > ".join(path),
                            "longueur_aller_m": round(L, 1), "dP_chemin_Pa": round(dp)})
    crit = {}
    for c in chemins:
        if c["circuit"] not in crit or c["dP_chemin_Pa"] > crit[c["circuit"]]["dP_chemin_Pa"]:
            crit[c["circuit"]] = c
    for c in chemins:
        k = crit[c["circuit"]]
        c["critique"] = "OUI" if c is k else ""
        c["exces_a_laminer_Pa"] = k["dP_chemin_Pa"] - c["dP_chemin_Pa"]
        c["HMT_circuit_mCE"] = round(k["dP_chemin_Pa"] / 1000 / h["mCE_kPa"], 2)
    return troncons, chemins, flags


# ---------------------------------------------------------------- modèle JSON
def export_modele(h, locaux, rads, resa, synth, dn_tab, cu_tab, troncons, chemins):
    base = json.load(open(os.path.join(DATA, "modele_base.json"), encoding="utf-8"))
    base["meta"]["genere_le"] = date.today().isoformat()
    base["hypotheses"] = {k: v for k, v in h.items() if not k.startswith("_")}
    base["materiaux"]["distribution_principale"]["diametres"] = dn_tab
    base["materiaux"]["raccordements_apparents"]["diametres"] = cu_tab
    base["locaux"] = [{k: l[k] for k in ("id_local", "niveau", "n_rapport", "code", "designation", "surface_m2",
                                          "ti_C", "deperd_total_W", "puissance_a_installer_W", "base", "P_base_W",
                                          "P_majoree_W", "nb_rad", "P_par_radiateur_W", "statut")} for l in locaux]
    for l in base["locaux"]:
        l["radiateurs"] = [r["id_radiateur"] for r in rads if r["id_local"] == l["id_local"]]
    base["radiateurs"] = [{
        "id": r["id_radiateur"], "niveau": r["niveau"], "circuit_dce": r["circuit"], "id_local": r["id_local"],
        "local": r["local"], "type_dessine": r["type_dessine"], "orientation_plan": r["orientation"],
        "position_m": {"x": r["x_m"], "y": r["y_m"], "z_bas_mm": h["hauteur_bas_radiateur_mm"],
                       "source": f"PDF {r['tuile']} ({r['px']},{r['py']}) ±{h['repere']['precision_m']} m",
                       "a_remplacer_par": "coordonnées DWG/RVT"},
        "L_dispo_mm": fnum(r["L_dispo_mm"]), "P_part_W": r0(r["P_part_W"]) or None,
        "facteur_regime": r["facteur_regime"], "P50_requise_W": r["P50_requise_W"] or None,
        "selection": {"modele": r["modele"], "P50_cat_W": r["P50_cat_W"], "P_regime_cat_W": r["P_regime_cat_W"],
                      "statut": r["statut_selection"]},
        "raccordement": {"nature": r["raccord_nature"], "materiau": "cuivre apparent",
                         "diametre": r["raccord_cuivre"], "P_transitee_W": r["raccord_P_W"],
                         "Qv_m3h": r["raccord_Qv_m3h"], "V_ms": r["raccord_V_ms"],
                         "longueur_m": r["raccord_longueur_m"] or None,
                         "parent_RDC": r["parent_RDC"] or None, "ecart_aplomb_m": r["ecart_aplomb_m"] or None,
                         "enfants_R1": r["enfants_R1"], "statut_aplomb": r["statut_aplomb"] or None},
        "statut": r["statut"], "remarque": r["remarque"]} for r in rads]
    base["reservations_dalle"] = resa
    for d in base["departs"]:
        tot = [x for x in synth if x["circuit"] in (d["id"], d["id"] + " (départ total)")]
        d["calcul"] = tot[-1] if tot else None  # PERI : départ total (PERI + restauration)
    base["reseau"]["troncons"] = troncons
    base["reseau"]["chemins"] = chemins
    os.makedirs(os.path.dirname(MODEL), exist_ok=True)
    with open(MODEL, "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bilan", default=os.path.join(DATA, "bilan_emetteurs_EN12831.csv"))
    ap.add_argument("--radiateurs", default=os.path.join(DATA, "radiateurs_positions_PROVISOIRE.csv"))
    ap.add_argument("--catalogue", default=os.path.join(DATA, "catalogue_radiateurs.csv"))
    ap.add_argument("--troncons", default=None)
    ap.add_argument("--hyp", default=os.path.join(DATA, "hypotheses.json"))
    a = ap.parse_args()
    h = json.load(open(a.hyp, encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)

    locaux, rads = puissances(h, read_csv(a.bilan), read_csv(a.radiateurs))
    catalogue = read_csv(a.catalogue) if os.path.exists(a.catalogue) else []
    rads = selection(h, rads, catalogue)
    dn_tab = table_dn(h)
    cu_tab = table_cuivre(h, dn_tab)
    rads = raccordements(h, couplage_R1(h, rads), cu_tab)
    resa = reservations(h, rads)
    synth = synthese_circuits(h, rads, dn_tab)

    write_csv(os.path.join(OUT, "01_locaux_puissances.csv"), locaux,
              ["id_local", "niveau", "n_rapport", "code", "designation", "surface_m2", "ti_C", "deperd_total_W",
               "puissance_a_installer_W", "base", "P_base_W", "P_majoree_W", "P_majoree_sur_deperd_W", "nb_rad",
               "P_par_radiateur_W", "statut"])
    write_csv(os.path.join(OUT, "02_radiateurs_selection.csv"),
              [{**r, "P_part_W": r0(r["P_part_W"]), "enfants_R1": ",".join(r["enfants_R1"])} for r in rads],
              ["id_radiateur", "niveau", "circuit", "id_local", "local", "type_dessine", "L_dispo_mm", "x_m", "y_m",
               "P_part_W", "facteur_regime", "P50_requise_W", "modele", "P50_cat_W", "P_regime_cat_W",
               "statut_selection", "parent_RDC", "ecart_aplomb_m", "enfants_R1", "statut_aplomb",
               "raccord_nature", "raccord_P_W", "raccord_Qv_m3h", "raccord_cuivre", "raccord_V_ms",
               "raccord_longueur_m", "statut", "remarque"])
    write_csv(os.path.join(OUT, "03_table_DN_regime_projet.csv"), dn_tab + cu_tab,
              ["materiau", "dn", "designation", "d_int_mm", "v_max", "qv_max_m3h", "p_max_kW_projet",
               "p_dt10_manuscrit", "remarque"])
    write_csv(os.path.join(OUT, "04_synthese_circuits.csv"), synth,
              ["circuit", "nb_radiateurs", "nb_sans_puissance", "P_kW", "Qv_m3h", "DN_depart_mini", "designation"])
    write_csv(os.path.join(OUT, "07_reservations_dalle_R1.csv"), resa, list(resa[0].keys()) if resa else ["id"])

    troncons, chemins = [], []
    if a.troncons:
        troncons, chemins, flags = dimensionner(h, read_csv(a.troncons), rads, dn_tab, cu_tab)
        write_csv(os.path.join(OUT, "05_troncons_dimensionnement.csv"), troncons,
                  ["circuit", "troncon_id", "amont_id", "materiau", "longueur_m", "radiateurs", "P_cumul_kW", "Qv_m3h",
                   "DN", "designation", "V_ms", "V_max_ms", "Re", "J_Pa_m", "dP_lin_Pa", "dP_sing_Pa", "dP_AR_Pa",
                   "alerte"])
        write_csv(os.path.join(OUT, "06_chemins_circuit_critique.csv"), chemins,
                  ["circuit", "id_radiateur", "critique", "longueur_aller_m", "dP_chemin_Pa", "exces_a_laminer_Pa",
                   "HMT_circuit_mCE", "troncons"])
        for f in flags:
            print("FLAG:", f)
    export_modele(h, locaux, rads, resa, synth, dn_tab, cu_tab, troncons, chemins)
    print("Facteur régime (n=%.2f, θi=%.0f °C) : %.3f" % (h["exposant_n_defaut"], h["t_ambiante_C"],
                                                          facteur_regime(h, h["exposant_n_defaut"])))
    print("Sorties :", OUT, "| Modèle :", MODEL)


if __name__ == "__main__":
    main()
