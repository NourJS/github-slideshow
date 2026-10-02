# Dossier de démarrage : chauffage à eau chaude du groupe scolaire Albert Camus (Talence)

**Réhabilitation et extension du groupe scolaire Albert Camus, 28 rue Lavoisier, 33400 Talence**
Lot CVC-PLB. Passage DCE vers EXE. Dossier mis à jour le 02/10/2026 (révision E).

> **Objet.** Tout ce qu'il faut pour reprendre le projet dans Claude Code ou Codex :
> - les données extraites des 6 pièces fournies et les règles d'ingénierie ;
> - les hypothèses sourcées et modifiables, et les écarts relevés ;
> - le workflow BIM Revit ;
> - les résultats de calcul ;
> - le **modèle JSON prêt à dessiner** (`model/modele_chauffage_albert_camus.json`) ;
> - un **prompt prêt à coller** (§ 8).
>
> **Changements de la révision E**
> - **Fiche CTA cuisine** intégrée (France Air PLATEPLAY T2000 en faux-plafond, batterie change-over en gaine) : **6 CTA sur 6**. Position non dessinée au DCE : supposée dans le faux-plafond de l'office cuisine élé (D-41).
> - Chaque émetteur piqué sur un tube qui continue vers l'aval reçoit sa propre branche (`B-<id>`), dimensionnée et étiquetée sur le plan.
>
> **Changements de la révision D**
> - **5 fiches CTA France Air POWERPLAY** intégrées (`data/cta_fiches.json`) : batteries **change-over** (eau chaude 60/40 °C, eau glacée 7/12 °C). La CTA cuisine est attendue.
> - Réseau CTA relu sur CVPS_01 et CVPS_02 (colonne vers la terrasse R+1) et dimensionné **en chaud et en froid** : le DN retenu est le plus grand des deux cas (H-19).
> - Plan RDC annoté complété : étiquettes CTA et diamètres du réseau CTA.
>
> **Changements de la révision C**
> - Positions des radiateurs relues sur les **symboles vectoriels** des PDF CVC (précision ≈ 0,05 m) ; **3 radiateurs RDC ajoutés** (R0-08-b, R0-13-b, R0-21-b), soit **94 radiateurs**. Recalage R+1 / RDC par corrélation des calques architecte.
> - **Réseau RDC relu sur le PDF vectoriel** (calque `VIV02_CHA_RES_ECH_A`) : 159 tronçons dimensionnés de bout en bout, circuits critiques et HMT calculés (§ 7.6).
> - **Plan RDC annoté** : `outputs/CVPS_01_RDC_radiateurs_diametres.pdf` (puissance de chaque radiateur, diamètre à chaque changement de section). Outil `tools/plan_rdc_annote.py`.
>
> **Changements de la révision B**
> - Puissances par local issues du **rapport émetteurs EN 12831** (F3b) : D-01 levé.
> - **Nouvelle règle de tracé du R+1** : chaque radiateur R+1 est raccordé depuis le radiateur RDC à l'aplomb, avec **une réservation dans la dalle par radiateur**. Le tracé DCE n'est suivi qu'au RDC.
> - **Couleurs DCE** relevées sur la légende (RGB).
> - Distribution principale en **acier**, raccordements apparents en **cuivre**.
> - Ajout du modèle JSON pour le dessin.

---

## 0. Mode d'emploi rapide

```bash
cd chauffage-albert-camus
python3 calc/calc_chauffage.py                         # outputs/*.csv + model/modele_chauffage_albert_camus.json
python3 calc/calc_chauffage.py --troncons data/troncons_<circuit>.csv   # avec le réseau tracé (export Revit)
python3 -m unittest calc/test_calc.py                  # 9 tests du moteur
pip install pymupdf && python3 tools/plan_rdc_annote.py --pdf <CVPS_01.pdf>   # réseau RDC + plan annoté
```

| Pour…                                   | modifier                                                       | puis |
|-----------------------------------------|----------------------------------------------------------------|------|
| régime d'eau, base de la majoration, hauteur d'étage, tolérance d'aplomb… | `data/hypotheses.json`                | relancer |
| positions réelles des radiateurs (DWG/RVT) | `data/radiateurs_positions_PROVISOIRE.csv`, ou en direct dans le modèle Revit puis export | relancer |
| modèles réels de radiateurs             | créer `data/catalogue_radiateurs.csv` (gabarit fourni)        | relancer |
| calques DWG, couleurs, textes de tracé  | `data/modele_base.json` (partie fixe du JSON)                 | relancer |
| tracé ou longueurs                      | export Revit → `data/troncons_*.csv` (§ 6.7)                  | relancer avec `--troncons` |

> Le JSON est **généré** : ne pas l'éditer à la main. On modifie `data/`, puis on relance.

---

## 1. Synthèse

