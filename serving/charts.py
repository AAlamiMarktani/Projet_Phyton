"""
in  : connexion postgres
out : dashboard matplotlib (affiche + sauvegarde dans charts.png)
"""

import matplotlib.pyplot as plt

from config import get_logger
from serving import queries
from storage import db

logger = get_logger("serving")


def _bar(ax, rows, title, xlabel="", ylabel="Nombre", horizontal=False, top=None):
    if not rows:
        logger.warning(f"{title} : aucune donnee")
        ax.set_title(f"{title} (aucune donnee)")
        return
    total = len(rows)
    if top:  # trop d'elements pour afficher tous les noms : on garde les plus grands
        rows = rows[:top]
        title = f"{title} (top {top} sur {total})"
    else:
        title = f"{title} ({total})"
    labels = ["(vide)" if r[0] in (None, "") else str(r[0]) for r in rows]
    values = [int(r[-1]) for r in rows]  # le nombre est toujours la derniere colonne
    if horizontal:
        bars = ax.barh(labels[::-1], values[::-1])  # le plus grand en haut
        ax.set_xlabel(ylabel)
        ax.tick_params(axis="y", labelsize=8)
    else:
        bars = ax.bar(labels, values)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        if len(rows) > 12:
            ax.tick_params(axis="x", rotation=90)
    ax.bar_label(bars, padding=2, fontsize=7)  # le nombre au bout de chaque barre
    ax.set_title(title)


def show(conn, path: str = "charts.png") -> None:
    fig, axes = plt.subplots(2, 4, figsize=(24, 11))

    # invalid user / failed password / success
    _bar(axes[0][0], queries.by_event(conn), "Evenements (invalid / failed / success)")

    # how many times same ip
    _bar(axes[0][1], queries.by_ip(conn), "IP (tentatives)", horizontal=True, top=25)

    # dashboard : nombre de tentatives echouees par pays
    _bar(
        axes[0][2],
        queries.failed_by_country(conn),
        "Tentatives echouees par pays",
        xlabel="Pays",
        top=30,
    )

    # dashboard : nombre de tentatives reussies par user
    _bar(
        axes[0][3],
        queries.success_by_user(conn),
        "Tentatives reussies par user",
        xlabel="User",
    )

    # dashboard : tentatives echouees avec invalid user
    _bar(
        axes[1][0],
        queries.failed_invalid_user(conn),
        "Echecs avec invalid user",
        horizontal=True,
        top=25,
    )

    # date
    rows = queries.by_date(conn)
    if rows:
        axes[1][1].plot([r[0] for r in rows], [int(r[1]) for r in rows], marker="o")
        axes[1][1].set_ylabel("Nombre")
        axes[1][1].tick_params(axis="x", rotation=45)
    axes[1][1].set_title("Tentatives par date")

    # time
    _bar(axes[1][2], queries.by_hour(conn), "Tentatives par heure", xlabel="Heure")

    axes[1][3].axis("off")  # case libre

    fig.tight_layout()
    try:
        fig.savefig(path)
        logger.info(f"dashboard enregistre dans {path}")
    except OSError as e:
        logger.error(f"{path} : sauvegarde impossible ({e})")
    plt.show()


if __name__ == "__main__":
    conn = db.connect()
    show(conn)
    conn.close()
