#!/usr/bin/env python3
"""Moteur de calcul chauffage eau chaude — Groupe scolaire Albert Camus (Talence).

Chaîne : puissances locaux (+20 %) -> part par radiateur -> puissance requise au régime
projet et équivalent NF EN 442 (75/65/20) -> sélection catalogue (si fourni)
-> dimensionnement réseau du radiateur le plus éloigné vers la source (méthode
« Dimensionnement réseau hydraulique » : Qv max par DN) -> pertes de charge
(Darcy-Weisbach / Colebrook) -> circuit critique et équilibrage.

Usage :
    python3 calc/calc_chauffage.py                       # données par défaut
    python3 calc/calc_chauffage.py --troncons data/troncons_XXX.csv

Aucune dépendance hors bibliothèque standard. Toutes les hypothèses sont dans
data/hypotheses.json ; les relancer après modification ne demande rien d'autre.
"""
import argparse
import csv
import json
import math
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "outputs")

T_NOM = (75.0, 65.0, 20.0)  # conditions normales NF EN 442-2


def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def fnum(v):
    v = (v or "").strip().replace(",", ".")
    return float(v) if v else None


def lmtd(t_in, t_out, t_air):
    """ΔT logarithmique de l'équation caractéristique NF EN 442-2."""
    a, b = t_in - t_air, t_out - t_air
    if a <= 0 or b <= 0:
        raise ValueError("régime incompatible avec la température ambiante")
    return a if abs(a - b) < 1e-9 else (a - b) / math.log(a / b)


def facteur_regime(h, n):
    """P_regime = P50 × facteur (NF EN 442-2 : Φ = Km·ΔT^n)."""
    dt = lmtd(h["t_aller_C"], h["t_retour_C"], h["t_ambiante_C"])
    dt50 = lmtd(*T_NOM)
    return (dt / dt50) ** n


def water_props(t):
    """ρ [kg/m³] et ν [m²/s] de l'eau, interpolation linéaire (tables usuelles)."""
    tab = [(20, 998.2, 1.004e-6), (30, 995.7, 0.801e-6), (40, 992.2, 0.658e-6),
           (50, 988.0, 0.553e-6), (60, 983.2, 0.474e-6), (70, 977.8, 0.413e-6),
           (80, 971.8, 0.365e-6)]
    t = min(max(t, tab[0][0]), tab[-1][0])
    for (t0, r0, n0), (t1, r1, n1) in zip(tab, tab[1:]):
        if t0 <= t <= t1:
            k = (t - t0) / (t1 - t0)
            return r0 + k * (r1 - r0), n0 + k * (n1 - n0)
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


# ---------------------------------------------------------------- étape 1-2
def puissances(h, locaux):
    rows_loc, rads = [], []
    for l in locaux:
        surf = fnum(l["surface_m2"])
        p_rap = fnum(l.get("P_base_W_rapport"))
        if p_rap is not None:
            p_base, origine = p_rap, "RAPPORT EN 12831"
        elif surf is not None:
            p_base, origine = surf * h["ratio_provisoire_W_m2"], "PROVISOIRE ratio W/m² (H-01)"
        else:
            p_base, origine = None, "MANQUANT (surface et puissance inconnues)"
        n = int(l["nb_rad"])
        p_maj = p_base * h["majoration_securite"] if p_base is not None else None
        p_part = p_maj / n if p_maj is not None else None
        rows_loc.append({**l, "P_base_W": r0(p_base), "origine_P": origine,
                         "P_majoree_W": r0(p_maj), "P_par_radiateur_W": r0(p_part)})
        for k in range(n):
            rads.append({"id_radiateur": f"{l['id_local']}-{chr(97 + k)}", "id_local": l["id_local"],
                         "niveau": l["niveau"], "circuit": l["circuit"], "local": l["local"],
                         "type_dessine": l["type_dessine"], "L_dispo_mm": l["L_dispo_mm"],
                         "statut_local": l["statut"], "P_requise_W": p_part, "origine_P": origine})
    return rows_loc, rads


def r0(v):
    return "" if v is None else round(v)


