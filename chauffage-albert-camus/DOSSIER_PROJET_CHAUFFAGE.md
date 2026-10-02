# Dossier de démarrage : chauffage à eau chaude du groupe scolaire Albert Camus (Talence)

**Réhabilitation et extension du groupe scolaire Albert Camus, 33400 Talence**
Lot CVC-PLB. Phase de travail : passage DCE vers EXE. Dossier établi le 02/10/2026.

> **Objet.** Ce fichier contient tout ce qu'il faut pour lancer le projet dans Claude Code ou Codex :
> les données extraites des 5 pièces fournies, les règles d'ingénierie, les hypothèses (sourcées et
> ajustables), les écarts relevés, le workflow BIM Revit complet, les premiers résultats de calcul et
> un **prompt prêt à coller** (§ 8).
>
> **Statut des résultats.** Tous les chiffres de puissance sont **PROVISOIRES**. Le bilan thermique fourni
> ne contient **aucune puissance par local** (voir D-01). Le moteur de calcul est prêt : il suffit de
> renseigner `P_base_W_rapport` dans l'inventaire et de relancer le calcul pour obtenir les valeurs définitives.

---

## 0. Mode d'emploi rapide

```bash
cd chauffage-albert-camus
python3 calc/calc_chauffage.py                 # recalcule tout -> outputs/*.csv
python3 -m unittest calc/test_calc.py          # contrôles du moteur
```

| Pour…                                   | modifier                                              | puis |
|-----------------------------------------|-------------------------------------------------------|------|
| changer le régime d'eau, θint, n, rugosité… | `data/hypotheses.json`                             | relancer |
| saisir les vraies puissances par local  | colonne `P_base_W_rapport` de `data/inventaire_locaux_radiateurs_PROVISOIRE.csv` | relancer |
| sélectionner des modèles réels          | créer `data/catalogue_radiateurs.csv` (gabarit fourni) | relancer |
| modifier le tracé ou les longueurs      | remplacer ou ajouter un fichier `data/troncons_*.csv` (export Revit, § 6.6) | relancer avec `--troncons` |

Le tracé et le dimensionnement sont **découplés**. Un nouveau tracé ne demande qu'un nouvel export des tronçons ; les puissances et la sélection des radiateurs restent inchangées.

---

## 1. Synthèse

| Élément | État |
|---|---|
| Inventaire des radiateurs (plans CVPS_01, CVPS_02 et ARCH_03) | **91 radiateurs** répartis dans 57 locaux, dont 86 verticaux ou non spécifiés et 5 plinthes. 26 locaux sont marqués `A_CONFIRMER` |
| Puissances par local | **BLOQUANT** (D-01). Valeurs provisoires = 49,65 W/m² × surface (ratio global du bilan) |
| Majoration +20 % et répartition par radiateur | calculées (règles 1 et 2) |
| Puissance requise au régime projet et équivalent NF EN 442 | calculées avec un régime 55/45/20 **supposé** (H-02) : facteur 0,511 |
| Choix des modèles | **en attente du catalogue fabricant** (D-18). Les P50 requises sont calculées |
| Dimensionnement des réseaux | moteur opérationnel. Esquisse R+1 (circuit ÉLÉM, 14 radiateurs) calculée de bout en bout, du radiateur le plus éloigné jusqu'au pied de colonne |
| Circuit critique | R+1 ÉLÉM : **R1-01-a** (classe élém. 5, radiateur en façade), 51,5 m aller, ΔP = 17,2 kPa depuis le pied de colonne |
| Départs en chaufferie (provisoire) | ÉLÉM 48,1 kW → DN50 · MAT 47,8 kW → DN50 · PÉRI 13,9 kW → DN32 · RESTAU 5,6 kW → DN20 · CTA : charge inconnue (D-17) |

---

## 2. Données extraites des fichiers fournis

### 2.1 Pièces fournies

| Réf. | Fichier | Contenu utile |
|---|---|---|
| F1 | `CVPS_01-Plan_de_reseau_de_chauffage_RDC.pdf` | Plan de principe chauffage du RDC, DCE ind. 0 du 27/03/2026, BE Vivien. Tracé des 4 départs, radiateurs, chaufferie, légende. Échelle 1/100 vérifiée par mesure |
| F2 | `CVPS_02-Plan_de_reseau_de_chauffage_R1.pdf` | Plan de principe chauffage du R+1, DCE ind. 0. Réseau ÉLÉM seul, plus un monosplit Daikin |
| F3 | `2026-09-22_EXE_..._BILAN_THERMIQUE_..._EN12831_ind-A.pdf` | Bilan thermique NF EN 12831. **3 pages, totaux seulement** |
| F4 | `ARCH_03_-_Plan_detage.pdf` | Plan architecte de l'**étage seul**, DCE ind. A, mars 2026, 1/100. Noms, codes et surfaces des locaux, mentions « radiateur à eau » |
| F5 | Photo de la note « Dimensionnement réseau hydraulique » | Tableau DN / Øint / V / Qv / puissance pour ΔT = 3, 5, 15 et 20 °C, colonne ΔT = 10 °C ajoutée à la main, mention manuscrite « 1 mCE = 10 kPa » |

### 2.2 Bilan thermique (F3) : contenu intégral exploitable

- Département 33 (Gironde), altitude 9 m, zone climatique **H2c**, θe base = **−5 °C**, θe moyenne = 12 °C
- Calcul selon **NF EN 12831**, bâtiment neuf (SRT : bâtiment neuf)
- **Totalisation** : surface 2 673,97 m², volume 8 369,8 m³, **déperditions 132 765 W**, **puissance installée 194 266 W**, soit un rapport de 1,463 lié à la surpuissance de relance d'après le titre du fichier
- **Aucun tableau par local** (voir D-01)
- Ratio global : 132 765 / 2 673,97 = **49,65 W/m²**, soit 15,86 W/m³

### 2.3 Plans CVC DCE (F1 et F2)

**Les 4 départs** sur la nourrice de distribution en chaufferie, lus de gauche à droite : *Départ Admin / Péri*, *Départ Élémentaire*, *Départ CTA*, *Départ Maternelle*.

| Circuit | Système (légende F1/F2) | Couleur aller | Couleur retour | Desserte constatée |
|---|---|---|---|---|
| **MAT** | RESEAU EAU DE CHAUFFAGE MAT ALLER / RETOUR | rouge | magenta | Aile maternelle (classes 1 à 6, siestes, motricité), office, laverie, vestiaires, buanderie |
| **ÉLÉM** | … ELEM ALLER / RETOUR | brun-orange | orange | Aile élémentaire RDC, salle polyvalente, **tout le R+1** par une colonne montante au droit du wc élém. 5 |
| **PÉRI** (Admin/Péri) | … PERI ALLER / RETOUR | bordeaux | rouge dans la légende, **violet sur le plan** (D-15) | Direction, enseignants, psychologue, RASED, animateurs, bibliothèque, ATSEM, et la restauration via des **V2V motorisées « réseaux restauration »** (D-06) |
| **CTA** | … CTA ALLER / RETOUR | vert foncé | vert | Batteries chaudes des CTA (locaux CTA du RDC et CTA en terrasse au R+1) |

