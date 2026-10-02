# -*- coding: utf-8 -*-
"""Construit le modèle chauffage dans Revit à partir des fichiers générés par le moteur.

Entrées (lecture seule) :
  model/modele_chauffage_albert_camus.json   niveaux, systèmes, radiateurs, CTA, réservations
  model/reseau_rdc_geometrie.json            polylignes du réseau RDC + sections retenues
  revit/config_revit.json                    familles, calage, hauteurs, étapes, dry_run

Lancement : pyRevit (bouton ou « Run script ») ou RevitPythonShell, projet ouvert.
- dry_run = true (défaut) : tout est créé dans un groupe de transactions puis ANNULÉ. Seul le journal est écrit.
- dry_run = false : les transactions sont validées.
Journal : revit/journal_build.txt

Compatible IronPython 2.7 et CPython (pas de f-strings). Script non testé hors Revit :
lancer d'abord en dry_run et lire le journal.
"""
import io
import json
import math
import os

from Autodesk.Revit.DB import (BuiltInCategory, BuiltInParameter, Color, CurveArray, ElementId,
                               ElementParameterFilter, ElementTransformUtils, FamilySymbol,
                               FilteredElementCollector, Floor, Level, Line, OverrideGraphicSettings,
                               ParameterFilterElement, ParameterFilterRuleFactory, StorageType, Transaction,
                               TransactionGroup, XYZ)
from Autodesk.Revit.DB.Plumbing import Pipe, PipeType, PipingSystemType
from Autodesk.Revit.DB.Structure import StructuralType

try:
    from System.Collections.Generic import List
except ImportError:  # pragma: no cover
    List = None

try:
    doc = __revit__.ActiveUIDocument.Document  # noqa: F821
    uidoc = __revit__.ActiveUIDocument  # noqa: F821
except NameError:
    from pyrevit import revit
    doc, uidoc = revit.doc, revit.uidoc

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
FT = 1.0 / 0.3048


def lire(chemin):
    with io.open(chemin, encoding="utf-8") as f:
        return json.load(f)


MODELE = lire(os.path.join(RACINE, "model", "modele_chauffage_albert_camus.json"))
GEOM = lire(os.path.join(RACINE, "model", "reseau_rdc_geometrie.json"))
CFG = lire(os.path.join(ICI, "config_revit.json"))
JOURNAL = []


def log(*args):
    txt = " ".join([u"%s" % a for a in args])
    JOURNAL.append(txt)
    print(txt)


# ---------------------------------------------------------------- outils
def xyz(x_m, y_m, z_m):
    tr = CFG["transformation"]
    a = math.radians(tr.get("angle_deg", 0.0))
    xr = x_m * math.cos(a) - y_m * math.sin(a) + tr.get("x0_m", 0.0)
    yr = x_m * math.sin(a) + y_m * math.cos(a) + tr.get("y0_m", 0.0)
    return XYZ(xr * FT, yr * FT, z_m * FT)


def nom(e):
    try:
        return e.Name
    except Exception:
        return None


def setp(e, nom_param, valeur):
    """Renseigne un paramètre s'il existe ; renvoie True si écrit."""
    if e is None or not nom_param:
        return False
    p = e.LookupParameter(nom_param)
    if p is None or p.IsReadOnly:
        return False
    try:
        st = p.StorageType
        if st == StorageType.String:
            p.Set(u"%s" % valeur)
        elif st == StorageType.Double:
            p.Set(float(valeur))
        elif st == StorageType.Integer:
            p.Set(int(valeur))
        else:
            return False
        return True
    except Exception:
        return False


def set_builtin(e, bip, valeur):
    try:
        p = e.get_Parameter(bip)
        if p is not None and not p.IsReadOnly:
            p.Set(valeur)
            return True
    except Exception:
        pass
    return False


class Etape(object):
    """Une transaction par étape (validée) ; le groupe englobant est annulé en dry_run."""

    def __init__(self, nom_etape):
        self.nom = nom_etape
        self.t = Transaction(doc, "CVC - " + nom_etape)

    def __enter__(self):
        self.t.Start()
        log("== étape", self.nom)
        return self

    def __exit__(self, typ, val, tb):
        if typ is not None:
            log("   ERREUR", self.nom, val)
            self.t.RollBack()
            return True
        self.t.Commit()
        return False


# ---------------------------------------------------------------- niveaux
NIVEAUX = {}


