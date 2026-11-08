"""
in  : connexion postgres
out : resultats des requetes sur ssh_events
"""

import psycopg2

from config import get_logger

logger = get_logger("serving")


def _fetch(conn, sql: str, params=None) -> list[tuple]:
    """Execute une requete ; en cas d'erreur : log + liste vide (le dashboard continue)."""
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"requete en echec : {e}")
        return []


def by_event(conn) -> list[tuple]:
    """invalid user / failed password / success : combien de fois."""
    return _fetch(
        conn, "SELECT event, SUM(count) FROM ssh_events GROUP BY event ORDER BY 2 DESC"
    )


def by_ip(conn, limit: int | None = None) -> list[tuple]:
    """Combien de fois la meme IP a tente de s'authentifier (+ pays)."""
    return _fetch(
        conn,
        """
        SELECT ip, country, SUM(count) AS n
        FROM ssh_events
        WHERE event IN ('wrong_password', 'success')
        GROUP BY ip, country
        ORDER BY n DESC
        LIMIT %s
        """,
        (limit,),
    )


def failed_by_country(conn, limit: int | None = None) -> list[tuple]:
    """Dashboard : nombre de tentatives echouees par pays."""
    return _fetch(
        conn,
        """
        SELECT country, SUM(count) AS n
        FROM ssh_events
        WHERE event = 'wrong_password'
        GROUP BY country
        ORDER BY n DESC
        LIMIT %s
        """,
        (limit,),
    )


def success_by_user(conn, limit: int | None = None) -> list[tuple]:
    """Dashboard : nombre de tentatives reussies par utilisateur."""
    return _fetch(
        conn,
        """
        SELECT username, SUM(count) AS n
        FROM ssh_events
        WHERE event = 'success'
        GROUP BY username
        ORDER BY n DESC
        LIMIT %s
        """,
        (limit,),
    )


def failed_invalid_user(conn, limit: int | None = None) -> list[tuple]:
    """Dashboard : tentatives echouees avec un utilisateur invalide (par nom d'utilisateur)."""
    return _fetch(
        conn,
        """
        SELECT username, SUM(count) AS n
        FROM ssh_events
        WHERE event = 'wrong_password' AND NOT valid_user
        GROUP BY username
        ORDER BY n DESC
        LIMIT %s
        """,
        (limit,),
    )


def by_date(conn) -> list[tuple]:
    """Combien de tentatives par jour."""
    return _fetch(
        conn,
        """
        SELECT date, SUM(count)
        FROM ssh_events
        WHERE event IN ('wrong_password', 'success')
        GROUP BY date
        ORDER BY date
        """,
    )


def by_hour(conn) -> list[tuple]:
    """Combien de tentatives par heure (0-23)."""
    return _fetch(
        conn,
        """
        SELECT EXTRACT(HOUR FROM time)::int AS hour, SUM(count)
        FROM ssh_events
        WHERE event IN ('wrong_password', 'success')
        GROUP BY hour
        ORDER BY hour
        """,
    )


def by_user_country(conn) -> list[tuple]:
    """Pour chaque utilisateur : son pays (celui de l'IP) et son nombre de tentatives."""
    return _fetch(
        conn,
        """
        SELECT username, valid_user, country, SUM(count) AS n
        FROM ssh_events
        WHERE event = 'invalid_user'
           OR (valid_user AND event IN ('wrong_password', 'success'))
        GROUP BY username, valid_user, country
        ORDER BY n DESC
        """,
    )
