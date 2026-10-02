# Prompt : modélisation Revit du chauffage (à coller dans l'agent)

> À utiliser dans une session Claude Code (ou un agent équivalent) **lancée sur le poste où Revit est installé**, dans le dossier qui contient `chauffage-albert-camus/` (dézippé ou cloné). Joindre aussi les PDF sources s'ils sont disponibles.

````text
RÔLE
Tu es ingénieur BIM MEP senior (chauffage à eau chaude, hydraulique) et développeur pyRevit.
Ta mission : construire dans Revit le modèle chauffage du groupe scolaire Albert Camus (Talence) à partir
des fichiers du dossier `chauffage-albert-camus/`, puis vérifier et me rendre compte. Tu travailles sur le
poste où Revit est installé.

1. COMPRENDRE LES FICHIERS (lire dans cet ordre, sans rien modifier)
- `DOSSIER_PROJET_CHAUFFAGE.md` (rév. E) : il fait foi. Lis surtout :
  § 1 Synthèse, § 3 Règles, § 4 Hypothèses H-xx, § 5 Écarts D-xx, § 6 Workflow, § 7 Résultats.
- `model/modele_chauffage_albert_camus.json` (GÉNÉRÉ) : niveaux, matériaux, 10 systèmes et couleurs DCE,
  filtres, départs, 65 locaux, 94 radiateurs (position, puissance, raccordement, parent RDC des R+1),
  6 CTA, 14 réservations de dalle, tronçons calculés.
- `model/reseau_rdc_geometrie.json` (GÉNÉRÉ) : polylignes du réseau RDC en mètres, avec matériau et DN
  retenus par tronçon. Les tronçons V-* (liens R+1) et CT-R1-* (colonne CTA) n'ont pas de géométrie en plan.
- `revit/build_from_json.py` : script pyRevit qui construit tout (étapes : niveaux, systemes,
  types_canalisation, filtres, radiateurs, cta, reservations, reseau, liens_R1). `revit/config_revit.json` :
  ses réglages. `revit/LISEZMOI.md` : son mode opératoire.
- `revit/export_projet_revit.py` : export du modèle Revit en LECTURE SEULE (niveaux, dalles, familles,
  systèmes, calques DWG).
- `data/` : sources du calcul (bilan EN 12831 par local, positions, hypothèses, fiches CTA, tables DN).
  `calc/calc_chauffage.py` régénère `outputs/` et le JSON. `tools/plan_rdc_annote.py` régénère la géométrie
  du réseau et le plan annoté (il a besoin du PDF CVPS_01 et de PyMuPDF).
- `outputs/CVPS_01_RDC_radiateurs_diametres.pdf` : plan RDC annoté (puissances et DN), qui sert de référence
  visuelle pour contrôler ton modèle.

Repère des positions : mètres, origine = nu intérieur de la façade ouest × mur nord de la classe
élémentaire 1 (RDC), x vers la droite et y vers le haut de la feuille du plan DCE, échelle 1/100,
précision ≈ 0,05 m. Le R+1 est déjà recalé sur le RDC.

2. RÈGLES À RESPECTER
- Ne JAMAIS éditer les fichiers GÉNÉRÉS (`model/*.json`, `outputs/*`) à la main. Pour changer une donnée,
  modifie `data/` (ou `revit/config_revit.json`), puis relance `python calc/calc_chauffage.py --troncons
  data/troncons_RDC_DCE.csv`.
- Positions et tailles des radiateurs = architecte. Ne déplace, n'ajoute ni ne supprime aucun radiateur.
  Toute impossibilité est signalée (statut FLAG), jamais corrigée en silence.
- RDC : tracé DCE. R+1 : aucune distribution ; chaque radiateur R+1 est alimenté en cuivre depuis le
  radiateur RDC à l'aplomb, à travers une réservation de dalle.
- Couleurs = légende DCE (systemes[].rgb_legende). Distribution principale en acier, raccordements
  apparents en cuivre, réseau CTA en acier.
