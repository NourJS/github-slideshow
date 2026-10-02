#!/usr/bin/env python3
"""Plan RDC annoté : radiateurs (puissance) + diamètres à chaque changement de section.

1. Lit le réseau ALLER du PDF DCE CVPS_01 (calque VIV02_CHA_RES_ECH_A, couleur = circuit) et les
   symboles radiateurs (calque VIV02_CHA_EQT).
2. Reconstitue un arbre par circuit (collecteur -> radiateurs), raccorde les radiateurs, ajoute les
   liens R+1 (règle de la décision D1) et écrit data/troncons_RDC_DCE.csv.
3. Dimensionne avec calc/calc_chauffage.py (méthode F5 pour l'acier, NF EN 1057 pour le cuivre).
4. Annote le plan : étiquette par radiateur (id + puissance) et étiquette de diamètre à chaque
   changement de section, puis écrit outputs/CVPS_01_RDC_radiateurs_diametres.pdf.

Usage : python3 tools/plan_rdc_annote.py --pdf <CVPS_01.pdf>
Dépendance : PyMuPDF (pip install pymupdf). Le moteur de calcul reste en bibliothèque standard.
"""
import argparse
import collections
import csv
import json
import math
import os
import sys

import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calc"))
import calc_chauffage as cc  # noqa: E402

PT_M = 0.035278  # 1 pt PDF à l'échelle 1/100, en m
COULEURS = {"MAT": (255, 0, 0), "ELEM": (205, 105, 40), "PERI": (153, 27, 30), "RESTAU": (242, 113, 114),
            "CTA": (19, 103, 52), "PRIM": (255, 0, 63)}
CIRCUIT_ENGINE = {"ELEM": "ELEM", "MAT": "MAT", "PERI": "PERI", "RESTAU": "PERI-RESTAU", "CTA": "CTA"}
MONTEE_CTA = "MONTEE-CTA-R1"  # pied de la colonne CTA vers la terrasse R+1 (CVPS_02 : (895 ; 1768) pt)
COLLECTEUR = (2105, 1640)  # nourrice 4 départs (coordonnées affichées CVPS_01)
G_MERGE, T_JOIN, TOL_C = 40, 22, 2.0


# ---------------------------------------------------------------- lecture PDF
def lire_tirets(page):
    M = page.rotation_matrix
    out = collections.defaultdict(list)
    for d in page.get_drawings():
        if d.get("layer") != "VIV02_CHA_RES_ECH_A" or d["type"] != "fs":
            continue
        col = tuple(round(x * 255) for x in d["fill"])
        nom = [k for k, v in COULEURS.items() if v == col]
        if not nom:
            continue
        r = d["rect"] * M
        if r.width >= r.height:
            out[nom[0]].append(("H", r.y0 + r.height / 2, r.x0, r.x1))
        else:
            out[nom[0]].append(("V", r.x0 + r.width / 2, r.y0, r.y1))
    return out


def fusion(segs):
    out = []
    for o in ("H", "V"):
        ss = sorted([x for x in segs if x[0] == o], key=lambda x: x[1])
        groupes = []
        for x in ss:
            if groupes and abs(x[1] - groupes[-1][-1][1]) <= TOL_C:
                groupes[-1].append(x)
            else:
                groupes.append([x])
        for g in groupes:
            iv = sorted(g, key=lambda x: x[2])
            a, b, cs = iv[0][2], iv[0][3], [iv[0][1]]
            for _, c, a2, b2 in iv[1:]:
                if a2 - b <= G_MERGE:
                    b = max(b, b2)
                    cs.append(c)
                else:
                    out.append((o, sum(cs) / len(cs), a, b))
                    a, b, cs = a2, b2, [c]
            out.append((o, sum(cs) / len(cs), a, b))
    return out


