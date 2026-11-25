import ipaddress

def analyser_ip_et_reservations(ip_obj: ipaddress.IPv4Address) -> dict:
    """
    Vérifie la classification exacte de l'IP selon les RFC de l'IANA.
    """
    # 1. Broadcast limité (255.255.255.255 - RFC 919 / RFC 1122)
    if ip_obj == ipaddress.IPv4Address("255.255.255.255"):
        return {
            "routable_public": False,
            "type": "Broadcast limité",
            "raison": "Adresse de diffusion limitée à tous les hôtes du réseau local. Non transférée par les routeurs (RFC 919 / RFC 1122)."
        }

    # 2. Adresse non spécifiée / "This host" (0.0.0.0 - RFC 1122)
    if ip_obj == ipaddress.IPv4Address("0.0.0.0"):
        return {
            "routable_public": False,
            "type": "Adresse non spécifiée (0.0.0.0/32)",
            "raison": "Utilisée comme adresse source par un hôte lors de l'obtention d'une IP via DHCP (RFC 1122)."
        }

    # 3. Loopback (127.0.0.0/8)
    if ip_obj.is_loopback:
        return {
            "routable_public": False,
            "type": "Loopback / Boucle locale (127.0.0.0/8)",
            "raison": "Réservé au trafic interne de la machine locale. Les paquets ne quittent jamais l'interface réseau locale."
        }
    
    # 4. APIPA / Link-Local (169.254.0.0/16 - RFC 3927)
    if ip_obj.is_link_local:
        return {
            "routable_public": False,
            "type": "APIPA / Link-Local (169.254.0.0/16 - RFC 3927)",
            "raison": "Adresse d'auto-configuration attribuée automatiquement en l'absence de serveur DHCP. Non routable au-delà du segment local."
        }
    
    # 5. Plages de Documentation (RFC 5737 : TEST-NET-1, TEST-NET-2, TEST-NET-3)
    doc_networks = [
        ipaddress.ip_network("192.0.2.0/24"),    # TEST-NET-1
        ipaddress.ip_network("198.51.100.0/24"), # TEST-NET-2
        ipaddress.ip_network("203.0.113.0/24")  # TEST-NET-3
    ]
    for doc_net in doc_networks:
        if ip_obj in doc_net:
            return {
                "routable_public": False,
                "type": f"Documentation / Test ({doc_net} - RFC 5737)",
                "raison": "Adresse réservée exclusivement aux exemples techniques et à la documentation. Non routable sur Internet public."
            }

    # 6. Multicast (224.0.0.0/4)
    if ip_obj.is_multicast:
        return {
            "routable_public": False,
            "type": "Classe D - Multicast (224.0.0.0/4)",
            "raison": "Destiné à la diffusion simultanée vers un groupe d'hôtes (ex: streaming, protocoles de routage OSPF/RIP). Non routable sur Internet public."
        }
    
    # 7. Carrier-Grade NAT / CGNAT (100.64.0.0/10 - RFC 6598)
    cgnat_network = ipaddress.ip_network("100.64.0.0/10")
    if ip_obj in cgnat_network:
        return {
            "routable_public": False,
            "type": "CGNAT / Shared Address Space (100.64.0.0/10 - RFC 6598)",
            "raison": "Réservé aux fournisseurs d'accès Internet (FAI) pour partager des IPv4 publiques entre plusieurs abonnés. Non routable sur le Web public."
        }
    
    # 8. Adresses privées RFC 1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    if ip_obj.is_private:
        return {
            "routable_public": False,
            "type": "Adresse Privée (RFC 1918)",
            "raison": "Réservé aux réseaux locaux d'entreprise ou domestiques. Les routeurs d'Internet (IP transit) bloquent ces adresses ; un NAT est obligatoire pour sortir."
        }
    
    # 9. IP Publique classique
    if ip_obj.is_global:
        return {
            "routable_public": True,
            "type": "Adresse Publique (Global Unicast)",
            "raison": "Routable directement sur l'Internet public."
        }

    return {
        "routable_public": False,
        "type": "Réservé / Spécial",
        "raison": "Adresse réservée par l'IANA pour des usages spécifiques ou expérimentaux."
    }