- **Modes de pose** donnés par la légende, avec 3 types de trait par système : *plinthe*, *dalle / enterré*, *plafond*
- **Équipements de production** (F1, chaufferie) :
  - PAC eau/eau **AERMEC WRL 300** (1 320 × 845 × 1 380 mm, 381 kg à vide) sur sondes géothermiques de 200 m chacune
  - échangeur géothermique, regard et nourrices de géothermie à la charge du lot forage
  - ballon tampon PAC 500 L (Atlantic Corprimo, 1 950 × Ø650)
  - ballon tampon PAC 750 L (Atlantic Corklim, 2 000 × Ø900)
  - vases d'expansion, **bouteille de mélange**, filtre magnétique, nourrice 4 départs avec pompes
  - réutilisation de la VB existante
- **Émetteurs** : symbole « RADIATEUR A EAU ». Libellés « **Radiateur vertical 1500x750** » (13 étiquettes au RDC) et « **Radiateur plinthe** » (5 étiquettes, restauration). Les radiateurs du R+1 ne sont pas étiquetés ; leur symbole mesure environ 1,0 m
- Les mentions « +3 °C » et « +65 °C » du RDC concernent les équipements de cuisine (chambres froides, maintien en température). **Elles ne donnent pas le régime de chauffage.**

### 2.4 Plan architecte R+1 (F4)

Il couvre l'aile élémentaire du R+1. Les radiateurs dessinés (« radiateur à eau ») sont repris en § 7.1, lignes R1-01 à R1-10. Locaux sans radiateur : wc enseignant 2 (B14, 5,86 m²), ménage 3 (B33, 5,56 m²), LT (2,41 m²), circulations et escaliers.

### 2.5 Note de méthode (F5) : autorité principale

Le tableau donne, pour chaque DN, le **débit maximal admissible** (Qv = π/4 · Øint² · V_max) et la puissance transportable P = 1,163 · Qv · ΔT. Dans cette formule, P est en kW, Qv en m³/h et ΔT en K. Cette relation a été vérifiée sur toutes les lignes : par exemple DN15 → 0,249 m³/h × 1,163 × 3 = 0,87 kW, comme imprimé.

**Règle appliquée.** Pour chaque tronçon, on cumule les puissances en remontant du radiateur le plus éloigné vers la source. On calcule ensuite Qv = P / (1,163·ΔT), puis on retient le **plus petit DN dont Qv_max ≥ Qv**. Cela revient à respecter la vitesse maximale du tableau. Les hauteurs manométriques sont converties avec 1 mCE = 10 kPa, comme dans la note.

La colonne ΔT = 10 °C manuscrite est recalculée exactement dans `outputs/03_table_DN_regime_projet.csv` (§ 7.3).

---

## 3. Règles d'ingénierie appliquées

| # | Règle | Implémentation |
|---|---|---|
| 1 | Puissance du local × **1,20** avant toute sélection | `P_majoree = P_base × majoration_securite` (hypotheses.json) |
| 2 | Si le local a n ≥ 2 radiateurs, la puissance majorée est **répartie à parts égales** | `P_par_radiateur = P_majoree / nb_rad`. Chaque radiateur est sélectionné pour sa part |
| 3 | Position et taille suivent l'architecte. Si le radiateur sélectionné **ne rentre pas**, il est **signalé** et une alternative est proposée | statut `FLAG ne rentre pas…`. Aucun déplacement automatique. Alternatives en § 6.4 |
| 4 | Tracé selon le DCE, recalculable | tronçons exportés de Revit vers le moteur, puis réinjection (§ 6.6 et 6.7) |
| 5 | Dimensionnement **du radiateur le plus éloigné vers la source** | cumul en post-ordre sur l'arbre des tronçons, puis chemin critique = ΣΔP maximal |

**Formules (NF EN 442-2)**

- ΔT_lm = (θ_aller − θ_retour) / ln[(θ_aller − θ_i) / (θ_retour − θ_i)]
- P_régime = P50 · (ΔT_lm / 49,83)^n, où 49,83 K est ΔT_lm aux conditions 75/65/20
- P50_requise = P_par_radiateur / (ΔT_lm / 49,83)^n

---

## 4. Hypothèses, toutes ajustables dans `data/hypotheses.json`

| Id | Hypothèse | Valeur | Source / justification |
|---|---|---|---|
| H-01 | Puissance de base provisoire par local | 49,65 W/m² × surface | Totalisation F3 (132 765 W / 2 673,97 m²). **À remplacer** par les puissances par local |
| H-02 | Régime d'eau | **55/45 °C** (ΔT 10 K) | Cohérent avec la colonne ΔT = 10 °C ajoutée sur F5 et avec une production par PAC. **À confirmer** : CCTP et température de départ maximale sur la fiche AERMEC WRL 300 |
| H-03 | Température intérieure θi | 20 °C | Référence NF EN 442-2. Remplacer par la θint du bilan, local par local |
| H-04 | Exposant n | 1,30 | Équation caractéristique NF EN 442-2. La valeur réelle figure sur la fiche fabricant |
| H-05 | Matériau et rugosité | acier noir, ε = 0,045 mm | Désignations 15/21… de type NF EN 10255. Matériau non précisé sur le DCE |
| H-06 | Pertes singulières | 30 % des pertes linéaires | Forfait d'avant-projet, à remplacer par Σζ issus de Revit |
| H-07 | ΔP terminal (robinet thermostatique, té de réglage, radiateur) | 10 kPa | À remplacer par les données fabricant (robinets NF EN 215 : Kv et préréglage) |
| H-08 | Bitube : longueur retour = longueur aller | ×2 | Tracé DCE aller/retour parallèle |
| H-09 | DN minimal de raccordement | DN15 | Usage |
| H-10 | Seuil d'alerte J | 200 Pa/m | Valeur d'usage, **non normative**. Le critère principal reste V_max (F5) |
| H-11 | Type des radiateurs RDC non étiquetés | vertical 1500×750 | Étiquettes F1 |
| H-12 | Point de départ du R+1 | colonne montante au droit du wc élém. 5 | Symbole de montée sur F2 et F1 |

**Sensibilité au régime** (facteur P_régime / P50, n = 1,3)

| Régime | θi = 20 °C | θi = 19 °C |
|---|---|---|
| 45/35 | 0,297 | 0,317 |
| 50/40 | 0,401 | 0,422 |
| **55/45 (H-02)** | **0,511** | 0,533 |
| 60/50 | 0,626 | 0,650 |
| 70/60 | 0,871 | 0,897 |

---

## 5. Écarts, lacunes et discordances

Pour chaque écart, l'hypothèse retenue permet de poursuivre. Tout est relu en une seule passe.

