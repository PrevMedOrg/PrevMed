"""
Paramètres globaux de l'application pour PrevMed.

Fournit un objet de configuration centralisé accessible depuis tous les modules.
Les paramètres sont remplis par les arguments CLI et utilisés dans toute l'application.
"""


class Settings:
    """
    Conteneur de paramètres pour toute l'application.

    Attributs
    ---------
    save_user_data : bool
        Indique s'il faut sauvegarder les données utilisateur de manière permanente
        (logs CSV, données JSON et rapports PDF).
        Si False, seuls des PDF temporaires sont créés pour le téléchargement sans
        enregistrer aucune donnée.
    """

    def __init__(self):
        self.save_user_data: bool = False


# Instance globale des paramètres accessible depuis n'importe quel module
settings = Settings()
