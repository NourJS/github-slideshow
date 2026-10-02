# Construire le modèle chauffage dans Revit

Le script `build_from_json.py` dessine le modèle à partir des fichiers générés :
`model/modele_chauffage_albert_camus.json` et `model/reseau_rdc_geometrie.json`.

> **Statut : non testé dans Revit.** Le script compile, et sa logique hors API a été vérifiée avec une API simulée. Lancer d'abord en `dry_run`, puis lire le journal.

## Prérequis

1. Revit 2024 ou plus récent, avec [pyRevit](https://github.com/pyrevitlabs/pyRevit) installé (ou RevitPythonShell).
2. Le dossier `chauffage-albert-camus/` copié sur le poste, avec `model/` et `revit/` côte à côte.
3. Le projet Revit ouvert, contenant :
   - les niveaux `RDC` et `R+1`, sinon le script les crée à 0 et 3,50 m (H-11) ;
   - une **dalle au R+1**, nécessaire pour les réservations ;
   - les **familles chargées** : radiateur vertical, radiateur plinthe, CTA (noms dans `config_revit.json`) ;
   - au moins un type de canalisation et un type de système hydronique aller / retour, qui servent de modèles à dupliquer.

## Réglages (`config_revit.json`)

| Clé | Rôle |
|---|---|
| `dry_run` | `true` : tout est créé puis annulé, seul le journal est écrit. `false` : les créations sont validées |
| `etapes` | Étapes à exécuter, dans l'ordre : niveaux, systemes, types_canalisation, filtres, radiateurs, cta, reservations, reseau, liens_R1 |
| `transformation` | Calage du repère JSON sur le projet : point Revit (m) de l'origine (nu intérieur de la façade ouest × mur nord de la classe élém. 1) et rotation |
| `familles` | Famille et type Revit pour chaque `type_dessine` (V1500x750, PLINTHE, NON_SPECIFIE) et pour les CTA |
| `hauteurs_m` | Altitudes : aller 2,70 m et retour 2,85 m en plafond, raccord radiateur 0,20 m (H-22, à caler sur les coupes) |

## Déroulé

1. Régler `transformation`, en relevant dans Revit les coordonnées de l'origine du repère.
2. Lancer avec `dry_run: true`, puis lire `revit/journal_build.txt` : familles introuvables, diamètres refusés, nœuds non raccordés.
3. Corriger la configuration, puis relancer avec `dry_run: false`.
4. Dans Revit, affecter un **segment** à chaque type de canalisation créé (préférences de routage) : acier NF EN 10255 et cuivre NF EN 1057. Relancer l'étape `reseau` si des diamètres ont été refusés.
5. Reprendre à la main les nœuds signalés dans le journal (croix, tés non alignés), puis vérifier les systèmes : *Analyser > Vérifier les systèmes de canalisations*.

## Ce que fait chaque étape

| Étape | Résultat |
|---|---|
| niveaux | Retrouve ou crée RDC et R+1 |
| systemes | 10 types de systèmes `CH-*-A/R`, abréviation et couleur de la **légende DCE** |
| types_canalisation | `CH_Acier_EN10255` et `CH_Cuivre_EN1057` (duplication) |
| filtres | 10 filtres « CH - … » appliqués à la vue active avec la couleur du circuit |
| radiateurs | 94 radiateurs à leur position, avec Marque = identifiant et Commentaires = local, puissance et statut. Paramètres `CVC_*` renseignés s'ils existent |
| cta | 6 CTA (3 au RDC, cuisine en faux-plafond, 2 en terrasse R+1) |
| reservations | 14 réservations 150 × 80 mm dans la dalle R+1 |
| reseau | Réseau RDC aller et retour superposés en plafond (acier ou cuivre, DN calculé), descentes vers les émetteurs (retour décalé de 10 cm), coudes, tés et manchons aux nœuds |
| liens_R1 | Liaisons cuivre des radiateurs R+1 depuis leur radiateur RDC parent, et colonne CTA vers la terrasse |

## Limites connues

- L'orientation des radiateurs suppose une longueur de famille selon X : le côté pièce est à vérifier.
- Le raccord final sur les connecteurs des familles n'est tenté que si la famille porte des connecteurs hydroniques aller / retour.
- Les liens R+1 sans aplomb (D-28) sont dessinés avec un parcours horizontal provisoire en plafond du RDC, comme indiqué dans le journal.
- Les altitudes et la superposition aller / retour sont des hypothèses de modélisation (H-22).
