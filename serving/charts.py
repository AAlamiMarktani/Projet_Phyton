import matplotlib.pyplot as plt

from config import get_logger
from serving import queries
from storage import db

logger = get_logger("serving")


def _bar(
    ax,
    rows,
    title,
    xlabel="",
    ylabel="Nombre",
    horizontal=False,
    top=None,
    rotation=None,
    label_rotation=0,
    label_size=7,
):
    if not rows:
        logger.warning(f"{title} : aucune donnee")
        ax.set_title(f"{title} (aucune donnee)")
        return
    total = len(rows)
    if top:
        rows = rows[:top]
        title = f"{title} (top {top} sur {total})"
    else:
        title = f"{title} ({total})"
    labels = ["(vide)" if r[0] in (None, "") else str(r[0]) for r in rows]
    values = [int(r[-1]) for r in rows]
    if horizontal:
        bars = ax.barh(labels[::-1], values[::-1])
        ax.set_xlabel(ylabel)
        ax.tick_params(axis="y", labelsize=8)
        ax.margins(x=0.15)
    else:
        bars = ax.bar(labels, values)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_ylim(0, max(values) * (1.25 if label_rotation else 1.18))
        if rotation is not None:
            ax.tick_params(axis="x", rotation=rotation)
        elif len(rows) > 12:
            ax.tick_params(axis="x", rotation=90)
    ax.bar_label(bars, padding=2, fontsize=label_size, rotation=label_rotation)
    ax.set_title(title)


def show(conn, path: str = "charts.png") -> None:
    fig, axes = plt.subplots(2, 4, figsize=(24, 13), layout="constrained")

    events = queries.by_event(conn)
    _bar(axes[0][0], events, "Evenements (invalid / failed / success)", label_size=9)

    _bar(axes[0][1], queries.by_ip(conn), "IP (tentatives)", horizontal=True, top=25)

    _bar(
        axes[0][2],
        queries.failed_by_country(conn),
        "Tentatives par pays",
        horizontal=True,
        top=25,
    )

    _bar(
        axes[0][3],
        queries.success_by_user(conn),
        "Tentatives reussies par user",
        horizontal=True,
    )

    _bar(
        axes[1][0],
        queries.failed_invalid_user(conn),
        "Echecs avec invalid user",
        horizontal=True,
        top=25,
    )

    rows = queries.by_date(conn)
    if rows:
        dates = [str(r[0]) for r in rows]
        axes[1][1].plot(dates, [int(r[1]) for r in rows], marker="o")
        axes[1][1].set_ylabel("Nombre")
        step = max(1, len(dates) // 10)
        axes[1][1].set_xticks(range(0, len(dates), step))
        axes[1][1].set_xticklabels(dates[::step], rotation=45, ha="right", fontsize=8)
        axes[1][1].grid(alpha=0.3)
    axes[1][1].set_title("Tentatives par date")

    _bar(
        axes[1][2],
        queries.by_hour(conn),
        "Tentatives par heure",
        xlabel="Heure",
        rotation=90,
        label_rotation=90,
        label_size=8,
    )
    axes[1][2].tick_params(axis="x", labelsize=9)

    axes[1][3].axis("off")
    totaux = {str(e): int(n) for e, n in events}
    lignes = [
        "Resume",
        "",
        f"Mots de passe errones : {totaux.get('wrong_password', 0)}",
        f"Utilisateurs invalides : {totaux.get('invalid_user', 0)}",
        f"Connexions reussies : {totaux.get('success', 0)}",
    ]
    axes[1][3].text(
        0.0,
        1.0,
        "\n".join(lignes),
        va="top",
        fontsize=13,
        linespacing=1.8,
        transform=axes[1][3].transAxes,
    )

    try:
        fig.savefig(path, dpi=150)
        logger.info(f"dashboard enregistre dans {path}")
    except OSError as e:
        logger.error(f"{path} : sauvegarde impossible ({e})")
    plt.show()


if __name__ == "__main__":
    conn = db.connect()
    show(conn)
    conn.close()