| Id | Gravité | Constat | Hypothèse retenue pour avancer |
|---|---|---|---|
| D-01 | **BLOQUANT** | Le bilan EN 12831 (F3) ne contient que la page de garde, les données climatiques et la **totalisation du bâtiment**. Aucune puissance par local | H-01 : ratio 49,65 W/m² × surface. Demander l'édition complète (« déperditions par local »). Le moteur bascule automatiquement sur `P_base_W_rapport` dès qu'il est renseigné |
| D-02 | Majeur | « Puissance installée » = 194 266 W = 1,463 × déperditions (surpuissance de relance). Ajouter +20 % sur cette valeur reviendrait à cumuler deux marges (×1,76) | La règle 1 s'applique aux **déperditions par local (Φ_HL)**. À valider par le maître d'ouvrage |
| D-03 | Majeur | **Pas de plan architecte du RDC** : ARCH_03 couvre seulement l'étage | Les positions RDC sont lues sur le fond architecte inséré dans CVPS_01 (mentions « radiateur à eau » visibles) |
| D-04 | Majeur | **Régime d'eau absent** de toutes les pièces | H-02 : 55/45 °C, avec la sensibilité du § 4 |
| D-05 | Moyen | Radiateurs dans des locaux **sans nom ou sans surface lisible** : R0-E11, R0-P09, R0-M09, R0-M20, R0-M16, R0-P12, R0-P14 | Puissance non calculée (FLAG). Le local est conservé dans l'inventaire |
| D-06 | Moyen | Réseau restauration : plinthes et V2V motorisées, couleurs absentes de la légende, rattachement de circuit ambigu | Rattaché à PÉRI (sous-circuit « PERI-RESTAU ») |
| D-07 | Moyen (règle 3) | R+1, classes élém. 6 et 7 : ARCH_03 place un radiateur **en façade**, CVPS_02 le place **sur le mur de l'escalier** | Esquisse de tracé sur la position CVC. Arbitrage de l'architecte requis. Aucun déplacement silencieux |
| D-08 | Mineur | Surfaces différentes entre ARCH_03 et le fond CVC : atelier 2 = 30,89 / 30,217 m², atelier 3 = 31,89 / 31,161 m² | Valeurs ARCH_03 retenues (ind. A) |
| D-09 | Moyen | Radiateurs sur cloisons mitoyennes, local d'affectation ambigu : R0-E04 (3e), R0-P05, R0-P07/P08, R0-P11, R0-M03/M06, R0-M12, R0-M21, R0-M22 | Affectation indiquée dans l'inventaire, statut `A_CONFIRMER` |
| D-10 | Mineur | Salle polyvalente « y compris préau » : un radiateur est en limite du préau (50,1 m²) | Préau non chauffé, radiateur affecté à la salle |
| D-11 | Moyen | Locaux **sans radiateur** qui pourraient être chauffés : hall élém. B11 (34,8 m²), hall mat A11 (35,0 m²), wc admin (×2), réserve info, wc enseignant 2, ménages, circulations R+1 | Considérés non chauffés ou traités par CTA. À croiser avec le bilan par local |
| D-12 | Mineur | Note F5 : Øint du 159/4,5 imprimé à 159,3 mm, alors que l'Øint réel vaut environ 150 mm. La capacité est surestimée d'environ 13 % | Valeur de la note conservée, toute sélection en DN150 est signalée. Sans effet ici (départs ≤ DN50) |
| D-13 | Mineur | Colonne ΔT = 10 °C manuscrite arrondie, avec un écart sur DN15 et des valeurs parfois peu lisibles | Recalcul exact par la formule de la note |
| D-14 | Info | 1 mCE = 10 kPa dans la note ; la valeur exacte est 9,81 kPa | Convention de la note conservée (écart < 2 %) |
| D-15 | Mineur | Couleurs : PÉRI retour en violet sur le plan, rouge dans la légende | Les filtres Revit suivent les **noms de systèmes**. Les couleurs sont paramétrables |
| D-16 | Majeur | **Aucune source CAO/BIM** (DWG, RVT, IFC) et aucune hauteur d'étage | Calque PDF à l'échelle 1/100 dans Revit. Demander DWG et RVT au BE et à l'architecte |
| D-17 | Majeur | **Puissances des batteries chaudes CTA inconnues** (CTA 5,0 m², LT CTA 3,7 m², CTA 4,25 m², CTA en terrasse au R+1) | Départ CTA non dimensionnable. Demander le tableau des CTA |
| D-18 | Majeur | **Pas de catalogue fabricant**. Radiateurs R+1 de type non précisé | Calcul de P50_requise. Sélection automatique dès que `catalogue_radiateurs.csv` est fourni |
| D-19 | Info | Codes architecte (B21, A21…) = **types** de locaux, non uniques | Identifiants uniques R0-xx / R1-xx créés |
| D-20 | Moyen | θint par local inconnue | H-03 : 20 °C |
| D-21 | **Risque** | P50 requise ≈ **3,6 kW par radiateur** de classe en 55/45/20 provisoire. Un radiateur vertical de 750 mm de large risque de ne pas suffire | Vérification par catalogue. Alternatives du § 6.4 si FLAG |
| D-22 | Mineur | Matériau des tubes non précisé | H-05 |
| D-23 | Info | Surface des locaux équipés de radiateurs : 1 936 m², soit 72 % des 2 674 m² du bilan | Cohérent avec des circulations et zones CTA non équipées |

---

## 6. Workflow pas à pas

### 6.0 Architecture : une source de vérité, deux mondes

```
  Bilan EN12831 ──┐
  Plans ARCH/CVC ─┼─► data/*.csv + hypotheses.json ──► calc/calc_chauffage.py ──► outputs/*.csv
  Catalogue ──────┘          ▲                                                       │
                             │ export_network.py (pyRevit)            apply_results.py (pyRevit)
                         [ Modèle Revit ] ◄──────────────────────────────────────────┘
```

- **Le calcul est en CPython, bibliothèque standard uniquement.** Il est testable et versionnable, et s'exécute hors Revit comme dans Revit (moteur CPython de pyRevit).
- **Revit sert à la géométrie** et reçoit les résultats (DN, paramètres). L'outil de dimensionnement natif de Revit n'applique pas la méthode F5 ; il ne sert qu'au **contrôle** (§ 6.8).
- Scripting retenu : **pyRevit**, avec des scripts Python en dépôt Git, des boutons et des exécutions répétables. Dynamo reste possible pour des contrôles visuels ponctuels, mais pas pour la chaîne de calcul.

### 6.1 Phase 0 : collecte et préparation

1. Obtenir : l'édition complète du bilan EN 12831 par local (D-01), les DWG ou RVT architecte du RDC et du R+1 (D-03, D-16), le régime d'eau du CCTP et la fiche AERMEC (D-04), le tableau des CTA (D-17) et le catalogue radiateurs retenu (D-18).
2. Faire valider par le maître d'ouvrage la base de la majoration de 20 % (D-02).

### 6.2 Phase 1 : extraction et inventaire

1. Partir de l'inventaire `data/inventaire_locaux_radiateurs_PROVISOIRE.csv` (déjà extrait des PDF).
2. **Contrôle** : compter les blocs « RADIATEUR A EAU » dans les DWG. Avec AutoCAD, `EXTRACTDONNEES` (DATAEXTRACTION) exporte X, Y, rotation, calque et longueur ; le décompte doit être égal à 91 ± les écarts listés.
3. Rapprochement : chaque radiateur doit avoir un local et chaque local du bilan un statut (chauffé ou non). Les écarts restants vont dans la section Écarts.

### 6.3 Phase 2 : puissances (règles 1 et 2)

On renseigne `P_base_W_rapport` à partir du bilan, puis on lance `calc_chauffage.py`. Résultats dans `outputs/01_locaux_puissances.csv` : P_base, P_majorée et P_par_radiateur.

### 6.4 Phase 3 : sélection des radiateurs (règle 3)

1. Créer `data/catalogue_radiateurs.csv` à partir des données **fabricant** au format NF EN 442 : P50 à ΔT 50 K, exposant n, H, L, type. Indiquer la référence et la page du catalogue dans `source_catalogue`.
2. Le moteur retient le plus petit modèle du **type dessiné** (vertical 1500 ou plinthe) dont P_régime ≥ P_par_radiateur et L ≤ L_dispo.
3. Si aucun modèle ne convient, statut **FLAG**. Les alternatives sont proposées dans cet ordre, **jamais appliquées sans accord** :
   - a) même emprise avec plus de panneaux ou d'ailettes (type 22 → 33), ou hauteur supérieure ;
   - b) radiateur supplémentaire dans le local, après accord de l'architecte, en redistribuant à parts égales ;
   - c) relèvement du régime, si la PAC le permet (§ 4, sensibilité) ;
   - d) émetteur basse température à ventilation assistée ;
   - e) revue de la charge du local avec le thermicien.

