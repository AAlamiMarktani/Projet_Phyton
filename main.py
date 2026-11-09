import time

from config import get_logger
from ingestion import read
from processing import extract_transform, geolocation
from storage import db
from serving import queries, charts

logger = get_logger("main")


def geolocaliser(conn, ips: list[str]) -> list[str]:
    inconnues = []
    for i, ip in enumerate(ips, 1):
        country = geolocation.country(ip)
        info = geolocation.geolocation(ip) if country not in ("local", "??") else None
        db.set_country(conn, ip, country, info)
        if country == "??":
            inconnues.append(ip)
        if i % 100 == 0:
            print(f"  {i}/{len(ips)} IP geolocalisees")
    return inconnues


if __name__ == "__main__":
    try:
        rows = read.ingest("./data/auth")
        if rows:
            records = extract_transform.extract_all(rows)
            s = extract_transform.summarize(records)

            print(f"{len(rows)} lignes lues, {len(records)} evenements ssh retenus\n")
            print(f"Utilisateurs valides   : {s['valid_user']}")
            print(f"Utilisateurs invalides : {s['invalid_user']}")
            print(
                f"Mots de passe errones  : {s['wrong_password']} "
                f"(dont {s['wrong_password_valid_user']} sur un utilisateur valide)"
            )
            print(f"Connexions reussies    : {s['success']}\n")

            conn = db.connect()
            db.save(conn, records)
            ips = db.unknown_ips(conn)
            print(f"Postgres : lignes enregistrees, {len(ips)} IP a geolocaliser...")

            inconnues = geolocaliser(conn, ips)
            for tour in range(1, 4):
                if not inconnues:
                    break
                print(f"  tour {tour} : {len(inconnues)} IP sans pays")
                geolocation.geolocation.cache_clear()
                time.sleep(5)
                inconnues = geolocaliser(conn, inconnues)
            if inconnues:
                logger.warning(f"{len(inconnues)} IP toujours sans pays")
            print(f"  IP toujours sans pays : {len(inconnues)}\n")

            print("\nPar evenement (postgres) :")
            for event, n in queries.by_event(conn):
                print(f"  {event:<18} {n:>6}")

            print("\nIP (postgres) :")
            for ip, country, n in queries.by_ip(conn):
                print(f"  {ip:<18} {n:>6}  {country}")

            print("\nUtilisateurs et pays (postgres) :")
            for user, valid, country, n in queries.by_user_country(conn):
                print(
                    f"  {user or '(vide)':<18} {'valide' if valid else 'invalide':<9} {country:<6} {n:>6}"
                )
            charts.show(conn)
            conn.close()
        else:
            logger.error("aucune ligne lue : verifier le dossier ./data/auth")
    except Exception:
        logger.exception("erreur fatale dans le pipeline")
        raise