def graphe(segs):
    coupes = [{s[2]: 0, s[3]: 0} for s in segs]
    jonctions = []
    for i, h in enumerate(segs):
        if h[0] != "H":
            continue
        for j, v in enumerate(segs):
            if v[0] != "V":
                continue
            px, py = v[1], h[1]
            dh, dv = max(0, h[2] - px, px - h[3]), max(0, v[2] - py, py - v[3])
            if dh <= T_JOIN and dv <= T_JOIN:
                xi, yj = min(max(px, h[2]), h[3]), min(max(py, v[2]), v[3])
                coupes[i][xi] = coupes[j][yj] = 0
                jonctions.append((i, xi, j, yj, max(dh, dv)))
    nodes, cle = {}, {}

    def nid(i, c):
        s = segs[i]
        k = (i, round(c, 2))
        if k not in cle:
            cle[k] = len(nodes)
            nodes[cle[k]] = (c, s[1]) if s[0] == "H" else (s[1], c)
        return cle[k]

    edges = []
    for i, (s, cs) in enumerate(zip(segs, coupes)):
        cs = sorted(cs)
        for a, b in zip(cs, cs[1:]):
            if b - a > 0.01:
                edges.append([nid(i, a), nid(i, b), b - a, 0.0])
    for i, xi, j, yj, gap in jonctions:
        a, b = nid(i, xi), nid(j, yj)
        edges.append([a, b, math.dist(nodes[a], nodes[b]), gap + 0.001])
    return nodes, edges


def d_pt_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    t = 0 if l2 == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2))
    q = (a[0] + t * dx, a[1] + t * dy)
    return math.dist(p, q), q


def d_seg_seg(a, b, c, d):
    best = None
    for p in (a, b):
        dd, q = d_pt_seg(p, c, d)
        best = min(best or (9e9, q), (dd, q))
    for p in (c, d):
        dd, _ = d_pt_seg(p, a, b)
        best = min(best, (dd, p))
    return best  # (distance, point sur [c,d])


def segment_radiateur(r):
    x, y, o = r["pt"]
    L = (float(r["L_dispo_mm"] or 750) / 1000) / PT_M
    return ((x - L / 2, y), (x + L / 2, y)) if o == "H" else ((x, y - L / 2), (x, y + L / 2))