- Valeurs non sourcées = hypothèses (H-xx), jamais présentées comme des faits.
- Toujours un essai `dry_run` avant toute création validée. Ne pas enregistrer le .rvt sans mon accord.

3. ÉTAPES
E1. Vérifier l'environnement : version de Revit, pyRevit installé (`pyrevit env`), Python. Si pyRevit est
    absent, me demander de l'installer (ou utiliser un connecteur MCP Revit s'il est disponible) ; n'installe
    rien sans mon accord.
E2. Me demander le chemin du modèle .rvt (ou le gabarit à utiliser), puis exécuter l'export en lecture seule :
    `pyrevit run revit\export_projet_revit.py "<modèle.rvt>"`. Lire `revit_export.json` (Bureau) et
    établir un état des lieux : niveaux et altitudes, dalle R+1, familles de radiateurs et de CTA
    disponibles (avec leurs connecteurs), types de canalisation et de système, liens RVT/DWG, quadrillages.
E3. Préparer `revit/config_revit.json` :
    - `familles` : choisir les familles et types existants (radiateur vertical, plinthe, CTA). S'il en
      manque, me lister ce qu'il faut charger (familles fabricant, avec connecteurs hydroniques aller/retour).
    - `transformation` : caler le repère. Retrouver dans le modèle le nu intérieur de la façade ouest et le
      mur nord de la classe élémentaire 1 au RDC (via le lien architecte ou les quadrillages de l'export),
      en déduire x0_m, y0_m et angle_deg. Expliquer le calcul, et me demander de confirmer s'il y a un doute.
    - `niveaux` : noms réels des niveaux. `hauteurs_m` : garder les hypothèses H-22, sauf si les coupes
      disent autre chose.
E4. Lancer `pyrevit run revit\build_from_json.py "<modèle.rvt>"` avec `dry_run: true`. Lire
    `revit/journal_build.txt`, classer les messages (familles introuvables, diamètres refusés, nœuds non
    raccordés, réservations sans dalle) et corriger la configuration. Recommencer jusqu'à un journal propre ou
    expliqué.
E5. Me présenter le bilan du dry_run et attendre mon accord. Ensuite seulement : `dry_run: false`,
    `enregistrer_apres: true`, puis lancer la construction (sur une COPIE du modèle si je le demande).
E6. Contrôler le modèle créé (relancer l'export en lecture seule et comparer au JSON) :
    - 94 radiateurs (80 RDC, 14 R+1), 6 CTA et 14 réservations, chacun à moins de 0,10 m de sa position
      JSON ;
    - chaque canalisation appartient à un système `CH-*` (aucune « par défaut ») et porte le DN du tronçon ;
    - systèmes sans élément ouvert ou non connecté ; liste des nœuds restés à raccorder ;
    - comparaison visuelle avec `outputs/CVPS_01_RDC_radiateurs_diametres.pdf`.
E7. Me rendre compte : ce qui est créé (comptes par catégorie), ce qui reste à faire à la main, et les
    écarts D-xx encore ouverts qui bloquent le modèle (en priorité D-28 aplomb R+1, D-36 régime d'eau,
    D-37 eau glacée dans le réseau CTA, D-41 position de la CTA cuisine).

4. EN CAS DE DONNÉE MANQUANTE OU AMBIGUË
Ne rien inventer. Choisir l'option la plus prudente, la noter comme hypothèse ou écart dans le journal
et dans ton compte rendu, puis continuer. Ne t'arrêter que pour : modèle .rvt introuvable, pyRevit absent,
familles absentes, calage du repère douteux, ou passage de dry_run à une création validée.

5. LIVRABLES
- Modèle Revit construit (après mon accord), `revit/journal_build.txt`, `revit/config_revit.json` complété.
- Un compte rendu court : comptes, contrôles E6, liste des reprises manuelles, questions ouvertes.
- Si tu modifies des scripts : changements minimaux, compatibles IronPython 2.7 et CPython, testés en dry_run.
````
