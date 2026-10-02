# -*- coding: utf-8 -*-
"""Export LECTURE SEULE du modèle Revit ouvert -> revit_export.json

À exécuter dans Revit via pyRevit (ou RevitPythonShell). Aucune transaction : le modèle n'est pas modifié.
Le fichier produit sert à vérifier les hypothèses du dossier (niveaux, positions des radiateurs,
espaces, dalles, systèmes, calques DWG) et à recaler model/modele_chauffage_albert_camus.json.
Compatible IronPython 2.7 et CPython 3 (pas de f-strings).
"""
import io
import json
import os

from Autodesk.Revit.DB import (BuiltInCategory, BuiltInParameter, FilteredElementCollector, Floor, Grid,
                               ImportInstance, Level, LocationCurve, LocationPoint, ParameterFilterElement,
                               RevitLinkInstance)
from Autodesk.Revit.DB.Plumbing import Pipe, PipeType, PipingSystemType

try:
    doc = __revit__.ActiveUIDocument.Document  # noqa: F821 (fourni par pyRevit / RPS)
except NameError:
    from pyrevit import revit
    doc = revit.doc

FT = 0.3048  # pied -> m


def m(v):
    return round(v * FT, 3)


def pt(p):
    return [m(p.X), m(p.Y), m(p.Z)]


def name_of(e):
    try:
        return e.Name
    except Exception:
        return None


def param(e, bip):
    p = e.get_Parameter(bip)
    if p is None or not p.HasValue:
        return None
    return p.AsValueString() or p.AsString()


def collect(cat=None, cls=None):
    c = FilteredElementCollector(doc)
    if cls is not None:
        c = c.OfClass(cls)
    if cat is not None:
        c = c.OfCategory(cat)
    return c.WhereElementIsNotElementType().ToElements() if cls is None else c.ToElements()


def location(e):
    loc = e.Location
    if isinstance(loc, LocationPoint):
        r = {"point_m": pt(loc.Point)}
        try:
            r["rotation_deg"] = round(loc.Rotation * 57.29578, 2)
        except Exception:
            pass
        return r
    if isinstance(loc, LocationCurve):
        c = loc.Curve
        return {"start_m": pt(c.GetEndPoint(0)), "end_m": pt(c.GetEndPoint(1)), "length_m": m(c.Length)}
    return {}


def connectors(e):
    out = []
    try:
        cm = e.MEPModel.ConnectorManager if hasattr(e, "MEPModel") and e.MEPModel else e.ConnectorManager
        for c in cm.Connectors:
            d = {"domain": str(c.Domain), "origin_m": pt(c.Origin), "connected": c.IsConnected}
            try:
                d["system_classification"] = str(c.PipeSystemType)
                d["diameter_mm"] = round(c.Radius * 2 * FT * 1000, 1)
            except Exception:
                pass
            out.append(d)
    except Exception:
        pass
    return out


data = {"document": {"title": doc.Title, "path": doc.PathName,
                     "revit_version": doc.Application.VersionName}}

# Points de base
bp = {}
for bic, key in ((BuiltInCategory.OST_ProjectBasePoint, "project_base_point"),
                 (BuiltInCategory.OST_SharedBasePoint, "survey_point")):
    for e in collect(bic):
        try:
            bp[key] = pt(e.Position)
        except Exception:
            bp[key] = None
data["base_points"] = bp

data["levels"] = sorted([{"name": l.Name, "elevation_m": m(l.Elevation)} for l in collect(cls=Level)],
                        key=lambda x: x["elevation_m"])
data["grids"] = [{"name": g.Name, "start_m": pt(g.Curve.GetEndPoint(0)), "end_m": pt(g.Curve.GetEndPoint(1))}
                 for g in collect(cls=Grid)]

data["links_rvt"] = []
for li in collect(cls=RevitLinkInstance):
    t = li.GetTotalTransform()
    data["links_rvt"].append({"name": li.Name, "origin_m": pt(t.Origin),
                              "basis_x": [round(t.BasisX.X, 4), round(t.BasisX.Y, 4)],
                              "loaded": li.GetLinkDocument() is not None})

data["imports_dwg"] = []
for ii in collect(cls=ImportInstance):
    layers = []
    try:
        for sc in ii.Category.SubCategories:
            layers.append(sc.Name)
    except Exception:
        pass
    data["imports_dwg"].append({"name": ii.Category.Name if ii.Category else name_of(ii), "is_link": ii.IsLinked,
                                "layers": sorted(layers)})