def etape_niveaux():
    existants = dict((l.Name, l) for l in FilteredElementCollector(doc).OfClass(Level))
    with Etape("niveaux"):
        for n in MODELE["niveaux"]:
            nom_revit = CFG["niveaux"].get(n["id"], n["id"])
            if nom_revit in existants:
                NIVEAUX[n["id"]] = existants[nom_revit]
                log("   niveau trouvé", nom_revit, round(existants[nom_revit].Elevation / FT, 3), "m")
            elif CFG["niveaux"].get("creer_si_absent", True):
                lv = Level.Create(doc, n["elevation_m"] * FT)
                lv.Name = nom_revit
                NIVEAUX[n["id"]] = lv
                log("   niveau créé", nom_revit, n["elevation_m"], "m (", n["source"], ")")


def z_niveau(id_niv):
    lv = NIVEAUX.get(id_niv)
    return lv.Elevation / FT if lv is not None else 0.0


# ---------------------------------------------------------------- systèmes et types
SYSTEMES = {}
TYPES_TUBE = {}


def etape_systemes():
    tous = list(FilteredElementCollector(doc).OfClass(PipingSystemType))
    par_nom = dict((nom(s), s) for s in tous)
    with Etape("systemes"):
        for s in MODELE["systemes"]:
            if s["id"] in par_nom:
                st = par_nom[s["id"]]
            else:
                classe = "SupplyHydronic" if s["sens"] == "aller" else "ReturnHydronic"
                modele = [x for x in tous if str(x.SystemClassification) == classe]
                if not modele:
                    log("   aucun type de système", classe, "à dupliquer :", s["id"], "non créé")
                    continue
                st = modele[0].Duplicate(s["id"])
                log("   système créé", s["id"], "depuis", nom(modele[0]))
            rgb = s.get("rgb_legende") or s.get("rgb_plan")
            if rgb:
                try:
                    st.LineColor = Color(rgb[0], rgb[1], rgb[2])
                except Exception as ex:
                    log("   couleur non appliquée", s["id"], ex)
            set_builtin(st, BuiltInParameter.RBS_SYSTEM_ABBREVIATION_PARAM, s["id"])
            SYSTEMES[s["id"]] = st


def etape_types_canalisation():
    tous = list(FilteredElementCollector(doc).OfClass(PipeType))
    par_nom = dict((nom(t), t) for t in tous)
    with Etape("types_canalisation"):
        for cle, c in CFG["types_canalisation"].items():
            if c["nom"] in par_nom:
                TYPES_TUBE[cle] = par_nom[c["nom"]]
                continue
            src = par_nom.get(c.get("dupliquer_depuis")) or (tous[0] if tous else None)
            if src is None:
                log("   aucun type de canalisation à dupliquer")
                continue
            TYPES_TUBE[cle] = src.Duplicate(c["nom"])
            log("   type créé", c["nom"], "- AFFECTER le segment (matériau, liste de tailles) dans les préférences"
                " de routage :", "acier NF EN 10255" if cle == "acier" else "cuivre NF EN 1057")


def etape_filtres():
    vue = doc.ActiveView
    cats = [ElementId(BuiltInCategory.OST_PipeCurves), ElementId(BuiltInCategory.OST_PipeFitting),
            ElementId(BuiltInCategory.OST_PipeAccessory), ElementId(BuiltInCategory.OST_FlexPipeCurves)]
    existants = dict((nom(f), f) for f in FilteredElementCollector(doc).OfClass(ParameterFilterElement))
    with Etape("filtres"):
        for s in MODELE["systemes"]:
            st = SYSTEMES.get(s["id"])
            if st is None:
                continue
            nom_f = "CH - " + s["id"]
            f = existants.get(nom_f)
            if f is None:
                regle = ParameterFilterRuleFactory.CreateEqualsRule(
                    ElementId(BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM), st.Id)
                f = ParameterFilterElement.Create(doc, nom_f, List[ElementId](cats), ElementParameterFilter(regle))
                log("   filtre créé", nom_f)
            rgb = s.get("rgb_legende") or s.get("rgb_plan")
            try:
                if not vue.IsFilterApplied(f.Id):
                    vue.AddFilter(f.Id)
                ogs = OverrideGraphicSettings()
                if rgb:
                    ogs.SetProjectionLineColor(Color(rgb[0], rgb[1], rgb[2]))
                vue.SetFilterOverrides(f.Id, ogs)
            except Exception as ex:
                log("   filtre non appliqué à la vue active", nom_f, ex)