| Élément | État |
|---|---|
| Bilan par local (F3b) | **65 locaux** (56 au RDC, 9 au R+1). Déperditions 79 325 W, puissance à installer 140 826 W (= D + 23 W/m² × S). Transcription vérifiée ligne à ligne et sur les totaux |
| Radiateurs | **94** : 80 au RDC (dont 5 plinthes) et 14 au R+1. Positions = symboles vectoriels des PDF CVC |
| Locaux du bilan **sans radiateur** dessiné | 6 : réserve info, local poubelles, wc admin 1, circulation A13/A33…, **hall maternelle (2,35 kW)**, **circulation R+1 (7,80 kW)** (D-25) |
| Radiateurs **sans local** au bilan | 3 : stockages 1, 2 et 3 (D-26) |
| Majoration +20 % | appliquée sur la colonne **« Puissance à installer »** (règle 1 lue à la lettre). Total 169,0 kW, dont 154,7 kW portés par des radiateurs. Sur les seules déperditions, ce serait 95,2 kW : **à confirmer** (D-02) |
| Puissance au régime et équivalent NF EN 442 | régime 55/45 °C **supposé** (H-02), θi du bilan (19 °C, 20 °C pour les vestiaires) : facteur 0,533 |
| R+1 | 14 radiateurs, **14 réservations** de dalle. **4 radiateurs** ont un radiateur RDC à l'aplomb (≤ 1,0 m) sur les plans DCE. Les 10 autres sont **signalés** (D-28) |
| Départs (provisoire) | **ÉLÉM** 53,4 kW → DN50 (R+1 compris, 20,4 kW) · **MAT** 70,7 kW → **DN65** · **PÉRI** 30,6 kW (dont restauration 13,8 kW) → DN40 · **CTA** (6 CTA) : 57,6 m³/h en eau glacée → **DN125** (13,5 m³/h en eau chaude, soit DN80 si le réseau ne transportait que de l'eau chaude) |
| CTA | 6 fiches France Air (2 × T10000 en terrasse R+1 pour l'élémentaire, 2 × T4000 et 1 × T2500 au RDC pour la maternelle, 1 × PLATEPLAY T2000 en faux-plafond pour la cuisine). Puissance max des batteries 300 kW à 60/40 °C, mais **besoin réel estimé ≈ 50 kW** (soufflage à 19 °C). HMT du circuit CTA : 3,4 mCE en chaud, **16,1 mCE en froid** (batteries à 128–137 kPa) |
| Choix des modèles | en attente du catalogue fabricant (D-18). P50 requise : 2,5 à 4,9 kW pour un radiateur de classe, **7,5 kW** pour chacun des 2 radiateurs du hall + circulation élém. et **8,2 kW** pour la circulation mat 2/5/6 (D-27) |
| Réseau RDC | relu sur le PDF vectoriel : 159 tronçons (356 m d'acier, 459 m de cuivre en aller, longueurs en plan + descentes H-18). Radiateurs critiques : ÉLÉM **R1-06-a** (2,03 mCE), MAT **R0-49-b** (2,91 mCE), PÉRI **R0-30-b** (2,17 mCE), restauration R0-16-a (1,71 mCE), hors chaufferie |
| Plan annoté | `outputs/CVPS_01_RDC_radiateurs_diametres.pdf` |
| Modèle JSON | prêt : niveaux, matériaux, 10 systèmes avec couleurs, filtres, départs, 65 locaux, 94 radiateurs (position, puissance, raccordement), 14 réservations, 159 tronçons et chemins, procédure de dessin |

---

## 2. Données extraites des fichiers fournis

### 2.1 Pièces fournies

| Réf. | Fichier | Contenu utile |
|---|---|---|
| F1 | `CVPS_01-Plan_de_reseau_de_chauffage_RDC.pdf` | Plan de principe chauffage RDC, DCE ind. 0 du 27/03/2026 (BE Vivien), 1/100. **Tracé à suivre** |
| F2 | `CVPS_02-Plan_de_reseau_de_chauffage_R1.pdf` | Plan de principe R+1. **Positions des radiateurs seulement** : le tracé est abandonné (décision D1) |
| F3 | `…BILAN_THERMIQUE_Résultats_Génération_Surpuissance…pdf` | Données climatiques et totalisation « génération » : 132 765 / 194 266 W |
| **F3b** | `…BILAN_THERMIQUE_Résultats_Emetteurs_Surpuissance…-129-137.pdf` | **Puissances par local** (p. 129 à 137) : surface, θi, déperditions par transmission et par ventilation, puissance à installer |
| F4 | `ARCH_03_-_Plan_detage.pdf` | Plan architecte de l'étage, ind. A, 1/100 |
| F5 | Photo de la note « Dimensionnement réseau hydraulique » | Tableau DN / Øint / V / Qv / P, autorité principale |
| F6 | 6 fiches CTA `CTA_DF_*.pdf` (France Air POWERPLAY et PLATEPLAY, édition 18/09/2026) | Débits d'air, batteries change-over chaud 60/40 °C et froid 7/12 °C : puissance, débit d'eau, pertes de charge eau et air, dimensions, poids |
| D1 | Décision du 02/10/2026 | Tracé DCE au RDC seulement ; R+1 raccordé radiateur par radiateur depuis le RDC avec une réservation par radiateur ; couleurs DCE ; acier pour la distribution principale, cuivre pour les raccordements apparents |

### 2.2 Bilan thermique

- Gironde (33), altitude 9 m, zone **H2c**, θe = **−5 °C**, θe moyenne = 12 °C, **NF EN 12831**, bâtiment neuf.
- F3b, colonne « Puissance à installer » = **Déperditions totales + 23 W/m² × Surface**. La majoration « D + 23x Sh » est imprimée sous chaque groupe et vérifiée sur les 65 lignes.
- Totaux F3b : RDC 2 212,6 m², 65 096,9 W et 115 986,0 W ; R+1 461,4 m², 14 227,6 W et 24 839,8 W. Bâtiment : **79 325 W et 140 826 W**.
- **Écart F3 / F3b** : F3 annonce 132 765 W et 194 266 W pour la même surface. L'écart est de 53 440 W sur les deux colonnes : des charges hors émetteurs (D-24) ?

### 2.3 Plans CVC DCE (F1 et F2)

- **Nourrice de 4 départs**, de gauche à droite : *Admin / Péri*, *Élémentaire*, *CTA*, *Maternelle*.
- **Production** :
  - PAC eau/eau **AERMEC WRL 300** (1 320 × 845 × 1 380 mm, 381 kg) sur sondes géothermiques de 200 m ;
  - ballons tampons 500 L (Atlantic Corprimo) et 750 L (Atlantic Corklim) ;
  - bouteille de mélange, filtre magnétique, vases d'expansion ;
  - réutilisation de la VB existante.
- **Couleurs DCE** (pixels de la légende F1, en RGB) :

| Circuit | Aller (légende) | Retour (légende) | Écart sur le plan |
|---|---|---|---|
| MAT | rouge 255,0,0 | magenta 255,0,255 | aucun |
| ÉLÉM | brun 205,105,40 | orange 242,103,34 | aucun |
| PÉRI | bordeaux 153,27,30 | rouge 205,32,39 | retour tracé en **violet 147,39,143** (D-15) |
| CTA | vert foncé 0,38,0 | vert 0,165,41 | tracés en 19,103,52 et 19,155,72 |
| Restauration (V2V, PÉRI) | hors légende | hors légende | 242,113,114 et 169,83,160 (D-06) |

  **Règle 6 : on dessine avec les couleurs de la légende.**
- **Modes de pose** (légende) : plinthe, dalle / enterré, plafond.
- **Émetteurs** : « Radiateur vertical 1500x750 » (13 étiquettes au RDC), « Radiateur plinthe » (5, restauration). R+1 non étiqueté (symbole d'environ 1,0 m).

### 2.4 Note de méthode (F5) : autorité principale

- Qv_max(DN) = π/4 · Øint² · V_max(DN) ;
- P = 1,163 · Qv · ΔT, avec P en kW, Qv en m³/h et ΔT en K (vérifié sur toutes les lignes) ;
- **plus petit DN tel que Qv ≤ Qv_max** ;
- 1 mCE = 10 kPa.

Pour le **cuivre**, la vitesse limite est transposée par diamètre intérieur (H-15).

### 2.5 Centrales de traitement d'air (F6)

| CTA | Modèle | Local | Soufflage m³/h | Chaud 60/40 : P max kW / Qv m³/h / ΔP kPa | Froid 7/12 : Qv m³/h / ΔP kPa | Besoin chaud estimé kW |
|---|---|---|---|---|---|---|
| CTA-CUISINE | PLATEPLAY T2000 + batterie CO gaine Plate Play T2000 | faux-plafond de l'office cuisine élé (E4) - position supposée | 1580 | 10.2 / 0.443 / 2.65 | 1.055 / 14.12 | 1.7 |
| CTA-ELEM-NORD | T10000-V-CO-Y | terrasse R+1 au-dessus de la chaufferie (bloc nord) | 9920 | 95.5 / 4.309 / 4.7 | 14.191 / 51.4 | 14.3 |
| CTA-ELEM-SUD | T10000-V-CO | terrasse R+1 au-dessus de la chaufferie (bloc sud) | 9075 | 91.7 / 4.14 / 4.4 | 20.092 / 99.9 | 15.5 |
| CTA-MAT-EST | T4000-M-CO | LT CTA 3,7 m² (extrémité est) | 3810 | 38.1 / 1.721 / 5.7 | 8.33 / 128.5 | 6.6 |
| CTA-MAT-MOTRICITE | T2500-M + module CO (caisson externe) | local CTA 4,25 m² (au sud de la salle de motricité) | 2500 | 24.6 / 1.109 / 2.8 | 5.35 / 62.5 | 4.5 |
| CTA-MAT-OUEST | T4000-M-CO | local CTA 5,0 m² (près du hall maternelle) | 4015 | 39.5 / 1.778 / 6.1 | 8.618 / 137.0 | 6.9 |

- Les puissances « chauffage » des fiches correspondent à la batterie à pleine ouverture : elles portent l'air de la sortie de la roue (≈ 14 à 16 °C) à **35 à 44 °C**. Le **besoin réel** est estimé pour un soufflage neutre à 19 °C : Qv_air × 1,2 × 1,006 × (19 − T sortie roue), soit **49.6 kW** pour les 6 CTA. C'est une estimation, à confirmer par la consigne de soufflage du CCTP.
- Recoupement : F3 (génération) − F3b (émetteurs) = 53,4 kW, contre 49.6 kW estimés pour les 6 CTA. L'écart correspond donc vraisemblablement au besoin de ventilation (le reliquat de 3.9 kW dépend de la consigne de soufflage retenue par le thermicien).
- **Hypothèse H-19** : les batteries étant change-over, le réseau « CTA » transporte aussi l'eau glacée. Il est donc dimensionné au débit maximal des deux cas.
- CTA cuisine : PLATEPLAY T2000 en **faux-plafond** (2 060 × 1 210 × 527 mm, 305 kg), batterie CO en gaine Ø355, raccord hydraulique 1/2". Débit d'air de 1 580 m³/h, alimentation 230 V mono.

---

## 3. Règles d'ingénierie appliquées

| # | Règle | Implémentation |
|---|---|---|
| 1 | Puissance du local (rapport) × **1,20** avant sélection | `P_majoree = <base_puissance_rapport> × 1,20`. La colonne de base est réglable (D-02) |
| 2 | n radiateurs dans un local : **parts égales** | `P_part = P_majoree / n`. Sélection de chaque radiateur pour sa part |
| 3 | Position et taille selon l'architecte ; si le radiateur **ne rentre pas** → **FLAG** et alternative | aucun déplacement ni ajout automatique. Alternatives en § 6.4 |
| 4 | **RDC** : tracé DCE. **R+1** : chaque radiateur est raccordé **depuis le radiateur RDC à l'aplomb**, à travers **une réservation de dalle** | `couplage_R1()`, `raccordements()`, `reservations()`. Tracé et calcul découplés |
| 5 | Dimensionnement **du radiateur le plus éloigné vers la source** | cumul en post-ordre ; chemin critique = ΣΔP maximal |
| 6 | **Couleurs DCE** ; **acier** pour la distribution principale ; **cuivre** pour les raccordements apparents | `systemes[]` (rgb_legende) ; types de canalisation `CH_Acier_EN10255` et `CH_Cuivre_EN1057` |

**Formules**
- NF EN 442-2 :
  - ΔT_lm = (θa − θr) / ln[(θa − θi)/(θr − θi)] ;
  - P_régime = P50 · (ΔT_lm / 49,83)^n ;
  - P50_requise = P_part / facteur.
- **Radiateur RDC « porteur »** : la branche cuivre transite P_RDC + Σ P_R1 raccordés. **Lien R+1** : il transite P_R1. Sa longueur provisoire vaut hauteur d'étage + écart horizontal.

---

## 4. Hypothèses, toutes dans `data/hypotheses.json`

| Id | Hypothèse | Valeur | Source / justification |
|---|---|---|---|
| H-01 | Base de la majoration | `puissance_a_installer_W` | Règle 1 lue à la lettre (« puissance requise du rapport »). Alternative : `deperd_total_W` (D-02) |
| H-02 | Régime d'eau | **55/45 °C** | Colonne ΔT = 10 °C manuscrite (F5) et production par PAC. **À confirmer** : CCTP et fiche AERMEC WRL 300 |
| H-03 | θi | **celle du bilan, local par local** (19 ou 20 °C) | F3b. Valeur par défaut 20 °C (NF EN 442-2) pour un local hors bilan |
| H-04 | Exposant n | 1,30 | NF EN 442-2. Remplacer par la valeur du fabricant |
| H-05 | Acier : rugosité | 0,045 mm | Tubes NF EN 10255, valeur usuelle |
| H-06 | Pertes singulières | 30 % des pertes linéaires | À remplacer par Σζ issus de Revit |
| H-07 | ΔP terminal | 10 kPa | À remplacer par les données des robinets (NF EN 215) |
| H-08 | Bitube | retour = aller | |
| H-09 | DN mini sur l'acier | DN15 | |
| H-10 | Seuil d'alerte J | 200 Pa/m | Usage, non normatif |
| H-11 | Hauteur d'étage | 3,50 m | **À lire sur les coupes** |
| H-12 | Bas du radiateur | 150 mm du sol fini | Usage, notice fabricant |
| H-13 | Tolérance d'« aplomb » | 1,0 m entre axes | Décision D1 traduite en critère |
| H-14 | Cuivre : rugosité | 0,0015 mm | Tube étiré NF EN 1057 |
| H-15 | Cuivre : V_max | interpolée sur Øint dans F5, palier à 0,32 m/s sous Ø16,6 | La note ne vise que l'acier |
| H-16 | Réservation par radiateur R+1 | 150 × 80 mm, 2 tubes cuivre sous fourreau, calfeutrement coupe-feu | **À valider** avec le lot GO et le BC (plancher d'ERP) |
| H-19 | Réseau CTA change-over | DN = max(débit chaud, débit froid) des fiches | Batteries « CO » des fiches France Air. Basculer `cta_base_debit` sur `chaud` si l'eau glacée a son propre réseau |
| H-20 | ΔP vanne de régulation CTA | 10 kPa | À remplacer par le Kv retenu |
| H-21 | Matériau du réseau CTA | acier | La règle « cuivre apparent » vise les radiateurs |
| H-17 | Positions | relevé PDF à ±0,3 m, repère commun RDC/R+1 (recalage sur la façade et les refends) | À remplacer par les DWG/RVT |

Facteur P_régime / P50 (n = 1,3) : 55/45 avec θi 19 °C = **0,533** ; θi 20 °C = 0,511 ; 50/40 avec θi 19 °C = 0,422 ; 60/50 avec θi 19 °C = 0,650.

---

## 5. Écarts, lacunes et discordances

Chaque ligne indique l'hypothèse retenue pour avancer.

| Id | Gravité | Constat | Hypothèse retenue |
|---|---|---|---|
| D-01 | ~~Bloquant~~ **LEVÉ** | Puissances par local absentes de F3 | Fournies par F3b |
| D-02 | **Majeur** | « Puissance à installer » contient déjà la relance (+23 W/m²). Avec +20 %, le total vaut 1,2 × 140,8 = 169,0 kW, contre 95,2 kW si la majoration porte sur les seules déperditions (+77 %) | Règle 1 appliquée à la lettre sur « Puissance à installer ». Bascule par `base_puissance_rapport`. **Décision requise** |
| D-03 | Majeur | Pas de plan architecte du RDC | Positions RDC lues sur le fond architecte de F1 |
| D-04 | Majeur | Régime d'eau absent | H-02 : 55/45 °C |
| D-06 | Moyen | Réseau restauration (V2V) : couleurs hors légende | Sous-réseau du départ PÉRI, dessiné aux couleurs PÉRI avec `CVC_Sous_Reseau = RESTAU` |
| D-07 | Moyen (règle 3) | Classes élém. 6 et 7 au R+1 : radiateur en façade sur ARCH_03, sur le mur de l'escalier sur CVPS_02 | Position CVPS_02 conservée et signalée. Arbitrage de l'architecte |
| D-09 | Moyen | Radiateurs sur cloisons mitoyennes : affectation ambiguë (statut `A_CONFIRMER` dans le CSV des positions) | Affectation au local le plus plausible du bilan |
| D-12 | Mineur | Note F5 : Øint du 159/4,5 = 159,3 mm imprimé (réel ≈ 150 mm) | Valeur de la note conservée. Sans effet (DN max = 65) |
| D-13 | Mineur | Colonne ΔT = 10 °C manuscrite arrondie | Recalcul exact |
| D-14 | Info | 1 mCE = 10 kPa (exact : 9,81) | Convention de la note |
| D-15 | Mineur | PÉRI retour en violet sur le plan, rouge dans la légende ; CTA de teintes différentes | Couleurs de la légende (règle 6). Les deux valeurs RGB sont dans le JSON |
| D-16 | Majeur | Aucun DWG, RVT ou IFC ; hauteurs d'étage inconnues | Relevé PDF à l'échelle 1/100 et H-11. Le JSON prévoit `import_dwg` |
| D-17 | ~~Majeur~~ **LEVÉ** | Puissances des batteries CTA inconnues | 6 fiches reçues (F6), dont la cuisine |
| D-18 | Majeur | Pas de catalogue de radiateurs | Calcul de la P50 requise. Sélection automatique dès réception du catalogue |
| D-19 | Info | Codes B21, A21… non uniques | Identifiants R0-nn / R1-nn = n° du bilan |
| D-22 | Info | Matériau précisé par la décision D1 : acier pour la distribution, cuivre pour les raccordements | Nuances à confirmer au CCTP (soudé ou fileté, brasé ou serti) |
| D-24 | Moyen | F3 (génération) − F3b (émetteurs) = 53 440 W, sur les déperditions comme sur la puissance installée | Probablement des charges hors radiateurs (CTA, ventilation…). À expliquer par le thermicien. Sans effet sur les radiateurs |
| D-25 | **Majeur** | Locaux du bilan **sans radiateur dessiné** : R0-04 réserve info (232 W), R0-17 local poubelles (783 W), R0-32 wc admin 1 (170 W), R0-43 circulation A13/A33… (593 W), **R0-44 hall maternelle (2 352 W)**, **R1-09 circulation R+1 (7 805 W)** | Puissance non couverte (14,3 kW majorés). **Aucun radiateur ajouté** (règle 3). Décision de l'architecte ou du thermicien requise. Au R+1, un ajout imposerait aussi un radiateur RDC à l'aplomb |
| D-26 | Moyen | Radiateurs **sans local** au bilan : stockage 1 (RDC), stockages 2 et 3 (R+1) | Conservés au dessin, puissance inconnue (FLAG). Supprimer ou faire chiffrer |
| D-27 | **Majeur** (règle 3) | Locaux **sous-équipés** au regard du bilan : R0-08 hall + circulation élém. (162,6 m²) avec **2 radiateurs** → 4,0 kW chacun, soit **P50 7,5 kW** ; R0-52 circulation mat 2/5/6 avec 1 radiateur → P50 8,2 kW ; R0-10 salle polyvalente et R0-27 motricité → P50 de 5,7 à 6,5 kW par radiateur ; R0-51 wc mat 4 → 5,5 kW | Un radiateur vertical 1500×750 ne peut probablement pas fournir ces puissances : **FLAG probable** dès réception du catalogue. Alternatives en § 6.4 |
| D-28 | **Majeur** (nouvelle règle R+1) | **4 des 14** radiateurs R+1 ont un radiateur RDC à ≤ 1,0 m en dessous (R1-05-a, R1-04-b, R1-08-a, NR-ST2-a). Les 10 autres sont à **1,5 à 5,1 m** du radiateur RDC ÉLÉM le plus proche | Proposition **provisoire, non appliquée au dessin** : raccordement sur le radiateur RDC ÉLÉM le plus proche, avec un parcours horizontal en plafond RDC. Options : (a) l'architecte aligne les positions RDC et R+1 ; (b) parcours horizontal accepté ; (c) piquage direct sur l'acier ÉLÉM en plafond RDC. **Décision requise** |
| D-29 | Moyen | R0-02-b (classe élém. 3) porterait 3 radiateurs R+1 et R0-08-a (hall) 1. La branche cuivre du hall atteint Cu 28 | Conséquence de D-28 : à revoir après décision |
| D-33 | Moyen | 3 symboles radiateurs du DCE manquaient au relevé visuel de la rév. B : R0-08-b (palier escalier élém.), R0-13-b (zone wc prof élé / SAS), R0-21-b (vestiaire 1, dos à dos avec la buanderie) | Ajoutés, statut `A_CONFIRMER` |
| D-34 | Moyen | Réseau relu sur le PDF : 2 liaisons supposées de 3,2 m sur le réseau restauration (tube masqué derrière les plinthes) ; 5 jonctions ambiguës ignorées pour supprimer des boucles (nourrice et classe mat 3 / 4) | Arbre retenu affiché sur le plan annoté et listé dans son cartouche. À confirmer sur le DWG |
| D-36 | **Majeur** | Les batteries CTA sont sélectionnées à **60/40 °C**, alors que les radiateurs sont calculés à 55/45 °C (H-02). La PAC doit donc produire 60 °C au départ | Le régime commun de la nourrice est à confirmer (fiche AERMEC WRL 300). Pour les radiateurs, 60/40 °C donnerait un facteur de 0,515 (θi 19 °C), proche du 55/45 actuel (0,533), et des débits divisés par 2 |
| D-37 | **Majeur** | Batteries **change-over** : le « réseau eau de chauffage CTA » du DCE transporte aussi l'eau glacée 7/12 °C l'été. Le débit froid (56,6 m³/h) est 4,3 fois le débit chaud (13,1 m³/h) | Réseau CTA dimensionné au débit froid (H-19) : DN125 au départ. Isolation anticondensation obligatoire. Confirmer la production de froid (PAC réversible / géocooling) et son raccordement à la nourrice |
| D-38 | **Majeur** | Batteries chaudes surdimensionnées : 300 kW à pleine ouverture (soufflage à 35–44 °C), pour un besoin estimé à 50 kW | Le débit chaud des fiches est conservé pour les tuyauteries (cas défavorable). Demander au fabricant une sélection au point de consigne réel et prévoir un réglage du débit (vanne d'équilibrage) |
| D-39 | Moyen | ΔP eau glacée des batteries : 137 kPa (Mat ouest) et 128 kPa (Mat est), contre 51 à 100 kPa pour les autres. La HMT du circuit CTA passe à **16,1 mCE** en froid, contre 3,4 mCE en chaud | Circulateur à sélectionner sur le cas froid, ou batteries à resélectionner (ΔP ≤ 50 kPa recommandé : valeur d'usage, à confirmer) |
| D-40 | Moyen | Affectation fiche ↔ local CTA déduite des positions : Mat ouest = CTA 5,0 m², Mat est = LT CTA 3,7 m², Motricité = CTA 4,25 m², Élém nord / sud = blocs de la terrasse R+1 (nord = haut de la feuille, supposé) | Statut `A_CONFIRMER` dans `data/cta_positions.csv` |
| D-41 | Moyen | La **CTA cuisine** n'est pas dessinée sur le plan DCE CVPS_01 (aucun symbole ni étiquette) | Position supposée dans le faux-plafond de l'office cuisine élé (E4), piquée sur le collecteur CTA de la circulation sud (branche de 1,9 m, DN32). À confirmer avec le plan de ventilation |
| D-35 | Info | Les départs PÉRI et restauration partagent le départ Admin/Péri : le tronçon commun nourrice → V2V n'est pas lisible | Dimensionné au DN du départ total (DN40, 30,6 kW) |
| D-30 | Mineur | Noms et surfaces F3b / plans : E1 « cantine élémentaire » (plan : « cantine maternelle ») ; atelier 1 = 31,88 m² (plan 30,19) ; laverie 1 = 19,60 m² (plan 5,60) ; classe 2 / classe 4 : 62,07 / 62,03 m² (plan 62,03 / 62,14) | Rapprochement par nom et position. Valeurs du bilan retenues |
| D-31 | Info | θi du bilan = 19 °C (20 °C pour les vestiaires), différente de la référence 20 °C | θi du bilan utilisée pour la conversion NF EN 442 (H-03) |
| D-32 | Mineur | R1-07-a (wc élém. 4) : le radiateur RDC le plus proche est sur le **PÉRI** (wc élém. 3, à 3,0 m) | Repli sur le radiateur ÉLÉM le plus proche (H-13), le circuit est conservé |

---

## 6. Workflow pas à pas

### 6.0 Architecture

```
 F3b bilan ─┐                                                       ┌─► outputs/*.csv (nomenclatures)
 Positions ─┼─► data/ ─► calc/calc_chauffage.py ─────────────────────┤
 Catalogue ─┤      ▲                                                └─► model/modele_chauffage_albert_camus.json
 DWG ───────┘      │                                                          │
                   └── export_network.py ◄── [ Modèle Revit ] ◄── build_from_json.py / draw_R1_links.py
                                                   ▲                 apply_results.py
                                                   └──────────────────────────┘
```

- Calcul en CPython, bibliothèque standard uniquement ; dessin dans Revit avec pyRevit.
- Le **JSON est l'interface** entre les deux : on ne redessine rien à la main tant qu'il n'a pas changé.

### 6.1 Phase 0 : à obtenir

1. DWG CVPS_01 (calques par système), DWG ou RVT architecte RDC et R+1, coupes (hauteur d'étage).
2. Régime d'eau du CCTP et fiche AERMEC.
3. Tableau des CTA.
4. Catalogue de radiateurs.
5. **Décisions D-02, D-25, D-27 et D-28.**

### 6.2 Phase 1 : inventaire

1. Remplacer les positions PDF par le **bloc « RADIATEUR A EAU » du DWG** : AutoCAD `EXTRACTDONNEES` donne X, Y, rotation et longueur. On recale ensuite avec la transformation à 2 points décrite dans `conventions.repere`.
2. Vérifier le rapprochement radiateurs ↔ locaux du bilan : D-09, D-25, D-26.

### 6.3 Phase 2 : puissances (règles 1 et 2)

Automatique depuis `bilan_emetteurs_EN12831.csv`. Résultats dans `outputs/01_locaux_puissances.csv` (§ 7.1).

### 6.4 Phase 3 : sélection (règle 3)

- Catalogue fabricant au format NF EN 442 : P50, n, H, L, type, avec la source (page).
- Le moteur retient le plus petit modèle du type dessiné avec P_régime ≥ P_part et L ≤ L_dispo, sinon **FLAG**.
- **Alternatives proposées, jamais appliquées sans accord** :
  - a) même emprise avec plus de panneaux ou une hauteur supérieure ;
  - b) radiateur supplémentaire, accepté par l'architecte (au R+1, il faut aussi un radiateur RDC à l'aplomb) ;
  - c) régime relevé si la PAC le permet ;
  - d) émetteur basse température à ventilation assistée ;
  - e) revue de la charge, en particulier sur D-02.

### 6.5 Phase 4 : dessin Revit depuis le JSON (`procedure_dessin_revit` du JSON)

| Étape | Script pyRevit (à écrire, T4) | Données JSON utilisées |
|---|---|---|
| Niveaux, lien architecte, recalage | `build_from_json.py --etape niveaux` | `niveaux`, `conventions.repere` |
| Types de canalisation acier et cuivre | `build_from_json.py --etape materiaux` | `materiaux.*.diametres` (Øint de la note F5 et NF EN 1057) |
| 10 types de systèmes avec couleur | `build_from_json.py --etape systemes` | `systemes[].rgb_legende`, `classification_revit` |
| Filtres et gabarits de vue | `build_from_json.py --etape filtres` | `filtres_vues` |
| Espaces MEP et paramètres CVC_* | `build_from_json.py --etape locaux` | `locaux` |
| Radiateurs (posés tels que dessinés, statut FLAG) | `build_from_json.py --etape radiateurs` | `radiateurs[].position_m`, `type_dessine`, `selection` |
| Distribution **acier** au RDC | `dwg_to_pipes.py` (polylignes des calques → canalisations) | `import_dwg.correspondance_calques`, `departs[].trace_RDC`, `modes_pose` |
| Piquages **cuivre** RDC | `connect_radiators.py` | `radiateurs[].raccordement` (diamètre, P transitée) |
| **R+1** : réservations et liens cuivre | `draw_R1_links.py` | `reservations_dalle`, `radiateurs[].raccordement.parent_RDC` |

**Détail R+1 (règle 4)**
- Pour chaque radiateur R+1 :
  1. réservation 150 × 80 mm dans la dalle haute du RDC, à l'axe du radiateur R+1 (famille d'ouverture ou modèle générique vide) ;
  2. té de piquage sur l'aller et le retour cuivre du radiateur RDC parent, **en amont de son robinet** ;
  3. 2 tubes cuivre verticaux à travers la réservation jusqu'au robinet du radiateur R+1.
- Si `statut_aplomb` = FLAG, le script **ne dessine pas** le parcours horizontal : il crée la réservation, marque `CVC_Statut = FLAG aplomb` et attend la décision D-28.

> **Disponible (rév. E)** : `revit/build_from_json.py` réunit les étapes ci-dessus en un seul script, lancé avec `dry_run`, piloté par `revit/config_revit.json` et documenté dans `revit/LISEZMOI.md`. Il lit le modèle JSON et `model/reseau_rdc_geometrie.json`, la géométrie du réseau RDC exportée par `tools/plan_rdc_annote.py`. **Non testé dans Revit** à ce stade.

### 6.6 Les 4 départs et les filtres de couleur

- Filtres par **type de système** (`CH-MAT-A` … `CH-CTA-R`) avec les couleurs de la légende du § 2.3.
- Filtres par **type de canalisation** : acier en trait épais, cuivre apparent en trait fin.
- Motif selon `CVC_Mode_Pose`.
- Filtres de contrôle : `FLAG` (rouge plein), `CVC_Critique = OUI` (très épais), réservations (hachures).
- Gabarits de vue : « CH - Tous circuits », puis un gabarit par circuit, par niveau.

### 6.7 Phase 5 : calcul du réseau, recalculable

1. `export_network.py` parcourt les connecteurs depuis la nourrice (un système aller par circuit). Il produit `data/troncons_<circuit>_<date>.csv` :
   - colonnes `circuit;troncon_id;amont_id;longueur_m;zeta_total;radiateurs;dn_impose;materiau` (acier ou cuivre) ;
   - le lien R+1 est un tronçon cuivre dont l'amont est la branche du radiateur RDC parent.
2. `calc_chauffage.py --troncons …` calcule :
   - le cumul depuis le radiateur le plus éloigné ;
   - les DN acier (note F5) et les diamètres cuivre (H-15) ;
   - V, Re, λ (Colebrook), J et ΔP ;
   - le circuit critique, la HMT et l'excès à laminer.
   Validé sur un réseau test mixte acier / cuivre / lien R+1 : le radiateur R+1 sort bien critique.
3. `apply_results.py` réinjecte les diamètres et les paramètres `CVC_*`.
4. **Nouveau tracé** : relancer 1 → 2 → 3. Rien d'autre ne change.

### 6.8 Phase 6 : vérifications

| Contrôle | Critère |
|---|---|
| Bilan | Σ P_part = Σ P_majorée des locaux équipés ; écart restant = D-25 uniquement |
| Vitesse | V ≤ V_max (acier selon F5, cuivre selon H-15) sur 100 % des tronçons |
| Arbre | aucune boucle ni tronçon orphelin (le moteur lève une erreur explicite) |
| R+1 | 1 réservation par radiateur R+1 ; chaque lien R+1 a un parent RDC ; aucun aplomb FLAG dessiné sans décision |
| Revit | aucun système ouvert ; rapport de perte de pression Revit vs moteur ≤ 15 % ; détection de conflits avec la dalle |
| Couleurs | chaque canalisation appartient à un type de système `CH-*` (aucune canalisation « par défaut ») |

---

## 7. Nomenclatures et résultats (régime supposé H-02, base de majoration H-01)

### 7.1 Puissances par local (règles 1 et 2) : `outputs/01_locaux_puissances.csv`

| Id | Local (bilan émetteurs) | S m² | θi | Déperd. W | P à installer W | ×1,20 W | Nb rad | W / rad | Statut |
|---|---|---|---|---|---|---|---|---|---|
| R0-01 | Salle de classe élémentaire 4 | 62.03 | 19 | 1638.1 | 3064.8 | 3678 | 2 | 1839 | OK |
| R0-02 | Salle de classe élémentaire 3 | 60.06 | 19 | 866.4 | 2247.8 | 2697 | 2 | 1349 | OK |
| R0-03 | WC élémentaire 2 | 31.53 | 19 | 475.7 | 1200.9 | 1441 | 2 | 721 | OK |
| R0-04 | Réserve info | 8.42 | 19 | 38 | 231.9 | 278 | 0 |  | **FLAG sans radiateur** |
| R0-05 | Salle de classe élémentaire 2 | 62.07 | 19 | 990.5 | 2418.2 | 2902 | 2 | 1451 | OK |
| R0-06 | Atelier élémentaire 1 | 31.88 | 19 | 677.7 | 1411.0 | 1693 | 1 | 1693 | OK |
| R0-07 | Salle de classe élémentaire 1 | 62.93 | 19 | 1914.8 | 3362.2 | 4035 | 2 | 2017 | OK |
| R0-08 | Hall + circulation élémentaire | 162.60 | 19 | 2944.2 | 6684.0 | 8021 | 2 | 4010 | OK |
| R0-09 | WC élémentaire 3 | 14.90 | 19 | 68 | 410.3 | 492 | 1 | 492 | OK |
| R0-10 | Salle polyvalente / activités périscolaires | 124.30 | 19 | 2961.3 | 5820.2 | 6984 | 2 | 3492 | OK |
| R0-11 | Rangement 1 | 6.60 | 19 | 51 | 203.0 | 244 | 1 | 244 | OK |
| R0-12 | Rangement 2 | 13.02 | 19 | 79 | 378.9 | 455 | 1 | 455 | OK |
| R0-13 | WC prof élé + Ménage 2 + SAS | 14.39 | 19 | 111.5 | 442.4 | 531 | 2 | 265 | OK |
| R0-14 | Laverie 1 élémentaire | 19.60 | 19 | 151.8 | 602.6 | 723 | 1 | 723 | OK |
| R0-15 | Cantine élémentaire / Zone de self | 125.91 | 19 | 3437.3 | 6333.2 | 7600 | 3 | 2533 | OK |
| R0-16 | Cantine élémentaire | 93.55 | 19 | 2190.5 | 4342.2 | 5211 | 2 | 2605 | OK |
| R0-17 | Local poubelles | 8.43 | 19 | 589.4 | 783.2 | 940 | 0 |  | **FLAG sans radiateur** |
| R0-18 | Salle de repos agents | 11.43 | 19 | 515.9 | 778.8 | 935 | 1 | 935 | OK |
| R0-19 | Office cuisine 1 élé + office cuisine 2 mat | 42.82 | 19 | 1525.6 | 2510.4 | 3012 | 2 | 1506 | OK |
| R0-20 | Laverie 2 mat | 12.53 | 19 | 504.9 | 793.1 | 952 | 1 | 952 | OK |
| R0-21 | Vestiaire 1 | 9.20 | 20 | 1561.5 | 1773.1 | 2128 | 2 | 1064 | OK |
| R0-22 | Buanderie | 6.38 | 19 | 984.4 | 1131.2 | 1357 | 1 | 1357 | OK |
| R0-23 | WC maternelle 2 | 5.53 | 19 | 908.3 | 1035.5 | 1243 | 1 | 1243 | OK |
| R0-24 | Ménage | 5.13 | 19 | 412.8 | 530.8 | 637 | 1 | 637 | OK |
| R0-25 | Vestiaires 2 | 10.86 | 20 | 1292.0 | 1541.7 | 1850 | 1 | 1850 | OK |
| R0-26 | Local stockage matériel d'animation | 10.73 | 19 | 340.1 | 586.9 | 704 | 1 | 704 | OK |
| R0-27 | Salle de motricité / activités périscolaires maternelles | 172.59 | 19 | 3587.0 | 7556.6 | 9068 | 3 | 3023 | OK |
| R0-28 | Couloir le long salle de motricité A23 - Zone maternelle | 46.27 | 19 | 2530.1 | 3594.3 | 4313 | 2 | 2157 | OK |
| R0-29 | WC maternelle | 27.12 | 19 | 285.9 | 909.7 | 1092 | 2 | 546 | OK |
| R0-30 | Bibliothèque | 60.70 | 19 | 1548.2 | 2944.3 | 3533 | 2 | 1767 | OK |
| R0-31 | WC admin 2 | 5.27 | 19 | 297.8 | 419.0 | 503 | 1 | 503 | OK |
| R0-32 | WC admin 1 | 5.54 | 19 | 43 | 170.4 | 204 | 0 |  | **FLAG sans radiateur** |
| R0-33 | Hall périsco | 21.15 | 19 | 1148.8 | 1635.2 | 1962 | 1 | 1962 | OK |
| R0-34 | Salle RASED | 24.47 | 19 | 627.2 | 1190.0 | 1428 | 1 | 1428 | OK |
| R0-35 | Salle des animateurs | 26.69 | 19 | 781.3 | 1395.2 | 1674 | 2 | 837 | OK |
| R0-36 | Salle des enseignants | 24.43 | 19 | 522.4 | 1084.2 | 1301 | 1 | 1301 | OK |
| R0-37 | Direction élémentaire | 12.70 | 19 | 503.7 | 795.8 | 955 | 1 | 955 | OK |
| R0-38 | Psychologue | 12.80 | 19 | 492.1 | 786.5 | 944 | 1 | 944 | OK |
| R0-39 | Direction périsco | 15.00 | 19 | 494.5 | 839.5 | 1007 | 1 | 1007 | OK |
| R0-40 | Circulation autour B12/B33/C2/D3/B13/C3/D4 | 18.29 | 19 | 171.9 | 592.6 | 711 | 1 | 711 | OK |
| R0-41 | Salle de service des ATSEM et enseignants | 28.40 | 19 | 939.6 | 1592.8 | 1911 | 1 | 1911 | OK |
| R0-42 | Direction maternelle | 12.70 | 19 | 514.9 | 807.0 | 968 | 1 | 968 | OK |
| R0-43 | Circulation autour A13/A33/A12/A24/C1/C4 | 18.29 | 19 | 171.9 | 592.6 | 711 | 0 |  | **FLAG sans radiateur** |
| R0-44 | Hall maternelle | 35.00 | 19 | 1547.3 | 2352.3 | 2823 | 0 |  | **FLAG sans radiateur** |
| R0-45 | Salle de sieste 1 | 60.26 | 19 | 1638.8 | 3024.8 | 3630 | 2 | 1815 | OK |
| R0-46 | Salle de classe maternelle 1 | 59.88 | 19 | 2008.9 | 3386.1 | 4063 | 2 | 2032 | OK |
| R0-47 | Salle de classe maternelle 2 | 59.80 | 19 | 2009.1 | 3384.5 | 4061 | 2 | 2031 | OK |
| R0-48 | Salle de sieste 2 | 60.06 | 19 | 1579.6 | 2961.0 | 3553 | 2 | 1777 | OK |
| R0-49 | Salle de classe maternelle 6 | 59.17 | 19 | 2977.2 | 4338.1 | 5206 | 2 | 2603 | OK |
| R0-50 | Salle de classe maternelle 5 | 60.49 | 19 | 2174.7 | 3566.0 | 4279 | 2 | 2140 | OK |
| R0-51 | WC maternelle 4 | 24.41 | 19 | 1902.0 | 2463.4 | 2956 | 1 | 2956 | OK |
| R0-52 | Circulation autour classes matern 2/5/6 + sieste 2 | 57.17 | 19 | 2343.1 | 3658.1 | 4390 | 1 | 4390 | OK |
| R0-53 | WC maternelle 3 | 8.94 | 19 | 184.1 | 389.7 | 468 | 1 | 468 | OK |
| R0-54 | Salle de classe maternelle 4 | 60.49 | 19 | 2266.1 | 3657.3 | 4389 | 2 | 2194 | OK |
| R0-55 | Salle de classe maternelle 3 | 60.49 | 19 | 2174.7 | 3566.0 | 4279 | 2 | 2140 | OK |
| R0-56 | Circulation autour classes matern 1/3/4 + sieste 1 | 57.17 | 19 | 400.1 | 1715.0 | 2058 | 2 | 1029 | OK |
| R1-01 | Salle de classe élémentaire 8 | 62.29 | 19 | 1852.8 | 3285.5 | 3943 | 2 | 1971 | OK |
| R1-02 | Atelier élémentaire 3 | 31.89 | 19 | 819.1 | 1552.6 | 1863 | 1 | 1863 | OK |
| R1-03 | Salle de classe élémentaire 7 | 62.14 | 19 | 1067.6 | 2496.9 | 2996 | 2 | 1498 | OK |
| R1-04 | Salle de classe élémentaire 6 | 62.14 | 19 | 1071.7 | 2500.9 | 3001 | 2 | 1501 | OK |
| R1-05 | Atelier élémentaire 2 | 30.89 | 19 | 803.4 | 1513.9 | 1817 | 1 | 1817 | OK |
| R1-06 | Salle de classe élémentaire 5 | 62.51 | 19 | 1979.9 | 3417.6 | 4101 | 2 | 2051 | OK |
| R1-07 | WC élémentaire 4 | 13.35 | 19 | 800.5 | 1107.6 | 1329 | 1 | 1329 | OK |
| R1-08 | WC élémentaire 5 | 13.54 | 19 | 848.6 | 1160.0 | 1392 | 1 | 1392 | OK |
| R1-09 | R+1 - Circulation | 122.65 | 19 | 4983.9 | 7804.9 | 9366 | 0 |  | **FLAG sans radiateur** |

### 7.2 Radiateurs : puissance, équivalent NF EN 442, raccordement et aplomb R+1 (`outputs/02_radiateurs_selection.csv`)

- Positions **x, y** dans le repère commun, à ±0,3 m (H-17).
- **Cuivre** = diamètre de la branche apparente. Pour un radiateur RDC « porteur », elle transite aussi les radiateurs R+1 qui lui sont raccordés.
- **Modèle et P_régime catalogue** : renseignés dès réception du catalogue (D-18).

| Radiateur | Circuit | Type dessiné | x m | y m | P part W | P50 requise W | Cuivre | P transitée W | Parent RDC | Écart m | Aplomb | Affectation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NR-ST1-a | ELEM | V1500x750 | 8.97 | -10.72 |  |  | Cu 16x1 | 2050 |  |  |  | A_CONFIRMER |
| R0-01-a | ELEM | V1500x750 | 0.12 | -36.98 | 1839 | 3448 | Cu 22x1 | 3810 |  |  |  | OK |
| R0-01-b | ELEM | V1500x750 | 8.57 | -42.17 | 1839 | 3448 | Cu 16x1 | 1839 |  |  |  | OK |
| R0-02-a | ELEM | V1500x750 | 0.12 | -30.51 | 1348 | 2528 | Cu 22x1 | 3212 |  |  |  | OK |
| R0-02-b | ELEM | V1500x750 | 8.61 | -34.49 | 1348 | 2528 | Cu 22x1 | 3320 |  |  |  | OK |
| R0-03-a | ELEM | V1500x750 | 0.69 | -24.98 | 720 | 1351 | Cu 18x1 | 2218 |  |  |  | OK |
| R0-03-b | ELEM | V1500x750 | 8.99 | -27.53 | 720 | 1351 | Cu 18x1 | 2218 |  |  |  | OK |
| R0-05-a | ELEM | V1500x750 | 0.12 | -16.27 | 1451 | 2720 | Cu 22x1 | 2952 |  |  |  | OK |
| R0-05-b | ELEM | V1500x750 | 8.65 | -19.29 | 1451 | 2720 | Cu 14x1 | 1451 |  |  |  | OK |
| R0-06-a | ELEM | V1500x750 | 0.13 | -8.84 | 1693 | 3174 | Cu 22x1 | 3510 |  |  |  | OK |
| R0-07-a | ELEM | V1500x750 | 0.12 | -5.95 | 2018 | 3782 | Cu 22x1 | 4068 |  |  |  | OK |
| R0-07-b | ELEM | V1500x750 | 8.36 | -0.98 | 2018 | 3782 | Cu 16x1 | 2018 |  |  |  | OK |
| R0-08-a | ELEM | V1500x750 | 8.22 | -13.16 | 4010 | 7519 | Cu 28x1 | 5511 |  |  |  | A_CONFIRMER |
| R0-08-b | ELEM | V1500x750 | 8.06 | -24.68 | 4010 | 7519 | Cu 22x1 | 4010 |  |  |  | A_CONFIRMER |
| R0-09-a | PERI | V1500x750 | 12.98 | -8.12 | 492 | 922 | Cu 12x1 | 492 |  |  |  | OK |
| R0-10-a | ELEM | V1500x750 | 12.61 | -14.8 | 3492 | 6547 | Cu 22x1 | 4821 |  |  |  | OK |
| R0-10-b | ELEM | V1500x750 | 20.4 | -15.29 | 3492 | 6547 | Cu 22x1 | 3492 |  |  |  | A_CONFIRMER |
| R0-11-a | ELEM | V1500x750 | 20.48 | -27.67 | 244 | 457 | Cu 12x1 | 244 |  |  |  | A_CONFIRMER |
| R0-12-a | PERI | V1500x750 | 18.54 | -8.12 | 455 | 853 | Cu 12x1 | 455 |  |  |  | OK |
| R0-13-a | ELEM | V1500x750 | 12.61 | -28.25 | 266 | 498 | Cu 12x1 | 266 |  |  |  | A_CONFIRMER |
| R0-13-b | ELEM | V1500x750 | 14.16 | -34.24 | 266 | 498 | Cu 16x1 | 1658 |  |  |  | A_CONFIRMER |
| R0-14-a | ELEM | V1500x750 | 17.58 | -31.48 | 723 | 1355 | Cu 12x1 | 723 |  |  |  | OK |
| R0-15-a | PERI-RESTAU | PLINTHE | 23.14 | -28.42 | 2533 | 4749 | Cu 18x1 | 2533 |  |  |  | A_CONFIRMER |
| R0-15-b | PERI-RESTAU | PLINTHE | 26.99 | -28.42 | 2533 | 4749 | Cu 18x1 | 2533 |  |  |  | A_CONFIRMER |
| R0-15-c | PERI-RESTAU | PLINTHE | 34.63 | -28.42 | 2533 | 4749 | Cu 18x1 | 2533 |  |  |  | A_CONFIRMER |
| R0-16-a | PERI-RESTAU | PLINTHE | 42.21 | -28.42 | 2606 | 4885 | Cu 18x1 | 2606 |  |  |  | A_CONFIRMER |
| R0-16-b | PERI-RESTAU | PLINTHE | 46.04 | -28.42 | 2606 | 4885 | Cu 18x1 | 2606 |  |  |  | A_CONFIRMER |
| R0-18-a | PERI-RESTAU | V1500x750 | 21.6 | -37.52 | 935 | 1753 | Cu 12x1 | 935 |  |  |  | A_CONFIRMER |
| R0-19-a | MAT | V1500x750 | 27.29 | -37.72 | 1506 | 2823 | Cu 14x1 | 1506 |  |  |  | OK |
| R0-19-b | MAT | V1500x750 | 43.16 | -36.98 | 1506 | 2823 | Cu 14x1 | 1506 |  |  |  | OK |
| R0-20-a | MAT | V1500x750 | 45.85 | -37.09 | 952 | 1785 | Cu 12x1 | 952 |  |  |  | OK |
| R0-21-a | MAT | V1500x750 | 50.14 | -38.89 | 1064 | 2083 | Cu 14x1 | 1064 |  |  |  | OK |
| R0-21-b | MAT | V1500x750 | 53.25 | -38.42 | 1064 | 2083 | Cu 14x1 | 1064 |  |  |  | A_CONFIRMER |
| R0-22-a | MAT | V1500x750 | 53.54 | -38.41 | 1357 | 2544 | Cu 14x1 | 1357 |  |  |  | OK |
| R0-23-a | MAT | V1500x750 | 55.75 | -37.38 | 1243 | 2330 | Cu 14x1 | 1243 |  |  |  | OK |
| R0-24-a | MAT | V1500x750 | 48.25 | -29.17 | 637 | 1194 | Cu 12x1 | 637 |  |  |  | A_CONFIRMER |
| R0-25-a | MAT | V1500x750 | 49.89 | -32.86 | 1850 | 3622 | Cu 16x1 | 1850 |  |  |  | OK |
| R0-26-a | MAT | V1500x750 | 55.05 | -31.07 | 704 | 1320 | Cu 12x1 | 704 |  |  |  | OK |
| R0-27-a | MAT | V1500x750 | 48.26 | -13.34 | 3023 | 5667 | Cu 22x1 | 3023 |  |  |  | OK |
| R0-27-b | MAT | V1500x750 | 55.44 | -11.97 | 3023 | 5667 | Cu 22x1 | 3023 |  |  |  | OK |
| R0-27-c | MAT | V1500x750 | 58.86 | -18.48 | 3023 | 5667 | Cu 22x1 | 3023 |  |  |  | A_CONFIRMER |
| R0-28-a | MAT | V1500x750 | 53.96 | -34.8 | 2156 | 4043 | Cu 18x1 | 2156 |  |  |  | A_CONFIRMER |
| R0-28-b | MAT | V1500x750 | 52.75 | -34.49 | 2156 | 4043 | Cu 18x1 | 2156 |  |  |  | A_CONFIRMER |
| R0-29-a | MAT | V1500x750 | 48.22 | -9.96 | 546 | 1024 | Cu 12x1 | 546 |  |  |  | OK |
| R0-29-b | MAT | V1500x750 | 55.88 | -8.15 | 546 | 1024 | Cu 12x1 | 546 |  |  |  | OK |
| R0-30-a | PERI | V1500x750 | 38.5 | -8.12 | 1766 | 3312 | Cu 16x1 | 1766 |  |  |  | OK |
| R0-30-b | PERI | V1500x750 | 46.07 | -8.55 | 1766 | 3312 | Cu 16x1 | 1766 |  |  |  | OK |
| R0-31-a | PERI | V1500x750 | 37.9 | -13.32 | 503 | 943 | Cu 12x1 | 503 |  |  |  | A_CONFIRMER |
| R0-33-a | PERI | V1500x750 | 35.45 | -9.65 | 1962 | 3678 | Cu 16x1 | 1962 |  |  |  | A_CONFIRMER |
| R0-34-a | PERI | V1500x750 | 29.39 | -9.09 | 1428 | 2677 | Cu 14x1 | 1428 |  |  |  | A_CONFIRMER |
| R0-35-a | PERI | V1500x750 | 23.65 | -12.44 | 837 | 1569 | Cu 12x1 | 837 |  |  |  | OK |
| R0-35-b | PERI | V1500x750 | 29.09 | -9.09 | 837 | 1569 | Cu 12x1 | 837 |  |  |  | A_CONFIRMER |
| R0-36-a | PERI | V1500x750 | 21.45 | -8.66 | 1301 | 2439 | Cu 14x1 | 1301 |  |  |  | OK |
| R0-37-a | PERI | V1500x750 | 20.31 | -6.3 | 955 | 1790 | Cu 12x1 | 955 |  |  |  | OK |
| R0-38-a | PERI | V1500x750 | 26.06 | -6.29 | 944 | 1770 | Cu 12x1 | 944 |  |  |  | A_CONFIRMER |
| R0-39-a | PERI | V1500x750 | 26.82 | -4.44 | 1007 | 1888 | Cu 12x1 | 1007 |  |  |  | OK |
| R0-40-a | PERI | V1500x750 | 27.59 | -8.12 | 711 | 1333 | Cu 12x1 | 711 |  |  |  | A_CONFIRMER |
| R0-41-a | PERI | V1500x750 | 42.09 | -4.45 | 1911 | 3583 | Cu 16x1 | 1911 |  |  |  | OK |
| R0-42-a | MAT | V1500x750 | 51.6 | -3.34 | 968 | 1815 | Cu 12x1 | 968 |  |  |  | OK |
| R0-45-a | MAT | V1500x750 | 70.28 | -0.79 | 1815 | 3403 | Cu 16x1 | 1815 |  |  |  | OK |
| R0-45-b | MAT | V1500x750 | 63.6 | -7.79 | 1815 | 3403 | Cu 16x1 | 1815 |  |  |  | OK |
| R0-46-a | MAT | V1500x750 | 71.7 | -0.8 | 2032 | 3809 | Cu 16x1 | 2032 |  |  |  | OK |
| R0-46-b | MAT | V1500x750 | 73.24 | -8.66 | 2032 | 3809 | Cu 16x1 | 2032 |  |  |  | OK |
| R0-47-a | MAT | V1500x750 | 89.05 | -0.8 | 2030 | 3807 | Cu 16x1 | 2030 |  |  |  | OK |
| R0-47-b | MAT | V1500x750 | 90.13 | -8.65 | 2030 | 3807 | Cu 16x1 | 2030 |  |  |  | OK |
| R0-48-a | MAT | V1500x750 | 96.8 | -0.8 | 1776 | 3331 | Cu 16x1 | 1776 |  |  |  | OK |
| R0-48-b | MAT | V1500x750 | 103.59 | -7.81 | 1776 | 3331 | Cu 16x1 | 1776 |  |  |  | OK |
| R0-49-a | MAT | V1500x750 | 107.71 | -12.19 | 2603 | 4880 | Cu 18x1 | 2603 |  |  |  | OK |
| R0-49-b | MAT | V1500x750 | 107.7 | -18.6 | 2603 | 4880 | Cu 18x1 | 2603 |  |  |  | OK |
| R0-50-a | MAT | V1500x750 | 92.41 | -12.09 | 2140 | 4011 | Cu 18x1 | 2140 |  |  |  | OK |
| R0-50-b | MAT | V1500x750 | 92.4 | -18.77 | 2140 | 4011 | Cu 18x1 | 2140 |  |  |  | OK |
| R0-51-a | MAT | V1500x750 | 90.82 | -12.28 | 2956 | 5542 | Cu 22x1 | 2956 |  |  |  | A_CONFIRMER |
| R0-52-a | MAT | V1500x750 | 94.0 | -11.26 | 4390 | 8230 | Cu 22x1 | 4390 |  |  |  | A_CONFIRMER |
| R0-53-a | MAT | V1500x750 | 75.18 | -13.29 | 468 | 877 | Cu 12x1 | 468 |  |  |  | OK |
| R0-54-a | MAT | V1500x750 | 74.78 | -12.12 | 2194 | 4114 | Cu 18x1 | 2194 |  |  |  | OK |
| R0-54-b | MAT | V1500x750 | 74.78 | -18.54 | 2194 | 4114 | Cu 18x1 | 2194 |  |  |  | OK |
| R0-55-a | MAT | V1500x750 | 60.09 | -11.26 | 2140 | 4011 | Cu 18x1 | 2140 |  |  |  | OK |
| R0-55-b | MAT | V1500x750 | 59.5 | -18.77 | 2140 | 4011 | Cu 18x1 | 2140 |  |  |  | OK |
| R0-56-a | MAT | V1500x750 | 75.61 | -9.06 | 1029 | 1929 | Cu 12x1 | 1029 |  |  |  | A_CONFIRMER |
| R0-56-b | MAT | V1500x750 | 66.94 | -12.12 | 1029 | 1929 | Cu 12x1 | 1029 |  |  |  | A_CONFIRMER |
| NR-ST2-a | ELEM | NON_SPECIFIE | 8.96 | -10.59 |  |  | Cu 12x1 | 0 | NR-ST1-a | 0.13 | OK | A_CONFIRMER |
| NR-ST3-a | ELEM | NON_SPECIFIE | 8.96 | -31.87 |  |  | Cu 12x1 | 0 | R0-02-b | 2.64 | **FLAG** | A_CONFIRMER |
| R1-01-a | ELEM | NON_SPECIFIE | 0.13 | -41.84 | 1972 | 3696 | Cu 16x1 | 1972 | R0-01-a | 4.86 | **FLAG** | OK |
| R1-01-b | ELEM | NON_SPECIFIE | 7.81 | -35.75 | 1972 | 3696 | Cu 16x1 | 1972 | R0-02-b | 1.49 | **FLAG** | OK |
| R1-02-a | ELEM | NON_SPECIFIE | 0.13 | -32.44 | 1863 | 3493 | Cu 16x1 | 1863 | R0-02-a | 1.93 | **FLAG** | OK |
| R1-03-a | ELEM | NON_SPECIFIE | 0.79 | -22.92 | 1498 | 2808 | Cu 14x1 | 1498 | R0-03-a | 2.06 | **FLAG** | A_CONFIRMER |
| R1-03-b | ELEM | NON_SPECIFIE | 8.04 | -29.85 | 1498 | 2808 | Cu 14x1 | 1498 | R0-03-b | 2.51 | **FLAG** | OK |
| R1-04-a | ELEM | NON_SPECIFIE | 0.78 | -20.09 | 1500 | 2813 | Cu 14x1 | 1500 | R0-05-a | 3.88 | **FLAG** | A_CONFIRMER |
| R1-04-b | ELEM | NON_SPECIFIE | 8.03 | -13.16 | 1500 | 2813 | Cu 14x1 | 1500 | R0-08-a | 0.19 | OK | OK |
| R1-05-a | ELEM | NON_SPECIFIE | 0.13 | -9.36 | 1817 | 3406 | Cu 16x1 | 1817 | R0-06-a | 0.52 | OK | OK |
| R1-06-a | ELEM | NON_SPECIFIE | 0.13 | -2.04 | 2050 | 3844 | Cu 16x1 | 2050 | R0-07-a | 3.91 | **FLAG** | OK |
| R1-06-b | ELEM | NON_SPECIFIE | 7.63 | -7.44 | 2050 | 3844 | Cu 16x1 | 2050 | NR-ST1-a | 3.54 | **FLAG** | OK |
| R1-07-a | ELEM | NON_SPECIFIE | 14.83 | -10.26 | 1329 | 2492 | Cu 14x1 | 1329 | R0-10-a | 5.05 | **FLAG** | OK |
| R1-08-a | ELEM | NON_SPECIFIE | 13.23 | -34.1 | 1392 | 2610 | Cu 14x1 | 1392 | R0-13-b | 0.94 | OK | OK |

### 7.3 Synthèse par départ : `outputs/04_synthese_circuits.csv`

| Circuit | Nb émetteurs | Sans puissance | P kW | Qv m³/h | DN départ | Désignation |
|---|---|---|---|---|---|---|
| ELEM | 34 | 3 | 53.39 | 4.59 | 50 | 50/60 |
| MAT | 39 | 0 | 70.66 | 6.08 | 65 | 66/76 |
| PERI | 15 | 0 | 16.88 | 1.45 | 32 | 33/42 |
| PERI-RESTAU | 6 | 0 | 13.75 | 1.18 | 32 | 33/42 |
| PERI (départ total) | 21 | 0 | 30.63 | 2.63 | 40 | 40/49 |
| CTA | 6 | 0 | 299.58 | 57.64 | 125 | 125/133 |

> Les radiateurs R+1 sont comptés dans le circuit de leur radiateur RDC parent (tous sur ÉLÉM). Ligne CTA : P = puissance max des batteries des 6 CTA (fiches, 60/40 °C) ; Qv = débit de dimensionnement max(chaud, froid). « Sans puissance » désigne les stockages absents du bilan (D-26).

### 7.4 Réservations de dalle R+1 : `outputs/07_reservations_dalle_R1.csv`

| Réservation | Radiateur R+1 | Radiateur RDC | x m | y m | Dim. mm | Tubes | Statut |
|---|---|---|---|---|---|---|---|
| RES-R1-01 | NR-ST2-a | NR-ST1-a | 8.96 | -10.59 | 150x80 | 2 × Cu 12x1 | OK |
| RES-R1-02 | NR-ST3-a | R0-02-b | 8.96 | -31.87 | 150x80 | 2 × Cu 12x1 | A_VALIDER (pas d'aplomb RDC) |
| RES-R1-03 | R1-01-a | R0-01-a | 0.13 | -41.84 | 150x80 | 2 × Cu 16x1 | A_VALIDER (pas d'aplomb RDC) |
| RES-R1-04 | R1-01-b | R0-02-b | 7.81 | -35.75 | 150x80 | 2 × Cu 16x1 | A_VALIDER (pas d'aplomb RDC) |
| RES-R1-05 | R1-02-a | R0-02-a | 0.13 | -32.44 | 150x80 | 2 × Cu 16x1 | A_VALIDER (pas d'aplomb RDC) |
| RES-R1-06 | R1-03-a | R0-03-a | 0.79 | -22.92 | 150x80 | 2 × Cu 14x1 | A_VALIDER (pas d'aplomb RDC) |
| RES-R1-07 | R1-03-b | R0-03-b | 8.04 | -29.85 | 150x80 | 2 × Cu 14x1 | A_VALIDER (pas d'aplomb RDC) |
| RES-R1-08 | R1-04-a | R0-05-a | 0.78 | -20.09 | 150x80 | 2 × Cu 14x1 | A_VALIDER (pas d'aplomb RDC) |
| RES-R1-09 | R1-04-b | R0-08-a | 8.03 | -13.16 | 150x80 | 2 × Cu 14x1 | OK |
| RES-R1-10 | R1-05-a | R0-06-a | 0.13 | -9.36 | 150x80 | 2 × Cu 16x1 | OK |
| RES-R1-11 | R1-06-a | R0-07-a | 0.13 | -2.04 | 150x80 | 2 × Cu 16x1 | A_VALIDER (pas d'aplomb RDC) |
| RES-R1-12 | R1-06-b | NR-ST1-a | 7.63 | -7.44 | 150x80 | 2 × Cu 16x1 | A_VALIDER (pas d'aplomb RDC) |
| RES-R1-13 | R1-07-a | R0-10-a | 14.83 | -10.26 | 150x80 | 2 × Cu 14x1 | A_VALIDER (pas d'aplomb RDC) |
| RES-R1-14 | R1-08-a | R0-13-b | 13.23 | -34.1 | 150x80 | 2 × Cu 14x1 | OK |

### 7.5 Tables de diamètres au régime projet (ΔT = 10 K) : `outputs/03_table_DN_regime_projet.csv`

| Matériau | Désignation | Øint mm | V max m/s | Qv max m³/h | P max kW (ΔT 10 K) | ΔT 10 manuscrit |
|---|---|---|---|---|---|---|
| acier | 15/21 | 16.6 | 0.32 | 0.249 | 2.9 | 2.9 |
| acier | 20/27 | 22.2 | 0.4 | 0.557 | 6.48 | 6.5 |
| acier | 26/34 | 27.9 | 0.45 | 0.99 | 11.52 | 11.6 |
| acier | 33/42 | 36.6 | 0.55 | 2.083 | 24.23 | 24.36 |
| acier | 40/49 | 42.5 | 0.6 | 3.064 | 35.64 | 35.96 |
| acier | 50/60 | 53.8 | 0.7 | 5.729 | 66.62 | 66.12 |
| acier | 66/76 | 68.8 | 0.85 | 11.376 | 132.3 | 132.44 |
| acier | 80/89 | 82.5 | 1.0 | 19.244 | 223.81 | 222 |
| acier | 102/114 | 107.1 | 1.6 | 51.891 | 603.49 | 602 |
| acier | 125/133 | 125.0 | 1.8 | 79.522 | 924.84 | 922 |
| acier | 159/4,5 | 159.3 | 2.0 | 143.501 | 1668.91 | 1663.44 |
| acier | 193/5,4 | 182.5 | 2.25 | 211.885 | 2464.22 | 2456 |
| acier | 219/5,6 | 206.5 | 2.5 | 301.42 | 3505.52 | 3496 |
| acier | 273/6,6 | 260.4 | 2.9 | 555.997 | 6466.24 | 6446 |
| cuivre | Cu 12x1 | 10.0 | 0.32 | 0.09 | 1.05 |  |
| cuivre | Cu 14x1 | 12.0 | 0.32 | 0.13 | 1.52 |  |
| cuivre | Cu 16x1 | 14.0 | 0.32 | 0.177 | 2.06 |  |
| cuivre | Cu 18x1 | 16.0 | 0.32 | 0.232 | 2.69 |  |
| cuivre | Cu 22x1 | 20.0 | 0.369 | 0.417 | 4.85 |  |
| cuivre | Cu 28x1 | 26.0 | 0.433 | 0.828 | 9.63 |  |
| cuivre | Cu 35x1,5 | 32.0 | 0.497 | 1.439 | 16.74 |  |
| cuivre | Cu 42x1,5 | 39.0 | 0.57 | 2.453 | 28.53 |  |

### 7.6 Réseau RDC et circuits critiques (`outputs/05_troncons_dimensionnement.csv`, `outputs/06_chemins_circuit_critique.csv`)

- Le tracé ALLER de CVPS_01 est relu sur le PDF vectoriel (calque `VIV02_CHA_RES_ECH_A`, couleur = circuit). Les tirets sont fusionnés en tubes, puis on reconstitue un arbre collecteur → radiateurs (`tools/plan_rdc_annote.py`). Les tronçons sont dans `data/troncons_RDC_DCE.csv`.
- Matériau : **acier** tant que le tronçon dessert plus d'un radiateur, **cuivre** du té de piquage au radiateur, plus les liens R+1.
- Longueurs : en plan, plus 2,5 m de descente par branche cuivre (H-18). ΔP terminal 10 kPa (H-07). Pertes singulières forfaitaires 30 % (H-06).

| Circuit | Radiateur critique | Longueur aller | ΔP chemin | HMT (hors chaufferie) |
|---|---|---|---|---|
| ÉLÉM | **R1-06-a** (classe élém. 5, R+1, par le lien vertical) | 61,4 m | 20,3 kPa | 2,03 mCE |
| MAT | **R0-49-b** (classe maternelle 6) | 126,1 m | 29,1 kPa | 2,91 mCE |
| PÉRI | **R0-30-b** (bibliothèque) | 79,7 m | 21,7 kPa | 2,17 mCE |
| Restauration | R0-16-a (cantine E1) | 40,7 m | 17,1 kPa | 1,71 mCE |

> Les pertes de la chaufferie (nourrice, bouteille, vannes) sont à ajouter pour choisir les circulateurs. Les excès de pression à laminer par radiateur sont dans `06_chemins_circuit_critique.csv`.

**Plan annoté** : `outputs/CVPS_01_RDC_radiateurs_diametres.pdf`. Chaque radiateur porte son identifiant, sa puissance et les radiateurs R+1 qu'il alimente. Chaque tube porte son diamètre au départ et à chaque changement de section (DN acier avec la puissance transitée, ou Cu). Le cartouche reprend les hypothèses et les points de relecture.

### 7.7 Réseau CTA (`outputs/08_cta_batteries.csv`, `09_troncons_CTA.csv`, `10_chemins_CTA.csv`)

| Tronçon | Amont | L m | Dessert | Qv chaud m³/h | DN chaud | Qv froid m³/h | DN froid | **DN retenu** |
|---|---|---|---|---|---|---|---|---|
| CT001 | SOURCE | 0.39 |  | 13.5 | 80 | 57.636 | 125 | **125** (125/133) |
| CT002 | CT001 | 11.77 |  | 5.051 | 50 | 23.353 | 100 | **100** (102/114) |
| B-CTA-CUISINE | CT002 | 1.89 | CTA-CUISINE | 0.443 | 20 | 1.055 | 32 | **32** (33/42) |
| CT003 | CT002 | 27.48 |  | 4.608 | 50 | 22.298 | 100 | **100** (102/114) |
| CT004 | CT003 | 30.17 |  | 3.499 | 50 | 16.948 | 80 | **80** (80/89) |
| CT005 | CT004 | 40.26 | CTA-MAT-EST | 1.721 | 32 | 8.33 | 65 | **65** (66/76) |
| CT006 | CT004 | 5.89 | CTA-MAT-OUEST | 1.778 | 32 | 8.618 | 65 | **65** (66/76) |
| CT007 | CT003 | 2.57 | CTA-MAT-MOTRICITE | 1.109 | 32 | 5.35 | 50 | **50** (50/60) |
| CT008 | CT001 | 0.23 |  | 8.449 | 65 | 34.283 | 100 | **100** (102/114) |
| CT-R1-MONTEE | CT008 | 4.45 |  | 8.449 | 65 | 34.283 | 100 | **100** (102/114) |
| CT-R1-NORD | CT-R1-MONTEE | 1.2 | CTA-ELEM-NORD | 4.309 | 50 | 14.191 | 80 | **80** (80/89) |
| CT-R1-SUD | CT-R1-MONTEE | 0.49 | CTA-ELEM-SUD | 4.14 | 50 | 20.092 | 100 | **100** (102/114) |

| Cas | CTA critique | Longueur aller | ΔP chemin | HMT (hors chaufferie) |
|---|---|---|---|---|
| chaud | CTA-MAT-EST | 110.1 m | 34.0 kPa | 3.4 mCE |
| froid | CTA-MAT-OUEST | 75.7 m | 161.6 kPa | 16.16 mCE |

> La colonne vers la terrasse R+1 est reconstituée d'après CVPS_02 : hauteur d'étage (H-11), puis 0,95 m, 1,2 m et 0,5 m en terrasse. Les ΔP terminaux = ΔP batterie (fiche) + vanne (H-20).

---

## 8. PROMPT POUR L'AGENT DE CODAGE (à coller tel quel, avec les fichiers)

````text
RÔLE
Tu es ingénieur BIM MEP senior (chauffage à eau chaude : radiateurs, hydraulique) et développeur
Python / pyRevit. Lis ENTIÈREMENT `chauffage-albert-camus/DOSSIER_PROJET_CHAUFFAGE.md`, puis
`chauffage-albert-camus/model/modele_chauffage_albert_camus.json`. Le dossier fait foi pour les règles,
les hypothèses H-xx et les écarts D-xx. Le JSON est la description du modèle à dessiner.

PROJET
Groupe scolaire Albert Camus, Talence (33), H2c, θe = -5 °C, NF EN 12831. Production : PAC eau/eau
AERMEC WRL 300, ballons tampons 500 L + 750 L, bouteille de mélange, nourrice de 4 départs :
PERI (Admin/Péri + restauration par V2V), ELEM, CTA, MAT.

ENTRÉES
- PDF : F1 CVPS_01 (RDC), F2 CVPS_02 (R+1), F3 et F3b bilans EN 12831 (F3b = puissances par local),
  F4 ARCH_03 (étage), F5 note de dimensionnement.
- data/ : bilan_emetteurs_EN12831.csv (65 locaux) ; cta_fiches.json + cta_positions.csv (6 CTA, batteries change-over) ; radiateurs_positions_PROVISOIRE.csv (94) ; troncons_RDC_DCE.csv (réseau RDC relu) ;
  hypotheses.json ; table_dimensionnement_methode.csv (acier, note F5) ; table_cuivre_NF_EN_1057.csv ;
  modele_base.json ; catalogue_radiateurs.csv (s'il existe) ; troncons_*.csv (export Revit).
- Si tu reçois des DWG, RVT, coupes, CCTP, catalogue ou tableau des CTA : ils REMPLACENT l'hypothèse
  correspondante. Mets à jour data/ et relance ; ne modifie jamais le JSON généré à la main.

RÈGLES NON NÉGOCIABLES
1. P_majorée = P_rapport × 1,20 (colonne définie par base_puissance_rapport, cf. D-02).
2. n radiateurs dans un local : P_part = P_majorée / n, à parts égales.
3. Position et taille = architecte. Si un radiateur ne rentre pas : FLAG et alternatives classées (§ 6.4).
   Ne jamais déplacer, agrandir, ajouter ou supprimer un radiateur sans accord écrit.
4. RDC : tracé DCE CVPS_01. R+1 : AUCUNE distribution ; chaque radiateur R+1 est raccordé en cuivre
   depuis le radiateur RDC à l'aplomb (piquage en amont de son robinet), par une réservation de dalle
   par radiateur. Sans aplomb (> tolerance_aplomb_m) : FLAG, réservation créée, parcours non dessiné.
5. Dimensionnement du radiateur le plus éloigné vers la source : Qv = P/(1,163·ΔT) ; acier = plus petit DN
   avec Qv ≤ π/4·Øint²·V_max (note F5) ; cuivre NF EN 1057 avec V_max transposée (H-15) ; 1 mCE = 10 kPa.
6. Couleurs = légende DCE (systemes[].rgb_legende) ; distribution principale en ACIER
   (CH_Acier_EN10255) ; raccordements apparents et liens R+1 en CUIVRE (CH_Cuivre_EN1057).
7. Puissance des radiateurs = catalogue fabricant au régime projet (NF EN 442-2, n du fabricant), jamais
   la valeur nominale 75/65/20 seule.

TÂCHES, DANS CET ORDRE
T1. `python3 -m unittest calc/test_calc.py` puis `python3 calc/calc_chauffage.py` : vérifier que les
    sorties et le JSON sont reproduits.
T2. DWG reçus : remplacer les positions par les blocs « RADIATEUR A EAU » (transformation à 2 points,
    conventions.repere), remplir import_dwg.correspondance_calques, relancer et recalculer les aplombs R+1
    (D-28).
T3. Catalogue reçu : construire data/catalogue_radiateurs.csv avec la source (référence et page), relancer,
    puis lister les FLAG avec alternatives (règle 3), en particulier D-27.
T4. Écrire dans revit/ des scripts pyRevit compatibles Revit 2024+ et moteur CPython, chacun avec un mode
    --dry-run qui n'écrit rien, et qui lisent UNIQUEMENT le JSON :
    build_from_json.py (étapes niveaux, materiaux, systemes, filtres, locaux, radiateurs),
    dwg_to_pipes.py (distribution acier RDC), connect_radiators.py (piquages cuivre),
    draw_R1_links.py (réservations + liens cuivre R+1), export_network.py (tronçons → data/troncons_*.csv),
    apply_results.py (diamètres + paramètres CVC_*).
T5. Générer outputs/note_calcul.md : nomenclatures, circuit critique et HMT par départ, liste des FLAG,
    réservations, D-xx ouverts.
T6. Tests supplémentaires : radiateur orphelin dans un tronçon, DN imposé sous-dimensionné, régime
    incompatible (θr ≤ θi), JSON conforme (94 radiateurs, 14 réservations, 10 systèmes).

DONNÉES MANQUANTES, AMBIGUËS OU INCOHÉRENTES : PROCÉDURE OBLIGATOIRE
- Ne jamais inventer une valeur. Toute valeur non sourcée devient une hypothèse H-xx dans hypotheses.json
  (source ou mention « hypothèse »).
- Chaque problème devient une ligne D-xx (constat, gravité, hypothèse retenue) : appliquer l'option la plus
  prudente, continuer, puis tout lister à la fin.
- Ne t'arrête que si poursuivre produirait un résultat faux impossible à signaler, et dis alors exactement
  ce qui manque.
- Toute citation de norme (NF EN 12831-1, NF EN 442-2, NF EN 215, NF EN 10255, NF EN 1057, NF DTU 65.10,
  NF DTU 65.11, NF EN 14336) pointe vers la clause utilisée, sinon « à vérifier ».

SORTIES
outputs/01 à 07 (CSV), outputs/note_calcul.md, model/modele_chauffage_albert_camus.json (régénéré),
revit/*.py, DOSSIER_PROJET_CHAUFFAGE.md mis à jour (§ 5 et § 7).

CONTRÔLES AVANT DE RENDRE
Σ P_part = Σ P_majorée des locaux équipés ; V ≤ V_max partout ; aucun tronçon orphelin ;
1 réservation par radiateur R+1 ; tous les tests passent ; aucun chiffre sans origine (bilan,
catalogue, DWG ou H-xx) ; français technique du projet.
````

---

## 9. Références

| Référence | Usage |
|---|---|
| Note F5 « Dimensionnement réseau hydraulique » | **Autorité principale** : DN, V_max, P = 1,163·Qv·ΔT, 1 mCE = 10 kPa |
| NF EN 12831-1 | Bilan F3 / F3b ; puissance à installer = D + 23 W/m² (relance) |
| NF EN 442-2 | Conditions 75/65/20, Φ = K·ΔT_lm^n, conversion au régime projet |
| NF EN 215 | Robinets thermostatiques : ΔP terminal, préréglage (H-07) |
| NF EN 10255 | Tubes acier de la distribution principale |
| NF EN 1057 | Tubes cuivre des raccordements apparents |
| NF DTU 65.10 / NF DTU 65.11 | Mise en œuvre des canalisations et dispositifs de sécurité du chauffage central |
| NF EN 14336 | Mise en service et équilibrage |
| Fiche AERMEC WRL 300, catalogue des radiateurs | **À obtenir** (H-02, D-18) |

> Versions et clauses à vérifier sur la base normative du projet. Aucune valeur numérique n'est tirée
> d'une norme sans être signalée comme hypothèse.

---

## 10. Arborescence

```
chauffage-albert-camus/
├── DOSSIER_PROJET_CHAUFFAGE.md            ← ce document
├── PROMPT_MODELISATION_REVIT.md          ← prompt pour l'agent qui construit le modèle dans Revit
├── model/
│   ├── modele_chauffage_albert_camus.json  ← modèle à dessiner (GÉNÉRÉ)
│   └── reseau_rdc_geometrie.json           ← polylignes du réseau RDC (GÉNÉRÉ)
├── data/
│   ├── hypotheses.json                     ← H-xx modifiables
│   ├── bilan_emetteurs_EN12831.csv         ← F3b retranscrit (65 locaux)
│   ├── radiateurs_positions_PROVISOIRE.csv ← 94 radiateurs (symboles vectoriels des PDF)
│   ├── troncons_RDC_DCE.csv                ← réseau RDC relu sur CVPS_01 (radiateurs + CTA)
│   ├── cta_fiches.json                     ← 6 fiches CTA France Air (F6)
│   ├── cta_positions.csv                   ← position et piquage de chaque CTA
│   ├── modele_base.json                    ← partie fixe du JSON (systèmes, couleurs, départs…)
│   ├── table_dimensionnement_methode.csv   ← note F5 (acier)
│   ├── table_cuivre_NF_EN_1057.csv
│   └── catalogue_radiateurs_TEMPLATE.csv
├── calc/
│   ├── calc_chauffage.py                   ← moteur (stdlib)
│   └── test_calc.py                        ← 9 tests
├── tools/
│   └── plan_rdc_annote.py                  ← relecture du réseau PDF + plan annoté (PyMuPDF)
├── revit/
│   ├── build_from_json.py                  ← construction du modèle Revit (pyRevit, dry_run)
│   ├── config_revit.json                   ← familles, calage, hauteurs, étapes
│   ├── LISEZMOI.md                         ← mode opératoire
│   └── export_projet_revit.py              ← export Revit en lecture seule (pyRevit)
└── outputs/                                ← CSV 01 à 10 + plan RDC annoté (PDF)
```

> Les PDF sources ne sont pas versionnés (documents du client) : il faut les joindre à la session de l'agent.