### 6.5 Phase 4 : modèle Revit (Revit 2024 ou plus récent, hypothèse)

**a. Gabarit**
- Unités : W, m³/h, m/s, Pa, mm.
- Niveaux RDC et R+1, avec les hauteurs à obtenir (D-16).
- Lien du modèle architecte, ou à défaut import du PDF en calque à l'échelle 1/100 (Insérer > PDF).

**b. Espaces MEP**
- Un espace par local de l'inventaire. `Number = id_local`, `Name = local`.

**c. Paramètres partagés** (groupe CVC)

| Paramètre | Catégorie | Contenu |
|---|---|---|
| `CVC_Id_Local` | Espaces, Équipements | id_local |
| `CVC_Circuit` | Équipements, Canalisations, Raccords | MAT, ELEM, PERI, PERI-RESTAU, CTA |
| `CVC_P_Base_W`, `CVC_P_Majoree_W`, `CVC_P_Part_W` | Espaces, Équipements | règles 1 et 2 |
| `CVC_P50_W`, `CVC_n`, `CVC_P_Regime_W`, `CVC_Statut_Selection` | Équipements mécaniques | sélection |
| `CVC_Troncon_Id`, `CVC_P_Cumul_kW`, `CVC_Qv_m3h`, `CVC_V_ms`, `CVC_J_Pa_m`, `CVC_dP_Pa`, `CVC_Critique` | Canalisations | résultats |
| `CVC_Mode_Pose` | Canalisations | plinthe, dalle ou plafond (légende DCE) |

**d. Familles**
- « Radiateur vertical » : équipement mécanique basé sur une face, paramètres H, L, P50, n et 2 connecteurs Hydronic Supply / Hydronic Return.
- « Radiateur plinthe » : longueur paramétrique.
- Utiliser de préférence les familles BIM du fabricant retenu et y ajouter les paramètres partagés.
- Formule de famille possible : `P_Regime = P50 * ((dTlm)/49.83)^n`, avec `dTlm` calculé par la fonction ln() de Revit.

**e. Placement**

Script pyRevit `place_radiators.py` :
1. lit le CSV (X, Y, rotation issus du DWG, ou points cliqués sur le calque) ;
2. place la famille sur la face du mur le plus proche, au niveau du local ;
3. renseigne `CVC_*` ;
4. **ne déplace jamais** un radiateur : si la largeur sélectionnée dépasse L_dispo, il pose `CVC_Statut_Selection = FLAG`.

**f. Systèmes**

| Type de système | Classification |
|---|---|
| `CH-MAT-A` / `CH-MAT-R` | Hydronic Supply / Hydronic Return |
| `CH-ELEM-A` / `CH-ELEM-R` | idem |
| `CH-PERI-A` / `CH-PERI-R` | idem |
| `CH-CTA-A` / `CH-CTA-R` | idem |
| `CH-PRIM-A` / `CH-PRIM-R` | idem (PAC → ballons → bouteille → nourrice) |

**g. Type de canalisation**
- « Acier noir NF EN 10255 », avec un segment dont les Øint sont **ceux du tableau F5**, pour que Revit et le calcul restent cohérents.

**h. Tracé** (règle 4)
- Modéliser selon CVPS_01 et CVPS_02, un système par départ, aller et retour en parallèle.
- Renseigner `CVC_Mode_Pose` d'après le type de trait.

### 6.6 Les 4 départs et les filtres de couleur

- Créer un **filtre de vue par type de système** (règle : *Type de système* égal à `CH-MAT-A`, etc.), soit 8 filtres et 2 de plus pour le primaire.
- Couleurs selon la légende DCE :

| Circuit | Aller | Retour |
|---|---|---|
| MAT | rouge | magenta |
| ÉLÉM | brun | orange |
| PÉRI | bordeaux | rouge |
| CTA | vert foncé | vert |

- **Motif de ligne** par `CVC_Mode_Pose` : continu pour le plafond, tireté pour la dalle, mixte pour la plinthe.
- Filtres de contrôle :
  - `CVC_Statut_Selection` contient « FLAG » → radiateur en rouge plein ;
  - `CVC_Critique = OUI` → tronçons du chemin critique en trait épais.
- Gabarits de vue :
  - `CH - Tous circuits` ;
  - `CH - MAT seul`, `CH - ELEM seul`, `CH - PERI seul`, `CH - CTA seul` (les autres systèmes sont masqués) ;
  - un plan par niveau et par circuit pour le contrôle du tracé.

### 6.7 Phase 5 : calcul du réseau, recalculable (règles 4 et 5)

1. **`export_network.py`** (pyRevit) :
   - Pour chaque système aller, parcourir le graphe des connecteurs (`Connector.AllRefs`) depuis le connecteur de départ de la nourrice.
   - Un **nœud** = té, nourrice ou radiateur. Un **tronçon** = suite de tubes et de coudes entre deux nœuds.
   - Sortie : `data/troncons_<circuit>_<date>.csv` au format de `troncons_R1_ELEM_ESQUISSE.csv` (`circuit; troncon_id; amont_id; longueur_m; zeta_total; radiateurs; dn_impose`), avec la liste des ElementId de chaque tronçon.
   - ζ est pris dans une table par famille de raccord (coude 90°, té passage, té dérivation, réduction). Si ζ manque, le forfait H-06 s'applique.
2. **`calc_chauffage.py --troncons ...`** :
   - cumul des puissances depuis le radiateur le plus éloigné ;
   - Qv → DN (F5) ;
   - V, Re, λ (Colebrook), J, ΔP linéaires et singulières, aller et retour ;
   - chemins source → radiateur, **circuit critique** = ΔP maximal, HMT en mCE ;
   - excès de pression à laminer sur chaque autre radiateur, pour l'équilibrage.
3. **`apply_results.py`** (pyRevit) :
   - écrit le diamètre de chaque tube du tronçon (`RBS_PIPE_DIAMETER_PARAM`) et les paramètres `CVC_*` ;
   - consigne les raccords que Revit n'a pas pu redimensionner.
4. **Re-tracé** : modifier le tracé dans Revit, puis relancer 1 → 2 → 3. Les puissances et la sélection ne bougent pas. Chaque exécution est horodatée dans `outputs/` pour comparer les versions.

### 6.8 Phase 6 : vérifications

| Contrôle | Critère |
|---|---|
| Bilan de puissance | Σ P_part = Σ P_majorée par local, et Σ par circuit = P du départ |
| Vitesse | V ≤ V_max du DN (F5) sur 100 % des tronçons |
| Cumul | P_cumul d'un tronçon = Σ des tronçons aval + radiateurs (contrôle d'arbre, pas de boucle) |
| Connectivité | Chaque radiateur relié à un seul système aller et un seul retour ; aucun « système ouvert » dans Revit |
| Pertes de charge | Rapport *Analyser > Rapport de perte de pression* de Revit comparé au moteur, écart attendu ≤ 15 % |
| Équilibrage | Excès à laminer compatible avec la plage de préréglage des robinets choisis |
| Règle 3 | Liste des FLAG vide, ou chaque FLAG associé à une alternative validée |
| Interférences | Détection de conflits canalisations / structure / gaines |

### 6.9 Phase 7 : livrables

- Nomenclatures Revit : espaces (puissances), équipements mécaniques (radiateurs), canalisations (DN, Qv, V, J, ΔP).
- Plans par circuit.
- Note de calcul générée depuis `outputs/`.
- Liste des écarts mise à jour.