# ---------------------------------------------------------------- familles
def symbole(cle):
    c = CFG["familles"].get(cle)
    if not c:
        return None
    for fs in FilteredElementCollector(doc).OfClass(FamilySymbol):
        try:
            if fs.Family.Name == c["famille"] and nom(fs) == c["type"]:
                if not fs.IsActive:
                    fs.Activate()
                return fs
        except Exception:
            continue
    return None


POSES = {}


def poser(id_elem, cle_famille, x, y, niveau, z_rel, orientation, infos):
    fs = symbole(cle_famille)
    if fs is None:
        log("   famille introuvable pour", id_elem, "(", cle_famille, ") : non posé")
        return None
    lv = NIVEAUX.get(niveau)
    p = xyz(x, y, z_niveau(niveau) + z_rel)
    inst = doc.Create.NewFamilyInstance(p, fs, lv, StructuralType.NonStructural)
    for bip in (BuiltInParameter.INSTANCE_ELEVATION_PARAM, BuiltInParameter.INSTANCE_FREE_HOST_OFFSET_PARAM):
        if set_builtin(inst, bip, z_rel * FT):
            break
    angle = math.radians(CFG["transformation"].get("angle_deg", 0.0)) + (math.pi / 2 if orientation == "V" else 0)
    if abs(angle) > 1e-9:
        ElementTransformUtils.RotateElement(doc, inst.Id, Line.CreateBound(p, p + XYZ.BasisZ), angle)
    set_builtin(inst, BuiltInParameter.ALL_MODEL_MARK, id_elem)
    set_builtin(inst, BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS, infos.get("commentaire", ""))
    prm = CFG.get("parametres", {})
    for cle in ("id", "circuit", "puissance", "p50", "statut"):
        if cle in infos:
            setp(inst, prm.get(cle), infos[cle])
    POSES[id_elem] = inst
    return inst


def etape_radiateurs():
    n = 0
    with Etape("radiateurs"):
        for r in MODELE["radiateurs"]:
            pm = r["position_m"]
            p = r.get("P_part_W")
            infos = {"id": r["id"], "circuit": r["circuit_dce"], "statut": r["statut"],
                     "commentaire": u"%s - P = %s W - %s" % (r["local"], p if p else "?", r["selection"]["statut"])}
            if p:
                infos["puissance"] = p
            if r.get("P50_requise_W"):
                infos["p50"] = r["P50_requise_W"]
            if poser(r["id"], r["type_dessine"], pm["x"], pm["y"], r["niveau"], pm["z_bas_mm"] / 1000.0,
                     r["orientation_plan"], infos):
                n += 1
        log("   radiateurs posés :", n, "/", len(MODELE["radiateurs"]),
            "- orientation par défaut : longueur selon X ; vérifier le côté pièce")


def etape_cta():
    n = 0
    h = CFG["hauteurs_m"]
    with Etape("cta"):
        for c in MODELE.get("cta", []):
            if "x_m" not in c:
                log("   CTA sans position :", c["id_cta"])
                continue
            z = h["cta_terrasse"] if c["niveau"] == "R+1" else h["cta_rdc"]
            infos = {"id": c["id_cta"], "circuit": "CTA", "statut": c["statut"],
                     "commentaire": u"%s - %s - chaud %s kW max / froid %s kW" % (
                         c["modele"], c["local"], c["P_batterie_chaud_W"] / 1000.0, c["P_batterie_froid_W"] / 1000.0)}
            if poser(c["id_cta"], "CTA", c["x_m"], c["y_m"], c["niveau"], z, "H", infos):
                n += 1
        log("   CTA posées :", n, "/", len(MODELE.get("cta", [])))


