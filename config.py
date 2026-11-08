"""
in  : rien
out : charger_env() lit le fichier .env ; get_logger(nom) donne un logger qui ecrit dans logs/<nom>.log
"""

import logging
import os

RACINE = os.path.dirname(os.path.abspath(__file__))


def charger_env() -> None:
    """Lit le fichier .env (lignes CLE=valeur) et remplit os.environ (sans ecraser une variable deja definie)."""
    chemin = os.path.join(RACINE, ".env")
    if not os.path.isfile(chemin):
        return
    with open(chemin, encoding="utf-8") as f:
        for ligne in f:
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#") or "=" not in ligne:
                continue
            cle, valeur = ligne.split("=", 1)
            os.environ.setdefault(cle.strip(), valeur.strip().strip('"').strip("'"))


def get_logger(nom: str) -> logging.Logger:
    """Un logger par module : logs/<nom>.log (tout) + console (avertissements et erreurs)."""
    logger = logging.getLogger(nom)
    if logger.handlers:  # deja configure
        return logger
    logger.setLevel(logging.INFO)
    os.makedirs(os.path.join(RACINE, "logs"), exist_ok=True)
    modele = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s : %(message)s")
    fichier = logging.FileHandler(
        os.path.join(RACINE, "logs", f"{nom}.log"), encoding="utf-8"
    )
    fichier.setFormatter(modele)
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(modele)
    logger.addHandler(fichier)
    logger.addHandler(console)
    return logger


charger_env()