# ---------------------------------------------------------------- étape 3
def selection(h, rads, catalogue):
    for r in rads:
        p = r["P_requise_W"]
        n = h["exposant_n_defaut"]
        f = facteur_regime(h, n)
        r["facteur_regime"] = round(f, 3)
        r["P50_requise_W"] = r0(p / f) if p is not None else ""
        r["P_requise_W"] = r0(p)
        r["modele"], r["P50_cat_W"], r["P_regime_cat_W"], r["statut_selection"] = "", "", "", ""
        if p is None:
            r["statut_selection"] = "FLAG puissance inconnue"
            continue
        if not catalogue:
            r["statut_selection"] = "CATALOGUE REQUIS (P50 requise calculée)"
            continue
        typ = r["type_dessine"]
        l_dispo = fnum(r["L_dispo_mm"]) or 1e9
        candidats = []
        for c in catalogue:
            if typ == "PLINTHE" and c["type"].upper() != "PLINTHE":
                continue
            if typ == "V1500x750" and (c["type"].upper() != "VERTICAL" or fnum(c["hauteur_mm"]) != 1500):
                continue
            nc = fnum(c["n"]) or n
            p_reg = fnum(c["P50_W"]) * facteur_regime(h, nc)
            candidats.append((fnum(c["longueur_mm"]), p_reg, c))
        ok = sorted([x for x in candidats if x[1] >= p and x[0] <= l_dispo], key=lambda x: (x[0], x[1]))
        if ok:
            L, preg, c = ok[0]
            r.update(modele=f"{c['fabricant']} {c['gamme']} {c['modele']}", P50_cat_W=c["P50_W"],
                     P_regime_cat_W=round(preg), statut_selection="OK")
        else:
            best = max(candidats, key=lambda x: x[1], default=None)
            r["statut_selection"] = ("FLAG ne rentre pas dans l'emplacement dessiné : voir alternatives"
                                     if best else "FLAG aucun modèle du type dessiné au catalogue")
            if best:
                r["modele"] = f"(max dispo) {best[2]['fabricant']} {best[2]['modele']} = {round(best[1])} W"
    return rads


# ---------------------------------------------------------------- étape 4
def table_dn(h):
    dt = h["t_aller_C"] - h["t_retour_C"]
    rows = []
    for t in read_csv(os.path.join(DATA, "table_dimensionnement_methode.csv")):
        d = fnum(t["d_int_mm"]) / 1000
        qv = math.pi / 4 * d * d * fnum(t["v_max_ms"]) * 3600
        rows.append({"dn": int(t["dn_mm"]), "designation": t["designation"], "d_int_mm": fnum(t["d_int_mm"]),
                     "v_max": fnum(t["v_max_ms"]), "qv_max_m3h": round(qv, 3),
                     "p_max_kW_projet": round(h["coef_puissance_kWh_m3K"] * qv * dt, 2),
                     "p_dt10_manuscrit": t["p_dt10_manuscrit_kW"], "remarque": t["remarque"]})
    return rows


def dimensionner(h, troncons, rads, dn_tab):
    dt = h["t_aller_C"] - h["t_retour_C"]
    rho, nu = water_props((h["t_aller_C"] + h["t_retour_C"]) / 2)
    p_rad = {r["id_radiateur"]: (r["P_requise_W"] or 0) for r in rads}
    by_id = {t["troncon_id"]: t for t in troncons}
    enfants = defaultdict(list)
    for t in troncons:
        enfants[t["amont_id"]].append(t["troncon_id"])
    flags = []

    def cumul(tid):  # du plus éloigné vers la source (post-ordre)
        t = by_id[tid]
        p = 0.0
        for rid in [x.strip() for x in t.get("radiateurs", "").split(",") if x.strip()]:
            if rid not in p_rad:
                flags.append(f"Tronçon {tid} : radiateur {rid} absent de l'inventaire")
            p += p_rad.get(rid, 0)
        for c in enfants[tid]:
            p += cumul(c)
        t["P_cumul_W"] = p
        return p

    for t in troncons:
        if t["amont_id"] == "SOURCE":
            cumul(t["troncon_id"])

    for t in troncons:
        p_kw = t["P_cumul_W"] / 1000
        qv = p_kw / (h["coef_puissance_kWh_m3K"] * dt)
        impose = fnum(t.get("dn_impose"))
        choix = [d for d in dn_tab if d["dn"] >= h["dn_min_raccordement"] and d["qv_max_m3h"] >= qv]
        if impose:
            choix = [d for d in dn_tab if d["dn"] == int(impose)]
        if not choix:
            flags.append(f"Tronçon {t['troncon_id']} : débit {qv:.2f} m³/h hors tableau")
            continue
        d = choix[0]
        di = d["d_int_mm"] / 1000
        v = qv / 3600 / (math.pi / 4 * di * di)
        re = v * di / nu
        lam = colebrook(re, h["rugosite_mm"] / 1000 / di) if v > 0 else 0
        j = lam / di * rho * v * v / 2
        L = fnum(t["longueur_m"]) or 0
        dp_lin = j * L
        zeta = fnum(t.get("zeta_total"))
        dp_sing = zeta * rho * v * v / 2 if zeta is not None else dp_lin * h["forfait_singularites_pct"] / 100
        dp = (dp_lin + dp_sing) * h["coef_aller_retour"]
        t.update(DN=d["dn"], designation=d["designation"], P_cumul_kW=round(p_kw, 2), Qv_m3h=round(qv, 3),
                 V_ms=round(v, 2), V_max_ms=d["v_max"], Re=round(re), J_Pa_m=round(j, 1),
                 dP_lin_Pa=round(dp_lin), dP_sing_Pa=round(dp_sing), dP_AR_Pa=round(dp),
                 alerte="J > seuil H-10" if j > h["J_alerte_Pa_m"] else "")
        if impose and qv > d["qv_max_m3h"]:
            t["alerte"] = (t["alerte"] + " DN imposé sous-dimensionné").strip()

    # chemins source -> radiateur, circuit critique
    chemins = []
    for t in troncons:
        rids = [x.strip() for x in t.get("radiateurs", "").split(",") if x.strip()]
        for rid in rids:
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