def reseau(circ, tirets, rads):
    nodes, edges = graphe(fusion(tirets[circ]))
    journal = []

    def adj():
        A = collections.defaultdict(list)
        for i, e in enumerate(edges):
            A[e[0]].append((e[1], i))
            A[e[1]].append((e[0], i))
        return A

    # 1) raccordement des radiateurs : extrémité libre la plus proche, sinon piquage sur un tube
    attache = {}
    for r in rads:
        rs, A = segment_radiateur(r), adj()
        libres = sorted((d_seg_seg(*rs, nodes[n], nodes[n])[0], n) for n in nodes if len(A[n]) == 1)
        libres = [c for c in libres if c[0] <= 30 and c[1] not in attache.values()]
        if libres:
            attache[r["id_radiateur"]] = libres[0][1]
            continue
        best = None
        for i, e in enumerate(edges):
            dd, q = d_seg_seg(*rs, nodes[e[0]], nodes[e[1]])
            if best is None or dd < best[0]:
                best = (dd, i, q)
        dd, i, q = best
        if dd > 40:
            journal.append(f"{r['id_radiateur']} : aucun tube à moins de 40 pt (non raccordé)")
            continue
        a, b, _, w = edges[i]
        k = max(nodes) + 1
        nodes[k] = q
        edges[i] = [a, k, math.dist(nodes[a], q), w]
        edges.append([k, b, math.dist(q, nodes[b]), w])
        attache[r["id_radiateur"]] = k

    # 2) pontage minimal des morceaux isolés (tube masqué derrière une plinthe, cartouche texte…)
    A = adj()
    racine = min([n for n in nodes if len(A[n]) == 1] or nodes, key=lambda n: math.dist(nodes[n], COLLECTEUR))

    def composantes():
        A = adj()
        vu, c = {}, 0
        for n in nodes:
            if n in vu:
                continue
            pile, vu[n] = [n], c
            while pile:
                u = pile.pop()
                for v, _ in A[u]:
                    if v not in vu:
                        vu[v] = c
                        pile.append(v)
            c += 1
        return vu

    for _ in range(50):
        vu = composantes()
        rc = vu[racine]
        autres = {c for c in set(vu.values()) if c != rc and any(vu[n] == c for n in attache.values())}
        if not autres:
            break
        A = adj()
        best = None
        for n in nodes:
            if vu[n] not in autres or len(A[n]) != 1:
                continue
            for m in nodes:
                if vu[m] != rc:
                    continue
                p, q = nodes[n], nodes[m]
                d = math.dist(p, q)
                if (abs(p[0] - q[0]) < 2 or abs(p[1] - q[1]) < 2 or d <= 25) and (best is None or d < best[0]):
                    best = (d, n, m)
        if best is None:
            journal.append(f"morceau isolé non relié ({sorted(autres)})")
            break
        d, n, m = best
        edges.append([n, m, d, 1000 + d])
        journal.append(f"liaison supposée de {d * PT_M:.1f} m entre {fmt(nodes[n])} et {fmt(nodes[m])}")

    # 3) arbre couvrant : tubes d'abord, puis jonctions par écart croissant (les boucles parasites tombent)
    par = {}

    def f(x):
        par.setdefault(x, x)
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    garde = []
    for e in sorted(edges, key=lambda e: e[3]):
        ra, rb = f(e[0]), f(e[1])
        if ra == rb:
            if e[3] > 0.01 and e[2] > 2:
                journal.append(f"jonction ignorée (boucle) {fmt(nodes[e[0]])} – {fmt(nodes[e[1]])}, écart {e[3]:.0f} pt")
            continue
        par[ra] = rb
        garde.append(e)
    edges[:] = garde
    A = adj()
    parent, ordre, file = {racine: None}, [racine], collections.deque([racine])
    while file:
        u = file.popleft()
        for v, _ in A[u]:
            if v not in parent:
                parent[v] = u
                ordre.append(v)
                file.append(v)
    rad_en = collections.defaultdict(list)
    for rid, n in attache.items():
        rad_en[n].append(rid)
    enfants = collections.defaultdict(list)
    for v, u in parent.items():
        if u is not None:
            enfants[u].append(v)
    utile = set()
    for n in reversed(ordre):
        if rad_en[n] or any(c in utile for c in enfants[n]):
            utile.add(n)

    def cle(n):
        return n == racine or bool(rad_en[n]) or len([c for c in enfants[n] if c in utile]) != 1

    troncons = []

    def parcours(depart, amont):
        for c in [c for c in enfants[depart] if c in utile]:
            pts, n = [nodes[depart]], c
            while True:
                pts.append(nodes[n])
                if cle(n):
                    break
                n = [x for x in enfants[n] if x in utile][0]
            tid = f"{circ[:2]}{len(troncons) + 1:03d}"
            troncons.append({"troncon_id": tid, "amont_id": amont, "pts": pts, "radiateurs": rad_en[n],
                             "longueur_m": sum(math.dist(a, b) for a, b in zip(pts, pts[1:])) * PT_M})
            parcours(n, tid)

    parcours(racine, "SOURCE")
    non_atteints = [rid for rid, n in attache.items() if n not in parent]
    non_raccordes = [r["id_radiateur"] for r in rads if r["id_radiateur"] not in attache]
    for rid in non_atteints + non_raccordes:
        journal.append(f"{rid} : non relié au collecteur")
    return troncons, journal, nodes[racine]


def fmt(p):
    return f"({p[0]:.0f};{p[1]:.0f})"


# ---------------------------------------------------------------- tronçons -> moteur
def branches_de_piquage(reseaux, positions):
    """Un émetteur piqué sur un tube qui continue vers l'aval (ou plusieurs émetteurs au même nœud)
    reçoit sa propre branche « B-<id> » : elle porte le raccordement (cuivre pour un radiateur) et son étiquette."""
    for circ, (troncons, _, _) in reseaux.items():
        fils = collections.Counter(t["amont_id"] for t in troncons)
        nouveaux = []
        for t in troncons:
            nouveaux.append(t)
            emetteurs = [x for x in t["radiateurs"] if x != MONTEE_CTA]
            if not emetteurs or (fils[t["troncon_id"]] == 0 and len(emetteurs) == 1):
                continue
            noeud = t["pts"][-1]
            for rid in emetteurs:
                cible = positions.get(rid, noeud)
                nouveaux.append({"troncon_id": "B-" + rid, "amont_id": t["troncon_id"], "pts": [noeud, cible],
                                 "radiateurs": [rid], "longueur_m": max(0.5, math.dist(noeud, cible) * PT_M)})
            t["radiateurs"] = [x for x in t["radiateurs"] if x == MONTEE_CTA]
        troncons[:] = nouveaux