---

## 7. Nomenclatures et résultats de calcul (PROVISOIRES, H-01 à H-12)

### 7.1 Puissances par local (règles 1 et 2) : `outputs/01_locaux_puissances.csv`

| id_local | niveau | circuit | local | code_archi | surface_m2 | nb_rad | P_base_W | P_majoree_W | P_par_radiateur_W | statut |
|---|---|---|---|---|---|---|---|---|---|---|
| R1-01 | R+1 | ELEM | salle de classe élémentaire 5 | B21 | 62.51 | 2 | 3104 | 3724 | 1862 | OK |
| R1-02 | R+1 | ELEM | atelier élémentaire 2 | B22 | 30.89 | 1 | 1534 | 1840 | 1840 | OK |
| R1-03 | R+1 | ELEM | stockage 2 | B31 | 7.56 | 1 | 375 | 450 | 450 | OK |
| R1-04 | R+1 | ELEM | wc élém 4 | B25 | 13.35 | 1 | 663 | 795 | 795 | OK |
| R1-05 | R+1 | ELEM | salle de classe élémentaire 6 | B21 | 62.14 | 2 | 3085 | 3702 | 1851 | A_CONFIRMER |
| R1-06 | R+1 | ELEM | salle de classe élémentaire 7 | B21 | 62.14 | 2 | 3085 | 3702 | 1851 | A_CONFIRMER |
| R1-07 | R+1 | ELEM | atelier élémentaire 3 | B22 | 31.89 | 1 | 1583 | 1900 | 1900 | OK |
| R1-08 | R+1 | ELEM | stockage 3 | B31 | 7.55 | 1 | 375 | 450 | 450 | OK |
| R1-09 | R+1 | ELEM | wc élém 5 | B25 | 13.54 | 1 | 672 | 807 | 807 | OK |
| R1-10 | R+1 | ELEM | salle de classe élémentaire 8 | B21 | 62.29 | 2 | 3093 | 3711 | 1856 | OK |
| R0-E01 | RDC | ELEM | salle de classe élémentaire 1 | B21 | 62.93 | 2 | 3124 | 3749 | 1875 | OK |
| R0-E02 | RDC | ELEM | atelier élémentaire 1 (nom tronqué) | B22 | 30.19 | 1 | 1499 | 1799 | 1799 | A_CONFIRMER |
| R0-E03 | RDC | ELEM | stockage 1 | B31 | 7.56 | 1 | 375 | 450 | 450 | OK |
| R0-E04 | RDC | ELEM | salle de classe élémentaire 2 | B21 | 62.03 | 3 | 3080 | 3696 | 1232 | A_CONFIRMER |
| R0-E05 | RDC | ELEM | wc élémentaire (grand) | B25 | 31.53 | 2 | 1565 | 1879 | 939 | OK |
| R0-E06 | RDC | ELEM | salle de classe élémentaire 3 | B21 | 60.10 | 2 | 2984 | 3581 | 1790 | OK |
| R0-E07 | RDC | ELEM | salle de classe élémentaire 4 | B21 | 62.14 | 2 | 3085 | 3702 | 1851 | OK |
| R0-E08 | RDC | ELEM | salle polyvalente / activités périscolaires élémentaires | ?24 | 124.30 | 2 | 6171 | 7406 | 3703 | A_CONFIRMER |
| R0-E09 | RDC | ELEM | rangement (6,6 m²) | B24 | 6.60 | 1 | 328 | 393 | 393 | A_CONFIRMER |
| R0-E10 | RDC | ELEM | laverie élémentaire | ? | 5.60 | 1 | 278 | 334 | 334 | A_CONFIRMER |
| R0-E11 | RDC | ELEM | dégagement près wc prof élé (non nommé) | ? |  | 1 |  |  |  | A_CONFIRMER |
| R0-P01 | RDC | PERI | wc élémentaire (14,9 m²) | B25 | 14.90 | 1 | 740 | 888 | 888 | OK |
| R0-P02 | RDC | PERI | rangement (13,0 m²) | B24 | 13.02 | 1 | 646 | 776 | 776 | OK |
| R0-P03 | RDC | PERI | direction élém | B12 | 12.70 | 1 | 631 | 757 | 757 | OK |
| R0-P04 | RDC | PERI | salle des enseignants | B13 | 24.43 | 1 | 1213 | 1456 | 1456 | OK |
| R0-P05 | RDC | PERI | psychologue | C2 | 12.80 | 1 | 636 | 763 | 763 | A_CONFIRMER |
| R0-P06 | RDC | PERI | direction périsco | ?3 | 15.00 | 1 | 745 | 894 | 894 | OK |
| R0-P07 | RDC | PERI | salle des animateurs | ?4 | 26.69 | 3 | 1325 | 1590 | 530 | A_CONFIRMER |
| R0-P08 | RDC | PERI | salle RASED | ?3 | 24.47 | 1 | 1215 | 1458 | 1458 | A_CONFIRMER |
| R0-P09 | RDC | PERI | hall / entrée périsco (non chiffré) | ? |  | 1 |  |  |  | A_CONFIRMER |
| R0-P10 | RDC | PERI | salle de service des ATSEM et enseignants | A13 | 28.40 | 1 | 1410 | 1692 | 1692 | OK |
| R0-P11 | RDC | PERI | bibliothèque | ?1 | 60.89 | 3 | 3023 | 3628 | 1209 | A_CONFIRMER |
| R0-P12 | RDC | PERI-RESTAU | cantine élémentaire / zone de self | ? |  | 3 |  |  |  | A_CONFIRMER |
| R0-P13 | RDC | PERI-RESTAU | cantine maternelle | E1 | 93.55 | 2 | 4645 | 5574 | 2787 | A_CONFIRMER |
| R0-P14 | RDC | PERI-RESTAU | salle des agents | E8 |  | 1 |  |  |  | A_CONFIRMER |
| R0-M01 | RDC | MAT | direction mat | A12 | 12.70 | 1 | 631 | 757 | 757 | OK |
| R0-M02 | RDC | MAT | wc maternelle (27,1 m²) | A24 | 27.12 | 2 | 1347 | 1616 | 808 | OK |
| R0-M03 | RDC | MAT | salle de motricité / activités périscolaires maternelles | A23 | 172.57 | 3 | 8568 | 10282 | 3427 | A_CONFIRMER |
| R0-M04 | RDC | MAT | salle de sieste 1 | A22 | 60.26 | 2 | 2992 | 3590 | 1795 | OK |
| R0-M05 | RDC | MAT | salle de classe maternelle 1 | A21 | 60.28 | 2 | 2993 | 3591 | 1796 | OK |
| R0-M06 | RDC | MAT | salle de classe maternelle 3 | A21 | 60.49 | 3 | 3003 | 3604 | 1201 | A_CONFIRMER |
| R0-M07 | RDC | MAT | salle de classe maternelle 4 | A21 | 60.49 | 2 | 3003 | 3604 | 1802 | OK |
| R0-M08 | RDC | MAT | wc mat 3 | A14 | 8.94 | 1 | 444 | 533 | 533 | OK |
| R0-M09 | RDC | MAT | circulation maternelle (non chiffrée) | ? |  | 2 |  |  |  | A_CONFIRMER |
| R0-M10 | RDC | MAT | salle de classe maternelle 2 | A21 | 60.28 | 2 | 2993 | 3591 | 1796 | OK |
| R0-M11 | RDC | MAT | salle de sieste 2 | A22 | 60.26 | 2 | 2992 | 3590 | 1795 | OK |
| R0-M12 | RDC | MAT | LT eau / wc maternelle 4 | A24 | 24.42 | 1 | 1212 | 1455 | 1455 | A_CONFIRMER |
| R0-M13 | RDC | MAT | salle de classe maternelle 5 | A21 | 60.49 | 2 | 3003 | 3604 | 1802 | OK |
| R0-M14 | RDC | MAT | salle de classe maternelle 6 (nom illisible) | A21 | 59.38 | 2 | 2948 | 3538 | 1769 | A_CONFIRMER |
| R0-M15 | RDC | MAT | office cuisine élé | E4 | 25.84 | 1 | 1283 | 1540 | 1540 | OK |
| R0-M16 | RDC | MAT | office cuisine mat | ? |  | 1 |  |  |  | A_CONFIRMER |
| R0-M17 | RDC | MAT | laverie 2 mat | E5 | 12.53 | 1 | 622 | 747 | 747 | OK |
| R0-M18 | RDC | MAT | vestiaires (10,9 m²) | E7 | 10.86 | 1 | 539 | 647 | 647 | OK |
| R0-M19 | RDC | MAT | vestiaire (9,1 m²) | E? | 9.10 | 1 | 452 | 542 | 542 | A_CONFIRMER |
| R0-M20 | RDC | MAT | local non identifié (au-dessus ménage E10) | ? |  | 1 |  |  |  | A_CONFIRMER |
| R0-M21 | RDC | MAT | local matériel D9 / local stockage matériel d'animation | D9 | 10.73 | 3 | 533 | 639 | 213 | A_CONFIRMER |
| R0-M22 | RDC | MAT | buanderie A32 / wc maternelle 2 A24 | A32 | 5.90 | 2 | 293 | 352 | 176 | A_CONFIRMER |

