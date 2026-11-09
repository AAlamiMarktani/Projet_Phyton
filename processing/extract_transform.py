import re
from collections import Counter
from datetime import datetime

from config import get_logger

logger = get_logger("processing")


DEFAULT_YEAR = 2026

HEADER = re.compile(
    r"^(?P<month>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<process>[\w\-/]+)(?:\[(?P<pid>\d+)\])?:\s+(?P<message>.*)$"
)

INVALID_USER = re.compile(r"Invalid user (?P<user>.*?) from (?P<ip>\S+) port \d+")

FAILED_PASSWORD = re.compile(
    r"(?:message repeated (?P<n>\d+) times: \[ )?"
    r"Failed password for (?P<invalid>invalid user )?(?P<user>.*?) from (?P<ip>\S+) port \d+"
)

ACCEPTED = re.compile(
    r"Accepted (?P<method>password|publickey) for (?P<user>\S+) from (?P<ip>\S+) port \d+"
)


def extract(row: str, year: int = DEFAULT_YEAR) -> dict | None:
    head = HEADER.match(row)
    if not head or head["process"] != "sshd":
        return None
    msg = head["message"]

    if m := INVALID_USER.search(msg):
        event, valid, count = "invalid_user", False, 1
    elif m := FAILED_PASSWORD.search(msg):
        # mot de passe errone ; l'utilisateur existe sauf si "invalid user"
        event, valid = "wrong_password", m["invalid"] is None
        count = int(m["n"]) if m["n"] else 1
    elif m := ACCEPTED.search(msg):
        event, valid, count = "success", True, 1
    else:
        return None

    try:
        dt = datetime.strptime(
            f"{year} {head['month']} {head['day']} {head['time']}", "%Y %b %d %H:%M:%S"
        )
    except ValueError as e:
        logger.error(f"date invalide, ligne ignoree ({e}) : {row[:80]}")
        return None
    return {
        "date": dt.date().isoformat(),
        "time": dt.time().isoformat(),
        "ip": m["ip"],
        "user": m["user"],
        "event": event,
        "valid_user": valid,
        "count": count,
    }


def extract_all(rows: list[str], year: int = DEFAULT_YEAR) -> list[dict]:
    records = [r for row in rows if (r := extract(row, year))]
    logger.info(f"{len(records)} evenements ssh retenus sur {len(rows)} lignes")
    return records


def summarize(records: list[dict]) -> dict:
    s = {
        "valid_user": 0,
        "invalid_user": 0,
        "wrong_password": 0,
        "wrong_password_valid_user": 0,
        "success": 0,
        "by_ip": Counter(),
        "invalid_users": Counter(),
    }
    for r in records:
        n = r["count"]
        if r["event"] == "invalid_user":
            s["invalid_user"] += n
            s["invalid_users"][r["user"]] += n
            continue
        # wrong_password ou success = vraie tentative d'authentification
        s["by_ip"][r["ip"]] += n
        if r["event"] == "wrong_password":
            s["wrong_password"] += n
            if r["valid_user"]:
                s["wrong_password_valid_user"] += n
                s["valid_user"] += n
        else:
            s["success"] += 1 * n
            s["valid_user"] += n
    return s