def synthese_circuits(h, rads, dn_tab):
    dt = h["t_aller_C"] - h["t_retour_C"]
    tot = defaultdict(lambda: [0.0, 0, 0])
    for r in rads:
        c = r["circuit"]
        tot[c][1] += 1
        if r["P_requise_W"] == "":
            tot[c][2] += 1
        else:
            tot[c][0] += r["P_requise_W"]
    rows = []
    for c, (p, n, nmiss) in sorted(tot.items()):
        qv = p / 1000 / (h["coef_puissance_kWh_m3K"] * dt)
        d = next((d for d in dn_tab if d["qv_max_m3h"] >= qv), None)
        rows.append({"circuit": c, "nb_radiateurs": n, "nb_sans_puissance": nmiss, "P_kW": round(p / 1000, 2),
                     "Qv_m3h": round(qv, 2), "DN_depart_mini": d["dn"] if d else "hors tableau",
                     "designation": d["designation"] if d else ""})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--locaux", default=os.path.join(DATA, "inventaire_locaux_radiateurs_PROVISOIRE.csv"))
    ap.add_argument("--catalogue", default=os.path.join(DATA, "catalogue_radiateurs.csv"))
    ap.add_argument("--troncons", default=os.path.join(DATA, "troncons_R1_ELEM_ESQUISSE.csv"))
    ap.add_argument("--hyp", default=os.path.join(DATA, "hypotheses.json"))
    a = ap.parse_args()
    h = json.load(open(a.hyp, encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)

    locaux_out, rads = puissances(h, read_csv(a.locaux))
    catalogue = read_csv(a.catalogue) if os.path.exists(a.catalogue) else []
    rads = selection(h, rads, catalogue)
    dn_tab = table_dn(h)

    write_csv(os.path.join(OUT, "01_locaux_puissances.csv"), locaux_out,
              ["id_local", "niveau", "circuit", "local", "code_archi", "surface_m2", "nb_rad", "origine_P",
               "P_base_W", "P_majoree_W", "P_par_radiateur_W", "statut", "remarque"])
    write_csv(os.path.join(OUT, "02_radiateurs_selection.csv"), rads,
              ["id_radiateur", "id_local", "niveau", "circuit", "local", "type_dessine", "L_dispo_mm",
               "P_requise_W", "facteur_regime", "P50_requise_W", "modele", "P50_cat_W", "P_regime_cat_W",
               "statut_selection", "statut_local", "origine_P"])
    write_csv(os.path.join(OUT, "03_table_DN_regime_projet.csv"), dn_tab, list(dn_tab[0].keys()))
    write_csv(os.path.join(OUT, "04_synthese_circuits.csv"), synthese_circuits(h, rads, dn_tab),
              ["circuit", "nb_radiateurs", "nb_sans_puissance", "P_kW", "Qv_m3h", "DN_depart_mini", "designation"])

    if os.path.exists(a.troncons):
        tr, chemins, flags = dimensionner(h, read_csv(a.troncons), rads, dn_tab)
        write_csv(os.path.join(OUT, "05_troncons_dimensionnement.csv"), tr,
                  ["circuit", "troncon_id", "amont_id", "longueur_m", "radiateurs", "P_cumul_kW", "Qv_m3h", "DN",
                   "designation", "V_ms", "V_max_ms", "Re", "J_Pa_m", "dP_lin_Pa", "dP_sing_Pa", "dP_AR_Pa", "alerte"])
        write_csv(os.path.join(OUT, "06_chemins_circuit_critique.csv"), chemins,
                  ["circuit", "id_radiateur", "critique", "longueur_aller_m", "dP_chemin_Pa", "exces_a_laminer_Pa",
                   "HMT_circuit_mCE", "troncons"])
        for f in flags:
            print("FLAG:", f)
    print("Facteur régime (n=%.2f) : %.3f" % (h["exposant_n_defaut"], facteur_regime(h, h["exposant_n_defaut"])))
    print("Sorties écrites dans", OUT)


if __name__ == "__main__":
    main()