def etape_reservations():
    lv = NIVEAUX.get("R+1")
    if lv is None:
        log("   niveau R+1 absent : réservations non créées")
        return
    dalles = [f for f in FilteredElementCollector(doc).OfClass(Floor) if f.LevelId == lv.Id]
    n = 0
    with Etape("reservations"):
        for r in MODELE.get("reservations_dalle", []):
            c = xyz(r["x_m"], r["y_m"], z_niveau("R+1"))
            hote = None
            for f in dalles:
                bb = f.get_BoundingBox(None)
                if bb and bb.Min.X <= c.X <= bb.Max.X and bb.Min.Y <= c.Y <= bb.Max.Y:
                    hote = f
                    break
            if hote is None:
                log("   pas de dalle R+1 sous", r["id"], "-> réservation non créée")
                continue
            w, d = [float(v) / 1000.0 * FT / 2 for v in r["dimensions_mm"].split("x")]
            pts = [XYZ(c.X - w, c.Y - d, c.Z), XYZ(c.X + w, c.Y - d, c.Z), XYZ(c.X + w, c.Y + d, c.Z),
                   XYZ(c.X - w, c.Y + d, c.Z)]
            ca = CurveArray()
            for i in range(4):
                ca.Append(Line.CreateBound(pts[i], pts[(i + 1) % 4]))
            try:
                op = doc.Create.NewOpening(hote, ca, True)
                set_builtin(op, BuiltInParameter.ALL_MODEL_MARK, r["id"])
                n += 1
            except Exception as ex:
                log("   réservation", r["id"], "non créée :", ex)
        log("   réservations créées :", n, "/", len(MODELE.get("reservations_dalle", [])))


# ---------------------------------------------------------------- canalisations
EXTREMITES = {}  # (sens, x, y, z arrondis) -> [connecteurs libres]
FIN_TRONCON = {}  # émetteur -> (point final du tronçon qui le dessert (m), direction)


def cle_pt(sens, p):
    return (sens, round(p.X, 3), round(p.Y, 3), round(p.Z, 3))


def nettoyer(pts, lmin):
    out = []
    for p in pts:
        if out and math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) < lmin:
            continue
        out.append(p)
    # fusion des points alignés
    res = out[:1]
    for i in range(1, len(out) - 1):
        a, b, c = res[-1], out[i], out[i + 1]
        if abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) > 1e-6:
            res.append(b)
    if len(out) > 1:
        res.append(out[-1])
    return res


def connecteurs(e):
    try:
        cm = e.MEPModel.ConnectorManager if hasattr(e, "MEPModel") and e.MEPModel else e.ConnectorManager
        return [c for c in cm.Connectors]
    except Exception:
        return []


def tube(id_sys, materiau, p1, p2, dn_mm, niveau, sens):
    st = SYSTEMES.get(id_sys)
    tt = TYPES_TUBE.get(materiau)
    if st is None or tt is None or niveau not in NIVEAUX:
        return None
    if p1.DistanceTo(p2) < CFG.get("longueur_min_m", 0.05) * FT:
        return None
    pi = Pipe.Create(doc, st.Id, tt.Id, NIVEAUX[niveau].Id, p1, p2)
    if dn_mm:
        if not set_builtin(pi, BuiltInParameter.RBS_PIPE_DIAMETER_PARAM, dn_mm / 1000.0 * FT):
            log("   diamètre", dn_mm, "non appliqué (taille absente du segment ?)")
    for c in connecteurs(pi):
        EXTREMITES.setdefault(cle_pt(sens, c.Origin), []).append(c)
    return pi


def raccorder_noeuds():
    ok = ko = 0
    for k, cs in EXTREMITES.items():
        libres = [c for c in cs if not c.IsConnected]
        try:
            if len(libres) == 2:
                d1, d2 = libres[0].CoordinateSystem.BasisZ, libres[1].CoordinateSystem.BasisZ
                if abs(d1.DotProduct(d2) + 1) < 1e-3:
                    doc.Create.NewUnionFitting(libres[0], libres[1])
                else:
                    doc.Create.NewElbowFitting(libres[0], libres[1])
                ok += 1
            elif len(libres) == 3:
                a, b, c = libres
                for m1, m2, br in ((a, b, c), (a, c, b), (b, c, a)):
                    if abs(m1.CoordinateSystem.BasisZ.DotProduct(m2.CoordinateSystem.BasisZ) + 1) < 1e-3:
                        doc.Create.NewTeeFitting(m1, m2, br)
                        ok += 1
                        break
                else:
                    ko += 1
            elif len(libres) > 3:
                ko += 1
        except Exception:
            ko += 1
    log("   raccords créés :", ok, "- nœuds à reprendre à la main :", ko)


DECALAGE_RETOUR_M = 0.10


