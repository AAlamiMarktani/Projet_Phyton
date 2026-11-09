import psycopg2

from config import get_logger

logger = get_logger("serving")


def _fetch(conn, sql: str, params=None) -> list[tuple]:
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"requete en echec : {e}")
        return []


def by_event(conn) -> list[tuple]:
    return _fetch(
        conn,
        """
        SELECT event, SUM(count) AS n
        FROM ssh_events
        GROUP BY event
        ORDER BY n DESC
        """,
    )


def by_ip(conn, limit: int | None = None) -> list[tuple]:
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
    return _fetch(
        conn,
        """
        SELECT country, SUM(count) AS n
        FROM ssh_events
        GROUP BY country
        ORDER BY n DESC
        LIMIT %s
        """,
        (limit,),
    )


def success_by_user(conn, limit: int | None = None) -> list[tuple]:
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
