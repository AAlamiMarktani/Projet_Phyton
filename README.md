# SSH Logs Analyzer

## Description

Le projet analyse les logs d'authentification SSH d'un serveur du 3 au 30 mai 2026. Il relève les tentatives de connexion, associe un pays à chaque adresse IP et stocke les résultats dans PostgreSQL. Un dashboard présente ensuite les données sous forme de graphiques.

## Organisation

Le traitement est découpé en modules, chacun couvrant une étape :

- `ingestion/read.py` : lit les fichiers logs et écarte les doublons.
- `processing/extract_transform.py` : extrait les informations des lignes SSH et identifie les événements.
- `processing/geolocation.py` : récupère le pays de chaque adresse IP via l'API IPinfo Lite.
- `storage/db.py` : crée et remplit les tables PostgreSQL.
- `serving/queries.py` : regroupe les requêtes SQL des statistiques.
- `serving/charts.py` : produit les graphiques avec Matplotlib.
- `config.py` : centralise la configuration et la journalisation.

Chaque partie se teste et se corrige sans toucher aux autres.

## Résultats

L'analyse relève 14 129 événements SSH et 1 853 adresses IP réparties sur 88 pays. Une seule connexion a réussi, avec l'utilisateur `adminesisa`. L'adresse la plus active, `45.148.10.141`, totalise 835 tentatives.

Le dashboard montre les échecs par pays, les connexions réussies par utilisateur et les tentatives sur des utilisateurs inexistants. Il ajoute des informations sur les IP et les périodes de connexion.

## Gestion des erreurs

Chaque module écrit dans son propre fichier de journalisation sous `logs/`, ce qui permet de suivre son exécution et de localiser l'origine d'un problème. Le terminal n'affiche que les avertissements et les erreurs.