def decale(xy, direction, sens):
    """Le retour est décalé de 10 cm perpendiculairement au dernier tronçon (pas de superposition des chutes)."""
    if sens == "A" or direction is None:
        return xy
    dx, dy = direction
    L = math.hypot(dx, dy) or 1.0
    return (xy[0] - dy / L * DECALAGE_RETOUR_M, xy[1] + dx / L * DECALAGE_RETOUR_M)


def chute_vers(id_sys, materiau, dn, xy, z_haut, z_bas, niveau, sens, emetteur, direction=None):
    """(Retour : petit décalage en plafond) puis descente verticale et raccord sur le connecteur de l'émetteur."""
    xy2 = decale(xy, direction, sens)
    if xy2 != xy:
        tube(id_sys, materiau, xyz(xy[0], xy[1], z_haut), xyz(xy2[0], xy2[1], z_haut), dn, niveau, sens)
    p_haut = xyz(xy2[0], xy2[1], z_haut)
    p_bas = xyz(xy2[0], xy2[1], z_bas)
    tube(id_sys, materiau, p_haut, p_bas, dn, niveau, sens)
    inst = POSES.get(emetteur)
    if inst is None:
        return
    classe = "SupplyHydronic" if sens == "A" else "ReturnHydronic"
    cible = [c for c in connecteurs(inst) if str(getattr(c, "PipeSystemType", "")) == classe]
    if not cible:
        log("   ", emetteur, ": pas de connecteur", classe, "-> raccord final à faire")
        return
    pi = tube(id_sys, materiau, p_bas, cible[0].Origin, dn, niveau, sens)
    if pi is not None:
        for c in connecteurs(pi):
            if c.Origin.DistanceTo(cible[0].Origin) < 1e-3:
                try:
                    c.ConnectTo(cible[0])
                except Exception:
                    pass


def etape_reseau():
    h = CFG["hauteurs_m"]
    pos_rad = dict((r["id"], (r["position_m"]["x"], r["position_m"]["y"])) for r in MODELE["radiateurs"])
    pos_cta = dict((c["id_cta"], (c.get("x_m"), c.get("y_m"))) for c in MODELE.get("cta", []))
    n = 0
    with Etape("reseau"):
        z0 = z_niveau("RDC")
        for t in GEOM["troncons"]:
            if not t["pts_m"]:
                continue
            circ = t["circuit"]
            base = "CH-PERI" if circ.startswith("PERI") else "CH-" + circ
            pts = nettoyer(t["pts_m"], CFG.get("longueur_min_m", 0.05))
            for sens, z in (("A", h["aller_plafond"]), ("R", h["retour_plafond"])):
                for a, b in zip(pts, pts[1:]):
                    if tube(base + "-" + sens, t["materiau"], xyz(a[0], a[1], z0 + z), xyz(b[0], b[1], z0 + z),
                            t["DN"], "RDC", sens):
                        n += 1
                direction = (pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1]) if len(pts) > 1 else None
                for em in t["emetteurs"]:
                    if em == "MONTEE-CTA-R1":
                        FIN_TRONCON["MONTEE-CTA-R1"] = (pts[-1], direction)
                        continue
                    if t["troncon_id"].startswith("B-") or len(t["emetteurs"]) == 1:
                        FIN_TRONCON[em] = (pts[-1], direction)
                        z_bas = h["cta_rdc"] + 0.5 if em.startswith("CTA") else h["raccord_radiateur"]
                        chute_vers(base + "-" + sens, t["materiau"], t["DN"], pts[-1], z0 + z, z0 + z_bas, "RDC",
                                   sens, em, direction)
        raccorder_noeuds()
        log("   canalisations créées :", n)
    return pos_rad, pos_cta