> Les cases vides correspondent à un local sans surface ni puissance connue (D-05). Ces locaux sont exclus des totaux et signalés.

### 7.2 Radiateurs : puissance requise et équivalent NF EN 442 (`outputs/02_radiateurs_selection.csv`)

- Facteur 55/45/20, n = 1,3 : **0,511**. On a donc **P50_requise = P_par_radiateur / 0,511**.
- Classes de 60 à 63 m² équipées de 2 radiateurs : P_part ≈ 1 850 W → **P50 ≈ 3 620 W par radiateur**.
- Stockages de 7,6 m² : P_part ≈ 450 W → P50 ≈ 880 W.
- **Modèle, dimensions et P_régime catalogue** : renseignés automatiquement dès réception du catalogue (D-18). Le statut actuel est `CATALOGUE REQUIS` sur les 91 radiateurs.

### 7.3 Table de dimensionnement au régime projet (ΔT = 10 K) : `outputs/03_table_DN_regime_projet.csv`

| dn | designation | d_int_mm | v_max | qv_max_m3h | p_max_kW_projet | p_dt10_manuscrit |
|---|---|---|---|---|---|---|
| 15 | 15/21 | 16.6 | 0.32 | 0.249 | 2.9 | 2.9 |
| 20 | 20/27 | 22.2 | 0.4 | 0.557 | 6.48 | 6.5 |
| 25 | 26/34 | 27.9 | 0.45 | 0.99 | 11.52 | 11.6 |
| 32 | 33/42 | 36.6 | 0.55 | 2.083 | 24.23 | 24.36 |
| 40 | 40/49 | 42.5 | 0.6 | 3.064 | 35.64 | 35.96 |
| 50 | 50/60 | 53.8 | 0.7 | 5.729 | 66.62 | 66.12 |
| 65 | 66/76 | 68.8 | 0.85 | 11.376 | 132.3 | 132.44 |
| 80 | 80/89 | 82.5 | 1.0 | 19.244 | 223.81 | 222 |
| 100 | 102/114 | 107.1 | 1.6 | 51.891 | 603.49 | 602 |
| 125 | 125/133 | 125.0 | 1.8 | 79.522 | 924.84 | 922 |
| 150 | 159/4,5 | 159.3 | 2.0 | 143.501 | 1668.91 | 1663.44 |
| 175 | 193/5,4 | 182.5 | 2.25 | 211.885 | 2464.22 | 2456 |
| 200 | 219/5,6 | 206.5 | 2.5 | 301.42 | 3505.52 | 3496 |
| 250 | 273/6,6 | 260.4 | 2.9 | 555.997 | 6466.24 | 6446 |

### 7.4 Synthèse par départ : `outputs/04_synthese_circuits.csv`

| circuit | nb_radiateurs | nb_sans_puissance | P_kW | Qv_m3h | DN_depart_mini | designation |
|---|---|---|---|---|---|---|
| ELEM | 32 | 1 | 48.07 | 4.13 | 50 | 50/60 |
| MAT | 38 | 4 | 47.82 | 4.11 | 50 | 50/60 |
| PERI | 15 | 1 | 13.9 | 1.2 | 32 | 33/42 |
| PERI-RESTAU | 6 | 4 | 5.57 | 0.48 | 20 | 20/27 |

> Le circuit CTA est absent faute de données (D-17). Le départ PÉRI réel (PÉRI + RESTAU) vaut 19,5 kW, soit Qv 1,67 m³/h, ce qui reste en DN32 (Qv_max 2,08). Des puissances manquent encore sur 10 radiateurs.

### 7.5 Esquisse R+1, circuit ÉLÉM : tronçons (`outputs/05_troncons_dimensionnement.csv`)

- Les longueurs sont mesurées sur CVPS_02 à l'échelle 1/100, à ±15 % près.
- L'origine est le pied de la colonne montante R+1 (H-12).
- dP_AR = (linéaire + singulier) × 2.