def calculer_sous_reseau(ip_str: str, masque_str: str) -> dict:
    """
    Prend une IP et un masque (en CIDR ex: '/24' ou décimal ex: '255.255.255.0')
    et retourne la fiche d'analyse complète.
    """
    # Nettoyage des espaces
    ip_str = ip_str.strip()
    masque_str = masque_str.strip()

    # Détection des champs vides
    if not ip_str:
        return {"erreur": "L'adresse IP ne peut pas être vide."}
    if not masque_str:
        return {"erreur": "Le masque de sous-réseau ne peut pas être vide."}

    # Validation précise du format IPv4 (4 octets)
    octets = ip_str.split('.')
    if len(octets) != 4:
        return {"erreur": "Adresse IP invalide. Une adresse IPv4 doit contenir exactement 4 octets."}

    # Validation préalable de la valeur des octets
    try:
        ip_obj = ipaddress.ip_address(ip_str)
    except ValueError:
        return {"erreur": f"L'adresse IP '{ip_str}' est invalide (les octets doivent être compris entre 0 et 255)."}

    # Validation du masque
    if not masque_str.startswith('/'):
        masque_str_format = f"/{masque_str}"
    else:
        masque_str_format = masque_str

    # Détection si la saisie CIDR contient des caractères non numériques
    valeur_masque = masque_str_format[1:]
    if '/' in masque_str and not valeur_masque.replace('.', '').isdigit():
        return {"erreur": f"Le préfixe CIDR '{masque_str}' est invalide. Il doit être un nombre entier compris entre 0 et 32."}

    # Vérification de la plage si CIDR numérique
    if valeur_masque.isdigit():
        prefix_val = int(valeur_masque)
        if prefix_val < 0 or prefix_val > 32:
            return {"erreur": f"Le préfixe CIDR '{masque_str_format}' est invalide. Il doit être compris entre /0 et /32."}

    ip_reseau_str = f"{ip_str}{masque_str_format}"

    try:
        reseau = ipaddress.ip_network(ip_reseau_str, strict=False)
    except ValueError:
        return {"erreur": f"Le masque décimal '{masque_str}' est invalide. Les bits à 1 du masque doivent être contigus."}

    # Gestion spécifique des plages d'hôtes selon le masque
    prefix = reseau.prefixlen
    if prefix == 31:
        # RFC 3021 Point-to-Point Links
        premiere_ip = str(reseau.network_address)
        derniere_ip = str(reseau.broadcast_address)
        nb_hotes = 2
    elif prefix == 32:
        # Route d'hôte unique (Host Route)
        premiere_ip = str(reseau.network_address)
        derniere_ip = str(reseau.network_address)
        nb_hotes = 1
    else:
        # Sous-réseau standard (/0 à /30)
        premiere_ip = str(reseau.network_address + 1)
        derniere_ip = str(reseau.broadcast_address - 1)
        nb_hotes = reseau.num_addresses - 2

    # Analyse de la routabilité et des réserves
    analyse_secu = analyser_ip_et_reservations(ip_obj)

    type_ip_final = analyse_secu["type"]
    explication_finale = analyse_secu["raison"]

    # Précision spécifique pour le masque /0 (Route par défaut)
    if prefix == 0:
        type_ip_final += " (Préfixe /0 : Route par défaut)"
        explication_finale = "L'IP saisie est publique, mais le préfixe /0 représente la route par défaut (0.0.0.0/0) couvrant la totalité de l'espace IPv4."

    return {
        "ip_saisie": ip_str,
        "masque_decimal": str(reseau.netmask),
        "cidr": f"/{reseau.prefixlen}",
        "adresse_reseau": str(reseau.network_address),
        "adresse_broadcast": str(reseau.broadcast_address),
        "premiere_ip_utile": premiere_ip,
        "derniere_ip_utile": derniere_ip,
        "nombre_hotes_utilisables": nb_hotes,
        "routable_public": "Oui" if analyse_secu["routable_public"] else "Non",
        "type_ip": type_ip_final,
        "explication_routabilite": explication_finale
    }


if __name__ == "__main__":
    print("=== CALCULATEUR IP & SOUS-RÉSEAUX ===")
    ip_saisie = input("Entrez l'adresse IP (ex: 192.168.1.50, 172.16.5.20, 8.8.8.8) : ")
    masque_saisi = input("Entrez le masque (ex: /24 ou 255.255.255.0) : ")
    
    res = calculer_sous_reseau(ip_saisie, masque_saisi)
    
    print("\n---------------- RÉSOLUTIONS ----------------")
    if "erreur" in res:
        print(f"Erreur : {res['erreur']}")
    else:
        print(f"IP saisie             : {res['ip_saisie']}")
        print(f"Masque décimal        : {res['masque_decimal']} (CIDR: {res['cidr']})")
        print(f"Adresse Réseau        : {res['adresse_reseau']}")
        print(f"Adresse Broadcast     : {res['adresse_broadcast']}")
        print(f"Plage d'IP utiles     : {res['premiere_ip_utile']} - {res['derniere_ip_utile']}")
        print(f"Nb hôtes utilisables  : {res['nombre_hotes_utilisables']}")
        print(f"Type d'IP             : {res['type_ip']}")
        print(f"Routable sur Internet : {res['routable_public']}")
        print(f"Explication           : {res['explication_routabilite']}")
    print("--------------------------------------------\n")