def etape_liens_R1():
    h = CFG["hauteurs_m"]
    rads = dict((r["id"], r) for r in MODELE["radiateurs"])
    z0, z1 = z_niveau("RDC"), z_niveau("R+1")
    n = 0
    with Etape("liens_R1"):
        for t in GEOM["troncons"]:
            if not t["troncon_id"].startswith("V-"):
                continue
            enf = rads.get(t["emetteurs"][0]) if t["emetteurs"] else None
            if enf is None:
                continue
            par = rads.get(enf["raccordement"]["parent_RDC"])
            if par is None:
                continue
            pe = enf["position_m"]
            depart, direction = FIN_TRONCON.get(par["id"], ((par["position_m"]["x"], par["position_m"]["y"]), None))
            for sens, z in (("A", h["aller_plafond"]), ("R", h["retour_plafond"])):
                sys_ = "CH-ELEM-" + sens
                d0 = decale(depart, direction, sens)
                d1 = decale((pe["x"], pe["y"]), direction, sens)
                a = xyz(d0[0], d0[1], z0 + z)
                b = xyz(d1[0], d1[1], z0 + z)
                c = xyz(d1[0], d1[1], z1 + h["raccord_radiateur"])
                if tube(sys_, "cuivre", a, b, t["DN"], "RDC", sens):  # parcours en plafond RDC si pas d'aplomb
                    n += 1
                if tube(sys_, "cuivre", b, c, t["DN"], "RDC", sens):  # montée à travers la réservation
                    n += 1
            if not enf["raccordement"]["statut_aplomb"].startswith("OK"):
                log("   ", enf["id"], ": pas d'aplomb RDC, parcours horizontal provisoire dessiné (D-28)")
        n += colonne_cta_R1(h, z0, z1)
        raccorder_noeuds()
        log("   tubes de liaison R+1 et colonne CTA créés :", n)


def colonne_cta_R1(h, z0, z1):
    """Colonne CTA : du pied (fin du tronçon RDC) jusqu'à la terrasse, puis vers chaque CTA élémentaire."""
    if "MONTEE-CTA-R1" not in FIN_TRONCON:
        log("   pied de colonne CTA introuvable")
        return 0
    pied, direction = FIN_TRONCON["MONTEE-CTA-R1"]
    geo = dict((t["troncon_id"], t) for t in GEOM["troncons"])
    dn_col = (geo.get("CT-R1-MONTEE") or {}).get("DN")
    n = 0
    z_ter = z1 + h["cta_terrasse"] + 0.6
    for sens, z in (("A", h["aller_plafond"]), ("R", h["retour_plafond"])):
        sys_ = "CH-CTA-" + sens
        p0 = decale(pied, direction, sens)
        if tube(sys_, "acier", xyz(p0[0], p0[1], z0 + z), xyz(p0[0], p0[1], z_ter + (0.15 if sens == "R" else 0)),
                dn_col, "RDC", sens):
            n += 1
        for c in MODELE.get("cta", []):
            if c.get("niveau") != "R+1" or "x_m" not in c:
                continue
            dn = (geo.get("CT-R1-NORD" if c["id_cta"].endswith("NORD") else "CT-R1-SUD") or {}).get("DN")
            zz = z_ter + (0.15 if sens == "R" else 0)
            if tube(sys_, "acier", xyz(p0[0], p0[1], zz), xyz(c["x_m"], c["y_m"], zz), dn, "R+1", sens):
                n += 1
            chute_vers(sys_, "acier", dn, (c["x_m"], c["y_m"]), zz, z1 + h["cta_terrasse"] + 0.5, "R+1", sens,
                       c["id_cta"], (c["x_m"] - p0[0], c["y_m"] - p0[1]))
    return n


# ---------------------------------------------------------------- principal
ETAPES = {"niveaux": etape_niveaux, "systemes": etape_systemes, "types_canalisation": etape_types_canalisation,
          "filtres": etape_filtres, "radiateurs": etape_radiateurs, "cta": etape_cta,
          "reservations": etape_reservations, "reseau": etape_reseau, "liens_R1": etape_liens_R1}


def main():
    tg = TransactionGroup(doc, "CVC - modèle chauffage depuis JSON")
    tg.Start()
    log("Projet :", doc.Title, "- dry_run =", CFG.get("dry_run", True))
    log("Modèle :", MODELE["meta"].get("genere_le"), "-", len(MODELE["radiateurs"]), "radiateurs,",
        len(MODELE.get("cta", [])), "CTA,", len(GEOM["troncons"]), "tronçons")
    for e in CFG["etapes"]:
        try:
            ETAPES[e]()
        except Exception as ex:
            log("ÉCHEC étape", e, ":", ex)
    if CFG.get("dry_run", True):
        tg.RollBack()
        log("dry_run : toutes les créations ont été annulées (passer dry_run à false pour valider)")
    else:
        tg.Assimilate()
        log("Modèle validé.")
    with io.open(os.path.join(ICI, "journal_build.txt"), "w", encoding="utf-8") as f:
        f.write(u"\n".join(JOURNAL))
    log("Journal :", os.path.join(ICI, "journal_build.txt"))


main()
