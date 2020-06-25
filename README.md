# Rolling

A [role game engine](https://redbricks.games/home/rolling-117).

# Development

## Os requires

On debian-like OS, need following debian packages:

    libsqlite3-dev

## Python environment require

A python3.7+ required. To install required packages:

    pip install --upgrade pip setuptools
    python setup.py develop

Then install dev packages:

    pip install -e ".[dev]"

# Roadmap (fr)

Pour participer, rendez-vous sur la page des [briques](https://redbricks.games/home/rolling-117/bricks).

(en cours de rédaction)

* Bases
  * [ ] Création personnage
  * [ ] Mécanisme de caractéristiques et compétences
  * [ ] Génération de carte du monde
  * [ ] Déplacements sur les zones
  * [ ] Ttypes de tuiles (roche, herbe, eau, etc)
  * [ ] Voyage d'une zone à l'autre
  * [ ] Gestion d'objets
  * [ ] Gestion de ressources
  * [ ] Réserve de ressources par zone (renouvellement et consommation)
  * [ ] Mécanisme de base de gestion/fabrication de batiments d'une tuile (mur, feux, etc)
  * [ ] Mécanisme de gestion/fabrication de batiments de plusieurs tuiles (grenier, pont)
  * [ ] Ecran de chat de zone
  * [ ] Ecran de chat de groupes
  * [ ] Ecran de chat d'affinités
  * [ ] Intégration des chats (zone, groupes, etc) sur l'écran de déplacement
  * [ ] Propositions commerciales permanentes
  * [ ] Propositions commerciales uniques
* Actions
  * [ ] Ramasser un objet
  * [ ] Rammasser des resources
  * [ ] Chercher de la nourriture (exploitation des ressources nourriture de la zone)
  * [ ] Mélanger des ressources (eau + terre = terre mouillé)
  * [ ] Exploiter des ressources (bois, pierre, etc)
  * [ ] Construire un objet à partir de ressources, objet
  * [ ] 
* Univers
  * [ ] Décors de base
  * [ ] Caractéristiques et compétences accordés avec gameplay
  * [ ] Choix du design de l'univers pour le serveur "modèle"


    FILL_STUFF = "FILL_STUFF"
    EMPTY_STUFF = "EMPTY_STUFF"
    ATTACK_CHARACTER_WITH = "ATTACK_CHARACTER_WITH"
    DRINK_RESOURCE = "DRINK_RESOURCE"
    DRINK_STUFF = "DRINK_STUFF"
    COLLECT_RESOURCE = "COLLECT_RESOURCE"
    USE_AS_BAG = "USE_AS_BAG"
    NOT_USE_AS_BAG = "NOT_USE_AS_BAG"
    USE_AS_WEAPON = "USE_AS_WEAPON"
    NOT_USE_AS_WEAPON = "NOT_USE_AS_WEAPON"
    USE_AS_SHIELD = "USE_AS_SHIELD"
    NOT_USE_AS_SHIELD = "NOT_USE_AS_SHIELD"
    USE_AS_ARMOR = "USE_AS_ARMOR"
    NOT_USE_AS_ARMOR = "NOT_USE_AS_ARMOR"
    DROP_STUFF = "DROP_STUFF"
    DROP_RESOURCE = "DROP_RESOURCE"
    MIX_RESOURCES = "MIX_RESOURCES"
    EAT_RESOURCE = "EAT_RESOURCE"
    EAT_STUFF = "EAT_STUFF"
    SEARCH_FOOD = "SEARCH_FOOD"
    BEGIN_BUILD = "BEGIN_BUILD"
    BRING_RESOURCE_ON_BUILD = "BRING_RESOURCE_ON_BUILD"
    CONSTRUCT_BUILD = "CONSTRUCT_BUILD"
    BUILD = "BUILD"
    TRANSFORM_STUFF_TO_RESOURCES = "TRANSFORM_STUFF_TO_RESOURCES"
    TRANSFORM_RESOURCES_TO_RESOURCES = "TRANSFORM_RESOURCES_TO_RESOURCES"
    CRAFT_STUFF_WITH_STUFF = "CRAFT_STUFF_WITH_STUFF"
    CRAFT_STUFF_WITH_RESOURCE = "CRAFT_STUFF_WITH_RESOURCE"
    BEGIN_STUFF_CONSTRUCTION = "BEGIN_STUFF_CONSTRUCTION"
    CONTINUE_STUFF_CONSTRUCTION = "CONTINUE_STUFF_CONSTRUCTION"
    SEARCH_MATERIAL = "SEARCH_MATERIAL"
    ATTACK_CHARACTER = "ATTACK_CHARACTER"
    CHEATS = "CHEATS"
    KILL_CHARACTER = "KILL_CHARACTER"
    TAKE_FROM_CHARACTER = "TAKE_FROM_CHARACTER"
    GIVE_TO_CHARACTER = "GIVE_TO_CHARACTER"