def rooms_like(bic):
    out = []
    for r in collect(bic):
        try:
            area = r.Area
        except Exception:
            area = 0
        if not area:
            continue  # non placé / non fermé
        lvl = doc.GetElement(r.LevelId)
        d = {"id": r.Id.IntegerValue, "number": param(r, BuiltInParameter.ROOM_NUMBER),
             "name": param(r, BuiltInParameter.ROOM_NAME), "level": lvl.Name if lvl else None,
             "area_m2": round(area * FT * FT, 2)}
        d.update(location(r))
        out.append(d)
    return out


data["rooms"] = rooms_like(BuiltInCategory.OST_Rooms)
data["spaces"] = rooms_like(BuiltInCategory.OST_MEPSpaces)

# Équipements : radiateurs (équipement mécanique + appareils sanitaires/terminaux nommés « radiat »)
equip = []
for bic in (BuiltInCategory.OST_MechanicalEquipment, BuiltInCategory.OST_DuctTerminal,
            BuiltInCategory.OST_GenericModel, BuiltInCategory.OST_SpecialityEquipment):
    for e in collect(bic):
        try:
            fam = e.Symbol.Family.Name
            typ = e.Symbol.Name if hasattr(e.Symbol, "Name") else name_of(e.Symbol)
        except Exception:
            fam, typ = None, name_of(e)
        label = (str(fam) + " " + str(typ)).lower()
        if bic != BuiltInCategory.OST_MechanicalEquipment and "radiat" not in label:
            continue
        lvl = doc.GetElement(e.LevelId) if e.LevelId else None
        d = {"id": e.Id.IntegerValue, "category": e.Category.Name, "family": fam, "type": typ,
             "level": lvl.Name if lvl else None,
             "offset_m": None, "host": name_of(e.Host) if getattr(e, "Host", None) else None,
             "connectors": connectors(e)}
        off = e.get_Parameter(BuiltInParameter.INSTANCE_ELEVATION_PARAM)
        if off and off.HasValue:
            d["offset_m"] = m(off.AsDouble())
        try:
            sp = e.Space
            d["space"] = param(sp, BuiltInParameter.ROOM_NUMBER) if sp else None
        except Exception:
            pass
        d.update(location(e))
        equip.append(d)
data["equipment"] = equip

# Dalles (épaisseur utile pour les réservations R+1)
floors = []
for f in collect(cls=Floor):
    lvl = doc.GetElement(f.LevelId)
    th = f.get_Parameter(BuiltInParameter.FLOOR_ATTR_THICKNESS_PARAM)
    floors.append({"id": f.Id.IntegerValue, "type": name_of(f.FloorType), "level": lvl.Name if lvl else None,
                   "thickness_m": m(th.AsDouble()) if th and th.HasValue else None})
data["floors"] = floors

# Canalisations
data["pipe_types"] = [name_of(t) for t in collect(cls=PipeType)]
sys_types = []
for st in collect(cls=PipingSystemType):
    d = {"name": name_of(st), "classification": str(st.SystemClassification),
         "abbreviation": param(st, BuiltInParameter.RBS_SYSTEM_ABBREVIATION_PARAM)}
    try:
        c = st.LineColor
        d["line_rgb"] = [c.Red, c.Green, c.Blue]
    except Exception:
        pass
    sys_types.append(d)
data["piping_system_types"] = sys_types

pipes = []
for p in collect(cls=Pipe):
    st = doc.GetElement(p.get_Parameter(BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM).AsElementId())
    d = {"id": p.Id.IntegerValue, "type": name_of(p.PipeType), "system_type": name_of(st) if st else None,
         "system_name": param(p, BuiltInParameter.RBS_SYSTEM_NAME_PARAM),
         "diameter_mm": round(p.Diameter * FT * 1000, 1)}
    d.update(location(p))
    pipes.append(d)
data["pipes"] = pipes

data["view_filters"] = [name_of(f) for f in collect(cls=ParameterFilterElement)]

data["summary"] = {k: len(v) for k, v in data.items() if isinstance(v, list)}

out_dir = os.path.join(os.path.expanduser("~"), "Desktop")
if not os.path.isdir(out_dir):
    out_dir = os.path.expanduser("~")
out = os.path.join(out_dir, "revit_export.json")
with io.open(out, "w", encoding="utf-8") as f:
    txt = json.dumps(data, ensure_ascii=False, indent=1)
    f.write(txt if isinstance(txt, type(u"")) else txt.decode("utf-8"))
print("Export écrit : " + out)
print(json.dumps(data["summary"]))
