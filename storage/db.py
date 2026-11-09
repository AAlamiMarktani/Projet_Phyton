import os

import psycopg2
from psycopg2.extras import Json, execute_values

from config import get_logger

logger = get_logger("storage")

CREATE = """
CREATE TABLE IF NOT EXISTS ssh_events (
    id         SERIAL PRIMARY KEY,
    date       DATE    NOT NULL,
    time       TIME    NOT NULL,
    ip         TEXT    NOT NULL,
    country    TEXT,
    username   TEXT,
    event      TEXT    NOT NULL,   -- 'invalid_user' | 'wrong_password' | 'success'
    valid_user BOOLEAN NOT NULL,
    count      INT     NOT NULL
)
"""

# infos deja trouvees (pays + tout ce que ipinfo renvoie) : cette table n'est jamais videe,
# une IP n'est donc geolocalisee qu'une seule fois
CREATE_IP = """
CREATE TABLE IF NOT EXISTS ip_countries (
    ip      TEXT PRIMARY KEY,
    country TEXT NOT NULL,
    info    JSONB               -- reponse complete d'ipinfo (pays, continent, asn, ...)
)
"""


def connect():
    try:
        return psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "logs"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
        )
    except psycopg2.Error as e:
        logger.error(f"connexion postgres impossible : {e}")
        raise


def save(conn, records: list[dict]) -> None:
    rows = [
        (
            r["date"],
            r["time"],
            r["ip"],
            "??",
            r["user"],
            r["event"],
            r["valid_user"],
            r["count"],
        )
        for r in records
    ]
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE)
            cur.execute(CREATE_IP)
            cur.execute(
                "CREATE INDEX IF NOT EXISTS ssh_events_ip ON ssh_events (ip)"
            )  # UPDATE par IP plus rapide
            cur.execute("TRUNCATE ssh_events RESTART IDENTITY")
            execute_values(
                cur,
                "INSERT INTO ssh_events (date, time, ip, country, username, event, valid_user, count) VALUES %s",
                rows,
            )
            # les pays deja connus sont remis directement
            cur.execute(
                "UPDATE ssh_events e SET country = c.country FROM ip_countries c WHERE e.ip = c.ip"
            )
        conn.commit()
        logger.info(f"{len(rows)} lignes enregistrees dans ssh_events")
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"enregistrement impossible : {e}")
        raise


def unknown_ips(conn) -> list[str]:
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT ip FROM ssh_events WHERE country = '??' ORDER BY ip"
            )
            return [r[0] for r in cur.fetchall()]
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"lecture des IP sans pays impossible : {e}")
        raise


def set_country(conn, ip: str, country: str, info: dict | None = None) -> None:
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ssh_events SET country = %s WHERE ip = %s", (country, ip)
            )
            if country != "??":
                cur.execute(
                    "INSERT INTO ip_countries (ip, country, info) VALUES (%s, %s, %s) "
                    "ON CONFLICT (ip) DO UPDATE SET country = EXCLUDED.country, info = EXCLUDED.info",
                    (ip, country, Json(info) if info else None),
                )
        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"{ip} : pays non enregistre ({e})")