| troncon_id | amont_id | longueur_m | radiateurs | P_cumul_kW | Qv_m3h | DN | designation | V_ms | V_max_ms | J_Pa_m | dP_AR_Pa |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S01 | SOURCE | 3.1 |  | 21.08 | 1.813 | 32 | 33/42 | 0.48 | 0.55 | 81.2 | 654 |
| B-WC5 | S01 | 1.1 | R1-09-a | 0.81 | 0.069 | 15 | 15/21 | 0.09 | 0.32 | 11.2 | 32 |
| S02 | S01 | 3.1 |  | 20.27 | 1.743 | 32 | 33/42 | 0.46 | 0.55 | 75.5 | 609 |
| S03 | S02 | 1.6 |  | 3.71 | 0.319 | 20 | 20/27 | 0.23 | 0.4 | 40.2 | 167 |
| S04 | S03 | 1.9 |  | 3.71 | 0.319 | 20 | 20/27 | 0.23 | 0.4 | 40.2 | 199 |
| B-C8b | S04 | 1.0 | R1-10-b | 1.86 | 0.16 | 15 | 15/21 | 0.2 | 0.32 | 48.0 | 125 |
| B-C8a | S04 | 16.8 | R1-10-a | 1.86 | 0.16 | 15 | 15/21 | 0.2 | 0.32 | 48.0 | 2096 |
| S05 | S02 | 1.0 |  | 16.56 | 1.424 | 32 | 33/42 | 0.38 | 0.55 | 52.1 | 135 |
| B-ST3 | S05 | 1.9 | R1-08-a | 0.45 | 0.039 | 15 | 15/21 | 0.05 | 0.32 | 3.2 | 16 |
| S06 | S05 | 2.4 |  | 16.11 | 1.385 | 32 | 33/42 | 0.37 | 0.55 | 49.6 | 309 |
| S07 | S06 | 1.5 |  | 3.75 | 0.323 | 20 | 20/27 | 0.23 | 0.4 | 40.9 | 160 |
| B-C7b | S07 | 0.9 | R1-06-b | 1.85 | 0.159 | 15 | 15/21 | 0.2 | 0.32 | 47.8 | 112 |
| B-AT3 | S07 | 10.9 | R1-07-a | 1.9 | 0.163 | 15 | 15/21 | 0.21 | 0.32 | 50.0 | 1418 |
| S08 | S06 | 7.2 |  | 12.36 | 1.063 | 32 | 33/42 | 0.28 | 0.55 | 30.6 | 573 |
| B-C7a | S08 | 8.7 | R1-06-a | 1.85 | 0.159 | 15 | 15/21 | 0.2 | 0.32 | 47.8 | 1080 |
| S09 | S08 | 2.9 |  | 10.51 | 0.904 | 25 | 26/34 | 0.41 | 0.45 | 86.4 | 651 |
| B-C6a | S09 | 8.8 | R1-05-a | 1.85 | 0.159 | 15 | 15/21 | 0.2 | 0.32 | 47.8 | 1093 |
| S10 | S09 | 7.3 |  | 8.66 | 0.745 | 25 | 26/34 | 0.34 | 0.45 | 60.6 | 1151 |
| S11 | S10 | 1.5 |  | 3.69 | 0.317 | 20 | 20/27 | 0.23 | 0.4 | 39.8 | 155 |
| B-C6b | S11 | 0.9 | R1-05-b | 1.85 | 0.159 | 15 | 15/21 | 0.2 | 0.32 | 47.8 | 112 |
| B-AT2 | S11 | 11.6 | R1-02-a | 1.84 | 0.158 | 15 | 15/21 | 0.2 | 0.32 | 47.3 | 1425 |
| S12 | S10 | 1.7 |  | 4.97 | 0.427 | 20 | 20/27 | 0.31 | 0.4 | 67.9 | 300 |
| B-ST2 | S12 | 1.7 | R1-03-a | 0.45 | 0.039 | 15 | 15/21 | 0.05 | 0.32 | 3.2 | 14 |
| S13 | S12 | 1.7 |  | 4.52 | 0.389 | 20 | 20/27 | 0.28 | 0.4 | 57.2 | 253 |
| B-WC4 | S13 | 6.1 | R1-04-a | 0.8 | 0.068 | 15 | 15/21 | 0.09 | 0.32 | 10.9 | 173 |
| S14 | S13 | 2.5 |  | 3.72 | 0.32 | 20 | 20/27 | 0.23 | 0.4 | 40.4 | 263 |
| S15 | S14 | 1.9 |  | 3.72 | 0.32 | 20 | 20/27 | 0.23 | 0.4 | 40.4 | 200 |
| B-C5b | S15 | 1.0 | R1-01-b | 1.86 | 0.16 | 15 | 15/21 | 0.21 | 0.32 | 48.3 | 125 |
| B-C5a | S15 | 16.7 | R1-01-a | 1.86 | 0.16 | 15 | 15/21 | 0.21 | 0.32 | 48.3 | 2095 |

### 7.6 Chemins et circuit critique : `outputs/06_chemins_circuit_critique.csv`

| id_radiateur | critique | longueur_aller_m | dP_chemin_Pa | exces_a_laminer_Pa |
|---|---|---|---|---|
| R1-09-a |  | 4.2 | 10686 | 6507 |
| R1-10-b |  | 10.7 | 11754 | 5439 |
| R1-10-a |  | 26.5 | 13725 | 3468 |
| R1-08-a |  | 9.1 | 11414 | 5779 |
| R1-06-b |  | 12.0 | 11979 | 5214 |
| R1-07-a |  | 22.0 | 13285 | 3908 |
| R1-06-a |  | 25.5 | 13360 | 3833 |
| R1-05-a |  | 28.5 | 14024 | 3169 |
| R1-05-b |  | 29.4 | 14349 | 2844 |
| R1-02-a |  | 40.1 | 15662 | 1531 |
| R1-03-a |  | 30.4 | 14396 | 2797 |
| R1-04-a |  | 36.5 | 14808 | 2385 |
| R1-01-b |  | 35.8 | 15223 | 1970 |
| R1-01-a | OUI | 51.5 | 17193 | 0 |

**Circuit critique (R+1, depuis le pied de colonne)** : radiateur **R1-01-a**, classe élémentaire 5 en façade.
- Longueur aller : 51,5 m. ΔP = 17,2 kPa (dont 10 kPa terminal H-07), soit 1,72 mCE.
- Il reste à y ajouter la colonne montante, le parcours du RDC jusqu'à la nourrice, la nourrice et la bouteille. Ces éléments seront connus à l'export Revit complet.

**Radiateurs critiques présumés des autres circuits, à confirmer par le calcul complet**
- MAT : R0-M14-b, classe maternelle 6, extrémité est, en fin de collecteur central.
- PÉRI : R0-P10 (salle ATSEM) ou R0-P11 (bibliothèque), en extrémité est du collecteur nord.
- ÉLÉM : le chemin passant par le R+1 (colonne + 51,5 m) est très probablement critique devant la classe élém. 1 du RDC.

---

## 8. PROMPT POUR L'AGENT DE CODAGE (à coller tel quel, avec les fichiers)

````text
RÔLE
Tu es ingénieur BIM MEP senior, spécialiste du chauffage à eau chaude (sélection de radiateurs,
dimensionnement hydraulique) et développeur Python/pyRevit. Tu travailles dans le dépôt contenant
le dossier `chauffage-albert-camus/`. Lis d'abord ENTIÈREMENT
`chauffage-albert-camus/DOSSIER_PROJET_CHAUFFAGE.md`. Il fait foi pour les données extraites, les règles,
les hypothèses (H-xx) et les écarts (D-xx).

PROJET
Groupe scolaire Albert Camus, Talence (33), zone H2c, θe = -5 °C, bilan NF EN 12831.
Production : PAC eau/eau AERMEC WRL 300, ballons tampons, bouteille de mélange,
nourrice de 4 départs : MAT, ELEM, PERI (Admin/Péri, avec sous-réseau restauration à V2V) et CTA.