def ecrire_troncons(h, reseaux, rads_eng, chemin):
    by_id = {r["id_radiateur"]: r for r in rads_eng}
    lignes = []
    for circ, (troncons, _, _) in reseaux.items():
        aval = collections.Counter()
        fils = collections.defaultdict(list)
        for t in troncons:
            fils[t["amont_id"]].append(t["troncon_id"])

        def compte(tid):
            t = next(x for x in troncons if x["troncon_id"] == tid)
            n = len(t["radiateurs"]) + sum(compte(c) for c in fils[tid])
            aval[tid] = n
            return n

        for t in troncons:
            if t["amont_id"] == "SOURCE":
                compte(t["troncon_id"])
        for t in troncons:
            if circ == "CTA":
                ecrire_cta(h, t, lignes)
                continue
            cuivre = aval[t["troncon_id"]] == 1 and not fils[t["troncon_id"]]
            L = t["longueur_m"] + (h.get("descente_radiateur_m", 0) if cuivre else 0)
            lignes.append({"circuit": CIRCUIT_ENGINE[circ], "troncon_id": t["troncon_id"], "amont_id": t["amont_id"],
                           "longueur_m": round(L, 2), "zeta_total": "", "radiateurs": ",".join(t["radiateurs"]),
                           "dn_impose": "", "materiau": "cuivre" if cuivre else "acier"})
            t["materiau"] = "cuivre" if cuivre else "acier"
            for rid in t["radiateurs"]:  # liens R+1 portés par ce radiateur RDC (décision D1)
                for enf in by_id[rid]["enfants_R1"]:
                    lignes.append({"circuit": CIRCUIT_ENGINE[circ], "troncon_id": "V-" + enf,
                                   "amont_id": t["troncon_id"],
                                   "longueur_m": by_id[enf]["raccord_longueur_m"] or h["hauteur_etage_m"],
                                   "zeta_total": "", "radiateurs": enf, "dn_impose": "", "materiau": "cuivre"})
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    return lignes


def ecrire_cta(h, t, lignes):
    """Réseau CTA : acier (H-21). La colonne montante vers la terrasse R+1 est reconstituée
    d'après CVPS_02 : hauteur d'étage + 0,95 m en terrasse, puis 1,2 m (CTA nord) et 0,5 m (CTA sud)."""
    t["materiau"] = h.get("cta_raccordement_materiau", "acier")
    rads = [x for x in t["radiateurs"] if x != MONTEE_CTA]
    lignes.append({"circuit": "CTA", "troncon_id": t["troncon_id"], "amont_id": t["amont_id"],
                   "longueur_m": round(t["longueur_m"], 2), "zeta_total": "", "radiateurs": ",".join(rads),
                   "dn_impose": "", "materiau": t["materiau"]})
    if MONTEE_CTA in t["radiateurs"]:
        lignes += [
            {"circuit": "CTA", "troncon_id": "CT-R1-MONTEE", "amont_id": t["troncon_id"],
             "longueur_m": round(h["hauteur_etage_m"] + 27 * PT_M, 2), "zeta_total": "", "radiateurs": "",
             "dn_impose": "", "materiau": t["materiau"]},
            {"circuit": "CTA", "troncon_id": "CT-R1-NORD", "amont_id": "CT-R1-MONTEE",
             "longueur_m": round(34 * PT_M, 2), "zeta_total": "", "radiateurs": "CTA-ELEM-NORD", "dn_impose": "",
             "materiau": t["materiau"]},
            {"circuit": "CTA", "troncon_id": "CT-R1-SUD", "amont_id": "CT-R1-MONTEE",
             "longueur_m": round(14 * PT_M, 2), "zeta_total": "", "radiateurs": "CTA-ELEM-SUD", "dn_impose": "",
             "materiau": t["materiau"]}]


