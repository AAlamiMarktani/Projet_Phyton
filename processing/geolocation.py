import ipaddress
import os
from functools import lru_cache

import requests

from config import get_logger

logger = get_logger("processing")

if not os.getenv("IPINFO_TOKEN"):
    logger.warning(
        "IPINFO_TOKEN absent (fichier .env) : les pays ne seront pas trouves"
    )


@lru_cache(maxsize=None)
def geolocation(ip: str) -> dict | None:
    headers = {"Authorization": f"Bearer {os.getenv('IPINFO_TOKEN')}"}
    try:
        response = requests.get(
            f"https://api.ipinfo.io/lite/{ip}", headers=headers, timeout=5
        )
    except requests.RequestException as e:
        logger.error(f"{ip} : requete impossible ({e})")
        return None
    if response.status_code != 200:
        logger.error(f"{ip} : ipinfo a repondu HTTP {response.status_code}")
        return None
    return response.json()


def country(ip: str) -> str:
    try:
        adresse = ipaddress.ip_address(ip)
    except ValueError:
        logger.error(f"adresse IP invalide : {ip}")
        return "??"
    if adresse.is_private or adresse.is_loopback:
        return "local"
    info = geolocation(ip)
    if not info:
        return "??"
    if "country_code" not in info:
        logger.warning(f"{ip} : pas de pays dans la reponse ipinfo")
        return "??"
    return info["country_code"]


if __name__ == "__main__":
    print(geolocation("88.147.152.239"))
    print(country("88.147.152.239"))