ENTRÉES (fichiers joints et données du dépôt)
- F1 CVPS_01 plan chauffage RDC (PDF DCE) ; F2 CVPS_02 plan chauffage R+1 ; F4 ARCH_03 plan architecte de l'étage
- F3 bilan thermique EN 12831 ; F5 note « Dimensionnement réseau hydraulique » (tableau DN/V/Qv/P)
- data/inventaire_locaux_radiateurs_PROVISOIRE.csv : 57 locaux, 91 radiateurs
- data/hypotheses.json ; data/table_dimensionnement_methode.csv ; data/troncons_*.csv ;
  data/catalogue_radiateurs.csv (s'il existe)
- éventuellement : bilan par local, DWG, RVT, IFC, catalogue fabricant, tableau des CTA. Si l'un de ces
  documents est fourni, il REMPLACE l'hypothèse correspondante.

RÈGLES NON NÉGOCIABLES
1. P_majorée = P_base_local × 1,20 (P_base = déperditions Φ_HL du local, pas la puissance de relance ; cf. D-02).
2. n radiateurs dessinés dans un local : P_part = P_majorée / n, à parts égales, et chaque radiateur est sélectionné pour sa part.
3. Position et taille = plan architecte. Un radiateur qui ne rentre pas est SIGNALÉ (statut FLAG) avec des
   alternatives classées (§ 6.4). Ne jamais déplacer, agrandir ni ajouter de radiateur sans accord écrit.
4. Tracé = DCE (F1/F2). Le tracé et le calcul restent découplés (export des tronçons → calcul → réinjection).
5. Dimensionnement du radiateur le plus éloigné vers la source, selon F5 : Qv = P/(1,163·ΔT) ;
   DN = plus petit DN tel que Qv ≤ Qv_max(DN) = π/4·Øint²·V_max(DN) ; conversion 1 mCE = 10 kPa.
6. Puissance des radiateurs = données CATALOGUE FABRICANT au régime du projet (NF EN 442-2 :
   P = P50·(ΔT_lm/49,83)^n avec le n du fabricant), jamais la valeur nominale 75/65/20 seule.

LOGIQUE DE CALCUL (déjà implémentée dans calc/calc_chauffage.py, à étendre et non à réécrire)
- Puissances : P_base_W_rapport si renseigné, sinon ratio H-01 marqué PROVISOIRE, sinon FLAG.
- Sélection : plus petit modèle du type dessiné avec P_régime ≥ P_part et L ≤ L_dispo, sinon FLAG.
- Réseau : arbre de tronçons (amont_id), cumul en post-ordre, DN F5, V, Re, λ de Colebrook
  (rugosité H-05), J, ΔP linéaires + singulières (Σζ, sinon forfait H-06) × aller/retour (H-08),
  + ΔP terminal (H-07). Chemins source→radiateur, circuit critique = ΣΔP max, HMT par
  circuit (mCE), excès à laminer par radiateur.

TÂCHES, DANS CET ORDRE
T1. Lancer `python3 -m unittest calc/test_calc.py` puis `python3 calc/calc_chauffage.py` et vérifier que les sorties sont reproduites.
T2. Si le bilan par local est fourni : renseigner P_base_W_rapport (rapprochement par nom ET surface,
    jamais par le code B21/A21 qui n'est pas unique), puis consigner les écarts nom/surface.
T3. Si un catalogue est fourni : construire data/catalogue_radiateurs.csv en citant la source (référence et page),
    relancer, puis produire la liste des FLAG avec alternatives (règle 3).
T4. Écrire les scripts pyRevit dans revit/ :
    - place_radiators.py (CSV → familles posées sur mur, paramètres CVC_*, aucun déplacement)
    - create_systems_filters.py (10 types de systèmes CH-*-A/R, filtres de couleur et de mode de pose, gabarits de vue)
    - export_network.py (graphe des connecteurs → data/troncons_<circuit>_<horodatage>.csv + ElementIds)
    - apply_results.py (diamètres + paramètres CVC_* ; journal des raccords non redimensionnés)
    Compatibles avec Revit 2024+ et pyRevit (moteur CPython), avec un mode « dry-run » qui n'écrit rien.
T5. Ajouter un générateur de note de calcul (Markdown → outputs/note_calcul.md) qui reprend les nomenclatures,
    le circuit critique, les HMT par départ, la liste des FLAG et la liste des D-xx ouverts.
T6. Étendre les tests : arbre avec boucle (doit échouer proprement), radiateur orphelin, DN imposé
    sous-dimensionné, régime incompatible (θretour ≤ θi).

DONNÉES MANQUANTES, AMBIGUËS OU INCOHÉRENTES : PROCÉDURE OBLIGATOIRE
- Ne JAMAIS inventer une valeur ni la présenter comme un fait. Toute valeur non sourcée devient une hypothèse
  H-xx dans hypotheses.json, avec sa source ou la mention « hypothèse », et reste modifiable.
- Pour chaque problème (local sans radiateur, radiateur sans local, surface illisible, conflit
  ARCH/CVC, puissance absente, DN hors tableau…) : ajouter une ligne D-xx (constat, gravité,
  hypothèse retenue), appliquer l'hypothèse la plus prudente, CONTINUER, puis tout lister à la fin.
- Arrêt seulement si la poursuite produirait un résultat faux sans signalement possible
  (ex. : fichier d'entrée corrompu). Dans ce cas, dire précisément ce qui manque.
- Toute citation de norme (NF EN 12831-1, NF EN 442-2, NF EN 215, NF EN 10255, NF DTU 65.10,
  NF DTU 65.11, NF EN 14336) doit pointer vers la clause utilisée. Sinon, écrire « à vérifier ».

SORTIES ATTENDUES
outputs/01_locaux_puissances.csv · 02_radiateurs_selection.csv · 03_table_DN_regime_projet.csv ·
04_synthese_circuits.csv · 05_troncons_dimensionnement.csv · 06_chemins_circuit_critique.csv ·
note_calcul.md ; scripts revit/*.py ; DOSSIER_PROJET_CHAUFFAGE.md mis à jour (§ 5 et § 7).

CONTRÔLES AVANT DE RENDRE
- Σ P_part = Σ P_majorée par local ; Σ par circuit = P_cumul du tronçon de départ
- V ≤ V_max sur 100 % des tronçons ; aucun tronçon sans amont ; aucun radiateur absent de l'arbre
- tous les tests passent ; aucun chiffre du § 7 sans origine (rapport, catalogue ou H-xx)
- écrire le français technique du projet (aller/retour, nourrice, DN, mCE, ΔP, régime)
````

---

## 9. Références

| Référence | Usage dans ce dossier |
|---|---|
| Note « Dimensionnement réseau hydraulique » (F5) | **Autorité principale** : choix des DN, V_max, P = 1,163·Qv·ΔT, 1 mCE = 10 kPa |
| NF EN 12831-1 (charge thermique nominale) | Base du bilan F3 ; Φ_HL par local (D-01, D-02) |
| NF EN 442-2 (radiateurs et convecteurs, méthodes d'essai et d'évaluation) | Conditions normales 75/65/20, équation caractéristique Φ = K·ΔT_lm^n, conversion au régime projet |
| NF EN 215 (robinets thermostatiques) | Caractéristiques des robinets pour ΔP terminal et préréglage (H-07) |
| NF EN 10255 | Tubes acier filetables, désignations 15/21… (H-05) |
| NF DTU 65.10 et NF DTU 65.11 | Mise en œuvre des canalisations sous pression et dispositifs de sécurité des installations de chauffage central (vérifications d'exécution) |
| NF EN 14336 | Mise en service et équilibrage des installations de chauffage à eau |
| Fiche technique AERMEC WRL 300 | Température de départ maximale, H-02 (**à obtenir**) |
| Catalogue du fabricant des radiateurs retenus | P50, n, dimensions (**à obtenir**, D-18) |

> Les versions et clauses précises des normes sont à vérifier sur la base AFNOR du projet. Aucune valeur
> numérique de ce dossier n'est tirée d'une norme sans être signalée comme hypothèse.

---

## 10. Arborescence

```
chauffage-albert-camus/
├── DOSSIER_PROJET_CHAUFFAGE.md          ← ce document
├── data/
│   ├── hypotheses.json                   ← toutes les hypothèses H-xx (modifiables)
│   ├── inventaire_locaux_radiateurs_PROVISOIRE.csv
│   ├── table_dimensionnement_methode.csv ← note F5 retranscrite
│   ├── troncons_R1_ELEM_ESQUISSE.csv     ← tracé R+1 mesuré sur CVPS_02
│   └── catalogue_radiateurs_TEMPLATE.csv ← à copier en catalogue_radiateurs.csv
├── calc/
│   ├── calc_chauffage.py                 ← moteur (stdlib)
│   └── test_calc.py
└── outputs/                              ← résultats régénérés à chaque exécution
```

> Les PDF sources ne sont pas versionnés dans ce dépôt (documents du client). Il faut les joindre à la session de l'agent.