# ---------------------------------------------------------------- annotation
class Placeur:
    """Place les étiquettes en évitant les chevauchements (essais autour du point d'ancrage)."""

    def __init__(self, obstacles):
        self.places = []
        self.obstacles = obstacles

    def poser(self, ax, ay, w, h, dist=7):
        essais = []
        for dx, dy in ((dist, -h - dist), (dist, dist), (-w - dist, -h - dist), (-w - dist, dist),
                       (-w / 2, -h - dist - 4), (-w / 2, dist + 4), (dist + 6, -h / 2), (-w - dist - 6, -h / 2),
                       (dist + 14, -h - dist - 10), (-w - dist - 14, dist + 10), (dist + 14, dist + 10),
                       (-w - dist - 14, -h - dist - 10)):
            r = pymupdf.Rect(ax + dx, ay + dy, ax + dx + w, ay + dy + h)
            cout = sum(self._inter(r, p) for p in self.places) * 10 + sum(self._inter(r, o) for o in self.obstacles)
            essais.append((cout, len(essais), r))
        r = min(essais)[2]
        self.places.append(r)
        return r

    @staticmethod
    def _inter(a, b):
        x = max(0, min(a.x1, b.x1) - max(a.x0, b.x0))
        y = max(0, min(a.y1, b.y1) - max(a.y0, b.y0))
        return x * y


def rgb(c):
    return tuple(v / 255 for v in c)


def annoter(src_pdf, out_pdf, reseaux, res_tr, rads_eng, rads_pt, synth, journal, h, chemins, ctas=()):
    out = pymupdf.open(src_pdf)
    sp = out[0]
    # On dessine sur la page d'origine. Les coordonnées de travail sont celles de la page AFFICHÉE
    # (CVPS_01 porte /Rotate 270) : conversion par derotation_matrix, texte tourné de la même valeur.
    Dm, ROT = sp.derotation_matrix, sp.rotation

    class _Page:
        def draw_rect(self, r, **k):
            sp.draw_rect(pymupdf.Rect(r) * Dm, **k)

        def draw_line(self, a, b, **k):
            sp.draw_line(pymupdf.Point(a) * Dm, pymupdf.Point(b) * Dm, **k)

        def draw_circle(self, c, rad, **k):
            sp.draw_circle(pymupdf.Point(c) * Dm, rad, **k)

        def insert_text(self, pt, txt, **k):
            sp.insert_text(pymupdf.Point(pt) * Dm, txt, rotate=ROT, **k)

    page = _Page()
    by_tr = {r["troncon_id"]: r for r in res_tr}
    by_rad = {r["id_radiateur"]: r for r in rads_eng}
    obstacles = []
    for circ, (troncons, _, _) in reseaux.items():
        for t in troncons:
            for a, b in zip(t["pts"], t["pts"][1:]):
                obstacles.append(pymupdf.Rect(min(a[0], b[0]) - 1.5, min(a[1], b[1]) - 1.5,
                                              max(a[0], b[0]) + 1.5, max(a[1], b[1]) + 1.5))
    pl = Placeur(obstacles)
    fs = 5.0

    def boite(rect, lignes, bord, fond=(1, 1, 1), couleur_txt=(0, 0, 0), gras=False):
        page.draw_rect(rect, color=rgb(bord), fill=fond, width=0.4)
        y = rect.y0 + fs + 0.6
        for i, txt in enumerate(lignes):
            page.insert_text((rect.x0 + 1.2, y), txt, fontsize=fs, fontname="hebo" if (gras or i == 0) else "helv",
                             color=couleur_txt)
            y += fs + 0.8

    # 1) diamètres : une étiquette au départ et à chaque changement de section
    for circ, (troncons, _, racine) in reseaux.items():
        col = COULEURS[circ]
        dn_amont = {"SOURCE": None}
        for t in troncons:
            r = by_tr.get(t["troncon_id"])
            if not r or "designation" not in r:
                continue
            lab = ("Cu " + r["designation"].replace("Cu ", "")) if r["materiau"] == "cuivre" else f"DN{r['DN']}"
            dn_amont[t["troncon_id"]] = lab
            if dn_amont.get(t["amont_id"]) == lab:
                continue
            # point d'ancrage : 35 % du premier tronçon droit significatif
            a, b = t["pts"][0], t["pts"][1]
            for p, q in zip(t["pts"], t["pts"][1:]):
                if math.dist(p, q) > 12:
                    a, b = p, q
                    break
            ax, ay = a[0] + 0.35 * (b[0] - a[0]), a[1] + 0.35 * (b[1] - a[1])
            if circ == "CTA":
                txt = f"{lab}  {r['Qv_m3h']:.1f} m3/h ({r['cas_dimensionnant']})"
            else:
                txt = lab + ("" if r["materiau"] == "cuivre" else f"  {r['P_cumul_kW']:.1f} kW")
            w = pymupdf.get_text_length(txt, fontname="hebo", fontsize=fs) + 2.4
            rect = pl.poser(ax, ay, w, fs + 2, dist=3)
            page.draw_line(pymupdf.Point(ax, ay), pymupdf.Point(rect.x0 + rect.width / 2, rect.y0 + rect.height / 2),
                           color=rgb(col), width=0.25)
            page.draw_circle(pymupdf.Point(ax, ay), 0.9, color=rgb(col), fill=rgb(col))
            boite(rect, [txt], col, couleur_txt=rgb(col), gras=True)
    # 2) CTA (fiches France Air)
    for c in ctas:
        if "pt" not in c:
            continue
        x, y = c["pt"]
        lignes = [f"{c['id_cta']} - {c['modele']}",
                  f"Soufflage {c['soufflage_m3h']} m3/h - {c['local']}",
                  f"Chaud {c['regime_chaud']} : {c['P_batterie_chaud_W'] / 1000:.1f} kW max, {c['Qv_chaud_m3h']:.2f} m3/h,"
                  f" dP {c['dp_batterie_chaud_kPa']:.1f} kPa",
                  f"Froid {c['regime_froid']} : {c['Qv_froid_m3h']:.2f} m3/h, dP {c['dp_batterie_froid_kPa']:.1f} kPa",
                  f"Besoin chaud estimé (soufflage à 19 °C) : {c['besoin_chaud_neutre_W_estime'] / 1000:.1f} kW"]
        w = max(pymupdf.get_text_length(s_, fontname="hebo", fontsize=fs) for s_ in lignes) + 2.6
        hh = len(lignes) * (fs + 0.8) + 1.6
        rect = pl.poser(x, y, w, hh, dist=12)
        page.draw_line(pymupdf.Point(x, y), pymupdf.Point(rect.x0 + rect.width / 2, rect.y0 + rect.height / 2),
                       color=rgb(COULEURS["CTA"]), width=0.35)
        page.draw_circle(pymupdf.Point(x, y), 2.2, color=rgb(COULEURS["CTA"]), width=0.6)
        boite(rect, lignes, COULEURS["CTA"], fond=(0.93, 1, 0.93))
    # 3) radiateurs
    for rid, (x, y, o) in rads_pt.items():
        r = by_rad[rid]
        circ = {"ELEM": "ELEM", "MAT": "MAT", "PERI": "PERI", "PERI-RESTAU": "RESTAU"}[r["circuit"]]
        p = r["P_part_W"]
        lignes = [rid, (f"P = {p:,.0f} W".replace(",", " ") if p else "P = ? (hors bilan)")]
        for enf in r["enfants_R1"]:
            pe = by_rad[enf]["P_part_W"]
            lignes.append(f"+ {enf} : {pe:,.0f} W".replace(",", " ") if pe else f"+ {enf} : ?")
        w = max(pymupdf.get_text_length(s, fontname="hebo", fontsize=fs) for s in lignes) + 2.6
        hh = len(lignes) * (fs + 0.8) + 1.6
        rect = pl.poser(x, y, w, hh, dist=9)
        page.draw_line(pymupdf.Point(x, y), pymupdf.Point(rect.x0 + rect.width / 2, rect.y0 + rect.height / 2),
                       color=(0, 0, 0), width=0.25)
        flag = r["statut"] != "OK" or not p
        boite(rect, lignes, COULEURS[circ], fond=(1, 1, 0.85) if flag else (1, 1, 1))
    # 4) cartouche de légende (police de base : ni Δ ni flèche)
    lx, ly = 1180, 120
    crit = {}
    for c in chemins:
        if c["critique"] == "OUI":
            crit[c["circuit"] + (f" ({c['cas']})" if c.get("cas") else "")] = c
    lignes = [
        "PLAN RDC - RADIATEURS ET DIAMÈTRES (PROVISOIRE, rév. C du 02/10/2026)",
        "Fond : CVPS_01 DCE ind. 0. Réseau ALLER relu sur le calque VIV02_CHA_RES_ECH_A ; le retour a la même section.",
        "Étiquette radiateur : identifiant / P = part du local (bilan émetteurs, puissance à installer x 1,20 / nb radiateurs).",
        "  + R1-xx = radiateur R+1 raccordé sur ce radiateur RDC (décision D1, réservation de dalle). Fond jaune = à confirmer.",
        "Étiquette tube : au départ et à chaque changement de section. DNxx = acier NF EN 10255 (note F5) + puissance transitée ;",
        "  Cu = raccordement apparent cuivre NF EN 1057, du té de piquage jusqu'au radiateur.",
        f"Hypothèses : régime {h['t_aller_C']:.0f}/{h['t_retour_C']:.0f} °C (H-02 à confirmer), dT = 10 K, V max de la note F5,"
        f" descente {h.get('descente_radiateur_m', 0)} m par branche, dP terminal {h['dp_terminal_kPa']:.0f} kPa.",
        "CTA : non dimensionné (puissances des batteries inconnues, D-17). Primaire PAC non traité.",
    ]
    for s_ in synth:
        lignes.append(f"Départ {s_['circuit']} : {s_['P_kW']} kW, {s_['Qv_m3h']} m3/h, DN {s_['DN_depart_mini']} mini")
    lignes.append("  PERI et restauration partent du même départ Admin/Péri : tronçon commun nourrice - V2V au DN du départ total.")
    lignes.append("CTA : batteries change-over (fiches France Air) : eau chaude 60/40 °C l'hiver, eau glacée 7/12 °C l'été dans le"
                  " même réseau ; DN = max des deux cas (H-19). La puissance « max » des fiches porte l'air à 44 °C : le besoin réel est bien plus faible.")
    for c, k in sorted(crit.items()):
        lignes.append(f"Radiateur critique {c} : {k['id_radiateur']}, {k['longueur_aller_m']} m aller,"
                      f" dP = {k['dP_chemin_Pa'] / 1000:.1f} kPa, soit {k['HMT_circuit_mCE']} mCE (hors chaufferie)")
    lignes += [f"Contrôle relecture : {x}" for x in journal][:14]
    w = max(pymupdf.get_text_length(s_, fontname="helv", fontsize=6.5) for s_ in lignes) + 14
    rect = pymupdf.Rect(lx, ly, lx + w, ly + len(lignes) * 8 + 8)
    page.draw_rect(rect, color=(0, 0, 0), fill=(1, 1, 1), width=0.6)
    y = ly + 9
    for i, s_ in enumerate(lignes):
        page.insert_text((lx + 4, y), s_, fontsize=7.5 if i == 0 else 6.3, fontname="hebo" if i == 0 else "helv")
        y += 8
    out.save(out_pdf, garbage=3, deflate=True)


# ---------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, help="PDF DCE CVPS_01 (plan de réseau de chauffage RDC)")
    ap.add_argument("--out", default=os.path.join(ROOT, "outputs", "CVPS_01_RDC_radiateurs_diametres.pdf"))
    a = ap.parse_args()
    h = json.load(open(os.path.join(cc.DATA, "hypotheses.json"), encoding="utf-8"))

    # moteur : puissances, couplage R+1, raccordements
    locaux, rads = cc.puissances(h, cc.read_csv(os.path.join(cc.DATA, "bilan_emetteurs_EN12831.csv")),
                                 cc.read_csv(os.path.join(cc.DATA, "radiateurs_positions_PROVISOIRE.csv")))
    rads = cc.selection(h, rads, [])
    dn_tab = cc.table_dn(h)
    cu_tab = cc.table_cuivre(h, dn_tab)
    rads = cc.raccordements(h, cc.couplage_R1(h, rads), cu_tab)
    rdc = [dict(r, pt=(float(r["px"]), float(r["py"]), r["orientation"])) for r in rads if r["niveau"] == "RDC"]
    assert all(r["tuile"] == "pdf0" for r in rdc), "positions RDC attendues en coordonnées PDF (tuile pdf0)"

    page = pymupdf.open(a.pdf)[0]
    tirets = lire_tirets(page)
    reseaux, journal = {}, []
    ctas = cc.charger_cta(h)
    pos_cta = {p["id_cta"]: p for p in cc.read_csv(os.path.join(cc.DATA, "cta_positions.csv"))}
    dx, dy = h["repere"]["recalage_R1_vers_RDC_pt"]
    term_cta = []
    for c in ctas:
        p = pos_cta[c["id_cta"]]
        off = (0, 0) if p["tuile"] == "pdf0" else (dx, dy)
        c["pt"] = (float(p["px"]) + off[0], float(p["py"]) + off[1])
        if p["niveau"] == "RDC":
            term_cta.append({"id_radiateur": c["id_cta"], "L_dispo_mm": "300",
                             "pt": (float(p["piquage_px"]), float(p["piquage_py"]), "H")})
    term_cta.append({"id_radiateur": MONTEE_CTA, "L_dispo_mm": "300", "pt": (895 + dx, 1768 + dy, "H")})
    for circ in ("ELEM", "MAT", "PERI", "RESTAU", "CTA"):
        rr = term_cta if circ == "CTA" else [r for r in rdc if CIRCUIT_ENGINE[circ] == r["circuit"]]
        tr, jr, racine = reseau(circ, tirets, rr)
        reseaux[circ] = (tr, jr, racine)
        journal += [f"{circ} : {x}" for x in jr if not x.startswith("jonction")]
        print(f"{circ} : {len(tr)} tronçons, {sum(len(t['radiateurs']) for t in tr)}/{len(rr)} radiateurs raccordés")
        for x in jr:
            print("   ", x)
    chemin = os.path.join(cc.DATA, "troncons_RDC_DCE.csv")
    positions = {r["id_radiateur"]: r["pt"][:2] for r in rdc}
    positions.update({c["id_cta"]: c["pt"] for c in ctas})
    branches_de_piquage(reseaux, positions)
    ecrire_troncons(h, reseaux, rads, chemin)
    tous = cc.read_csv(chemin)
    res_tr, chemins, flags = cc.dimensionner(h, [t for t in tous if t["circuit"] != "CTA"], rads, dn_tab, cu_tab)
    t_cta, ch_cta, fl_cta = cc.dimensionner_cta(h, [t for t in tous if t["circuit"] == "CTA"], dn_tab, cu_tab, ctas)
    res_tr, chemins, flags = res_tr + t_cta, chemins + ch_cta, flags + fl_cta
    for f_ in flags:
        print("FLAG", f_)
    synth = [s for s in cc.synthese_circuits(h, rads, dn_tab, ctas) if s["circuit"] != "PERI-RESTAU"]
    annoter(a.pdf, a.out, reseaux, res_tr, rads, {r["id_radiateur"]: r["pt"] for r in rdc}, synth, journal, h, chemins,
            ctas)
    for c in chemins:
        if c["critique"] == "OUI":
            print("Critique", c["circuit"], c.get("cas", ""), c["id_radiateur"], c["longueur_aller_m"], "m", c["dP_chemin_Pa"], "Pa", c["HMT_circuit_mCE"], "mCE")
    print("Tronçons :", chemin)
    print("Plan annoté :", a.out)


if __name__ == "__main__":
    main()
