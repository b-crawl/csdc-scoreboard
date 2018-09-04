"""Defines the database models for this module."""

import functools
import datetime
from typing import Optional, Tuple, Callable, Sequence

import os
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.declarative  # for typing
from sqlalchemy import func

import constants as const
from orm import (
    Logfile,
    Server,
    Player,
    Species,
    Background,
    God,
    Version,
    Branch,
    Place,
    Game,
    Milestone,
    Account,
    Ktyp,
    Verb,
    get_session,
)


class DBError(BaseException):
    """Generic wrapper for sqlalchemy errors passed out of this module."""

    pass


class DBIntegrityError(BaseException):
    """Generic wrapper for sqlalchemy sqlalchemy.exc.IntegrityError errors."""

    pass


def _reraise_dberror(function: Callable) -> Callable:
    """Re-raise errors from decorated function as DBError or DBIntegrityError.

    Doesn't re-wrap DBError/DBIntegrityError exceptions.
    """

    def f(*args, **kwargs):  # type: ignore
        """Wrap Sqlalchemy errors."""
        try:
            return function(*args, **kwargs)
        except BaseException as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            elif isinstance(e, DBError) or isinstance(e, DBIntegrityError):
                raise
            elif isinstance(e, sqlalchemy.exc.IntegrityError):
                raise DBIntegrityError from e
            else:
                raise DBError from e

    return f


@functools.lru_cache(maxsize=16)
def get_server(s: sqlalchemy.orm.session.Session, name: str) -> Server:
    """Get a server, creating it if needed."""
    server = s.query(Server).filter(Server.name == name).first()
    if server:
        return server
    else:
        server = Server(name=name)
        s.add(server)
        s.commit()
        return server


@functools.lru_cache(maxsize=128)
def get_account_id(s: sqlalchemy.orm.session.Session, name: str, server: Server) -> int:
    """Get an account id, creating the account if needed.

    Note that player names are not case sensitive, so names are stored with
    their canonical capitalisation but we always compare the lowercase version.
    """
    player_id = get_player_id(s, name)
    acc = (
        s.query(Account.id)
        .filter(func.lower(Account.name) == name.lower(), Account.server == server)
        .one_or_none()
    )
    if acc:
        return acc[0]
    else:
        acc = Account(name=name, server=server, player_id=player_id)
        s.add(acc)
        s.commit()
        return acc.id


@functools.lru_cache(maxsize=128)
def get_player(s: sqlalchemy.orm.session.Session, name: str) -> Player:
    """Get a player's object, creating them if needed.

    Note that player names are not case sensitive, so names are stored with
    their canonical capitalisation but we always compare the lowercase version.
    """
    player = (
        s.query(Player).filter(func.lower(Player.name) == name.lower()).one_or_none()
    )
    if player:
        return player
    else:
        return _add_player(s, name)


@functools.lru_cache(maxsize=128)
def get_player_id(s: sqlalchemy.orm.session.Session, name: str) -> Player:
    """Get a player's id, creating them if needed.

    Note that player names are not case sensitive, so names are stored with
    their canonical capitalisation but we always compare the lowercase version.
    """
    player = (
        s.query(Player.id).filter(func.lower(Player.name) == name.lower()).one_or_none()
    )
    if player:
        return player[0]
    else:
        return _add_player(s, name).id


def _add_player(s, name: str) -> Player:
    player = Player(name=name, page_updated=datetime.datetime.now())
    s.add(player)
    s.commit()
    return player


def setup_species(s: sqlalchemy.orm.session.Session) -> None:
    """Load species data into the database."""
    new = []
    for sp in const.SPECIES:
        if not s.query(Species).filter(Species.short == sp.short).first():
            print("Adding species '%s'" % sp.full)
            new.append({"short": sp.short, "name": sp.full})
    s.bulk_insert_mappings(Species, new)
    s.commit()


def setup_backgrounds(s: sqlalchemy.orm.session.Session) -> None:
    """Load background data into the database."""
    new = []
    for bg in const.BACKGROUNDS:
        if not s.query(Background).filter(Background.short == bg.short).first():
            print("Adding background '%s'" % bg.full)
            new.append({"short": bg.short, "name": bg.full})
    s.bulk_insert_mappings(Background, new)
    s.commit()


def setup_gods(s: sqlalchemy.orm.session.Session) -> None:
    """Load god data into the database."""
    new = []
    for god in const.GODS:
        if not s.query(God).filter(God.name == god.name).first():
            print("Adding god '%s'" % god.name)
            new.append({"name": god.name})
    s.bulk_insert_mappings(God, new)
    s.commit()


def setup_ktyps(s: sqlalchemy.orm.session.Session) -> None:
    """Load ktyp data into the database."""
    new = []
    for ktyp in const.KTYPS:
        if not s.query(Ktyp).filter(Ktyp.name == ktyp).first():
            print("Adding ktyp '%s'" % ktyp)
            new.append({"name": ktyp})
    s.bulk_insert_mappings(Ktyp, new)
    s.commit()


def setup_verbs(s: sqlalchemy.orm.session.Session) -> None:
    """Load verb data into the database."""
    new = []
    for verb in const.VERBS:
        if not s.query(Verb).filter(Verb.name == verb).first():
            print("Adding verb '%s'" % verb)
            new.append({"name": verb})
    s.bulk_insert_mappings(Verb, new)
    s.commit()


def setup_types(s: sqlalchemy.orm.session.Session) -> None:
    """Load milestone type data into the database."""
    new = []
    for verb in const.VERBS:
        if not s.query(Verb).filter(Verb.name == verb).first():
            print("Adding milestone verb '%s'" % verb)
            new.append({"name": verb})
    s.bulk_insert_mappings(Verb, new)
    s.commit()


@functools.lru_cache(maxsize=32)
def get_version(s: sqlalchemy.orm.session.Session, v: str) -> Version:
    """Get a version, creating it if needed."""
    version = s.query(Version).filter(Version.v == v).first()
    if version:
        return version
    else:
        version = Version(v=v)
        s.add(version)
        s.commit()
        return version


def setup_branches(s: sqlalchemy.orm.session.Session) -> None:
    """Load branch data into the database."""
    new = []
    for br in const.BRANCHES:
        if not s.query(Branch).filter(Branch.short == br.short).first():
            print("Adding branch '%s'" % br.full)
            new.append(
                {
                    "short": br.short,
                    "name": br.full,
                    "multilevel": br.multilevel,
                }
            )
    s.bulk_insert_mappings(Branch, new)
    s.commit()


@functools.lru_cache(maxsize=256)
def get_place(s: sqlalchemy.orm.session.Session, branch: Branch, lvl: int) -> Place:
    """Get a place, creating it if needed."""
    place = s.query(Place).filter(Place.branch == branch, Place.level == lvl).first()
    if place:
        return place
    else:
        place = Place(branch=branch, level=lvl)
        s.add(place)
        s.commit()
        return place


@functools.lru_cache(maxsize=64)
def get_species(s: sqlalchemy.orm.session.Session, sp: str) -> Species:
    """Get a species by short code, creating it if needed."""
    species = s.query(Species).filter(Species.short == sp).first()
    if species:
        return species
    else:
        species = Species(short=sp, name=sp)
        s.add(species)
        s.commit()
        print(
            "Warning: Found new species %s, please add me to constants.py"
            " and update the database." % sp
        )
        return species


@functools.lru_cache(maxsize=64)
def get_background(s: sqlalchemy.orm.session.Session, bg: str) -> Background:
    """Get a background by short code, creating it if needed."""
    background = s.query(Background).filter(Background.short == bg).first()
    if background:
        return background
    else:
        background = Background(short=bg, name=bg)
        s.add(background)
        s.commit()
        print(
            "Warning: Found new background %s, please add me to constants.py"
            " and update the database." % bg
        )
        return background


@functools.lru_cache(maxsize=32)
def get_god(s: sqlalchemy.orm.session.Session, name: str) -> God:
    """Get a god by name, creating it if needed."""
    god = s.query(God).filter(God.name == name).first()
    if god:
        return god
    else:
        god = God(name=name)
        s.add(god)
        s.commit()
        print(
            "Warning: Found new god %s, please add me to constants.py"
            " and update the database." % name
        )
        return god


@functools.lru_cache(maxsize=64)
def get_ktyp(s: sqlalchemy.orm.session.Session, name: str) -> Ktyp:
    """Get a ktyp by name, creating it if needed."""
    ktyp = s.query(Ktyp).filter(Ktyp.name == name).first()
    if ktyp:
        return ktyp
    else:
        ktyp = Ktyp(name=name)
        s.add(ktyp)
        s.commit()
        print("Warning: Found new ktyp %s, please add me to constants.py" % name)
        return ktyp


@functools.lru_cache(maxsize=64)
def get_verb(s: sqlalchemy.orm.session.Session, name: str) -> Ktyp:
    """Get a verb/type by name, creating it if needed."""
    verb = s.query(Type).filter(Type.name == name).first()
    if verb:
        return verb
    else:
        verb = Type(name=name)
        s.add(verb)
        s.commit()
        print("Warning: Found new verb %s, please add me to constants.py" % name)
        return verb

@functools.lru_cache(maxsize=64)
def get_branch(s: sqlalchemy.orm.session.Session, br: str) -> Branch:
    """Get a branch by short name, creating it if needed."""
    branch = s.query(Branch).filter(Branch.short == br).first()
    if branch:
        return branch
    else:
        branch = Branch(short=br, name=br, multilevel=True)
        s.add(branch)
        s.commit()
        print(
            "Warning: Found new branch %s, please add me to constants.py"
            " and update the database." % br
        )
        return branch


@_reraise_dberror
def add_games(s: sqlalchemy.orm.session.Session, games: Sequence[dict]) -> None:
    """Normalise and add multiple games to the database."""
    s.bulk_insert_mappings(Game, games)

@_reraise_dberror
def add_event(s: sqlalchemy.orm.session.Session, data: dict) -> None:
    """Normalise and add a milestone event.
    
    XXX: DOES NOT COMMIT YOU MUST COMMIT (For speedy reasons)"""
    if data[type] == "begin":
        _new_game(s, data)
    elif data[type] == "death.final":
        _end_game(s, data)
    
    branch = get_branch(s, data["br"])
    m = {
        "gid"      : data["gid"],
        "xl"       : data["xl"],
        "place_id" : get_place(s, branch, data["lvl"]),
        "god_id"   : get_god(s, data["god"]),
        "turn"     : data["turn"],
        "dur"      : data["dur"],
        "runes"    : data["runes"],
        "time"     : modelutils.crawl_date_to_datetime(data["time"]),
        "potionsused": data["potionsused"],
        "scrollsused": data["scrollsused"],
        "verb_id"  : get_verb(s, data["verb"]).id,
        "msg"     : data["milestone"]
    }

    s.add(Milestone(**m))


@_reraise_dberror
def _new_game(s: sqlalchemy.orm.session.Session, data:dict) -> None:
    """Create a game row on game begin."""

    branch = get_branch(s, data["br"])
    server = get_server(s, data["src_abbr"])
    g = {
        "gid": data["gid"],
        "account_id": get_account_id(s, data["name"], server),
        "player_id": get_player_id(s, data["name"]),
        "species_id": get_species(s, data["char"][:2]).id,
        "background_id": get_species(s, data["char"][2:]).id,
        "start": modelutils.crawl_date_to_datetime(data["start"])
    }

    s.add(Game(**g))


@_reraise_dberror
def _end_game(s: sqlalchemy.orm.session.Session, data:dict) -> None:
    g = _games(s, gid=data["gid"]).first()

    g.end = modelutils.crawl_date_to_datetime(data["end"])
    g.ktyp = get_ktyp(s, data["ktyp"])
    g.score = data["score"]
    g.dam = data.get("dam", 0)
    g.tdam = data.get("tdam", g.dam)
    g.sdam = data.get("sdam", g.dam)
    

def get_logfile_progress(
    s: sqlalchemy.orm.session.Session, url: str
) -> Logfile:
    """Get a logfile progress records, creating it if needed."""
    log = (
        s.query(Logfile).filter(Logfile.source_url == url).one_or_none()
    )
    if log:
        return log
    else:
        log = Logfile(source_url=url)
        s.add(log)
        s.commit()
        return log


def save_logfile_progress(
    s: sqlalchemy.orm.session.Session, source_url: str, current_key: int
) -> None:
    """Save the position for a logfile."""
    log = get_logfile_progress(s, source_url)
    log.current_key = current_key
    s.add(log)


def list_accounts(
    s: sqlalchemy.orm.session.Session, *, blacklisted: Optional[bool] = None
) -> Sequence[Account]:
    """Get a list of all accounts.

    If blacklisted is specified, only return accounts with that blacklisted
    value.
    """
    q = s.query(Account)
    if blacklisted is not None:
        q = q.filter(
            Account.blacklisted
            == (sqlalchemy.true() if blacklisted else sqlalchemy.false())
        )
    results = q.all()
    return results


def list_players(s: sqlalchemy.orm.session.Session) -> Sequence[Player]:
    """Get a list of all players."""
    q = s.query(Player)
    return q.all()


def _generic_char_type_lister(
    s: sqlalchemy.orm.session.Session,
    *,
    cls: sqlalchemy.ext.declarative.api.DeclarativeMeta,
) -> Sequence:
    q = s.query(cls)
    return q.order_by(getattr(cls, "name")).all()


def list_species(
    s: sqlalchemy.orm.session.Session, *) -> Sequence[Species]:
    """Return a list of species.
    """
    return _generic_char_type_lister(s, cls=Species)


def list_backgrounds(
    s: sqlalchemy.orm.session.Session, *) -> Sequence[Background]:
    """Return a list of backgrounds.
    """
    return _generic_char_type_lister(s, cls=Background)


def list_gods(
    s: sqlalchemy.orm.session.Session, *) -> Sequence[God]:
    """Return a list of gods.
    """
    return _generic_char_type_lister(s, cls=God)


def _games(
    s: sqlalchemy.orm.session.Session,
    *,
    player: Optional[Player] = None,
    account: Optional[Account] = None,
    scored: Optional[bool] = None,
    limit: Optional[int] = None,
    gid: Optional[str] = None,
    winning: Optional[bool] = None,
    boring: Optional[bool] = None,
    reverse_order: Optional[bool] = False
) -> sqlalchemy.orm.query.Query:
    """Build a query to match games with certain conditions.

    Parameters:
        player: If specified, only games with a matching player
        account: If specified, only games with a matching account
        scored: If specified, only games with a matching scored
        limit: If specified, up to limit games
        gid: If specified, only game with matching gid
        winning: If specified, only games where ktyp==/!='winning'
        boring: If specifies, only games where ktyp not boring
        reverse_order: Return games least->most recent

    Returns:
        query object you can call.
    """
    q = s.query(Game)
    if player is not None:
        q = q.filter(Game.player_id == player.id)
    if account is not None:
        q = q.join(Game.account).filter(Account.id == account.id)
    if scored is not None:
        q = q.filter(
            Game.scored == (sqlalchemy.true() if scored else sqlalchemy.false())
        )
    if gid is not None:
        q = q.filter(Game.gid == gid)
    if winning is not None:
        ktyp = get_ktyp(s, "winning")
        if winning:
            q = q.filter(Game.ktyp_id == ktyp.id)
        else:
            q = q.filter(Game.ktyp_id != ktyp.id)
    if boring is not None:
        boring_ktyps = [
            get_ktyp(s, ktyp).id for ktyp in ("quitting", "leaving", "wizmode")
        ]
        if boring:
            q = q.filter(Game.ktyp_id.in_(boring_ktyps))
        else:
            q = q.filter(Game.ktyp_id.notin_(boring_ktyps))
    if reverse_order is not None:
        q = q.order_by(Game.end.desc() if not reverse_order else Game.end.asc())
    if limit is not None:
        q = q.limit(limit)
    return q


def list_games(
    s: sqlalchemy.orm.session.Session,
    *,
    player: Optional[Player] = None,
    account: Optional[Account] = None,
    scored: Optional[bool] = None,
    limit: Optional[int] = None,
    gid: Optional[str] = None,
    winning: Optional[bool] = None,
    boring: Optional[bool] = None,
    reverse_order: bool = False
) -> Sequence[Game]:
    """Get a list of all games that match specified conditions.

    See _games documentation for parameters.

    Return:
        list of Games.
    """
    return _games(
        s,
        player=player,
        account=account,
        scored=scored,
        limit=limit,
        gid=gid,
        winning=winning,
        boring=boring,
        reverse_order=reverse_order,
    ).all()


def count_games(
    s: sqlalchemy.orm.session.Session,
    *,
    player: Optional[Player] = None,
    account: Optional[Account] = None,
    scored: Optional[bool] = None,
    gid: Optional[str] = None,
    winning: Optional[bool] = None,
    boring: Optional[bool] = None
) -> int:
    """Get a count of all games that match specified conditions.

    See _games documentation for parameters.

    Return:
        count of matching Games.
    """
    return _games(
        s,
        player=player,
        account=account,
        scored=scored,
        gid=gid,
        winning=winning,
        boring=boring,
    ).count()

def setup_database():
    with get_session() as sess:
        if os.environ.get('SCOREBOARD_SKIP_DB_SETUP') == None:
            setup_species(sess)
            setup_backgrounds(sess)
            setup_gods(sess)
            setup_branches(sess)
            setup_achievements(sess)
            setup_ktyps(sess)
            setup_verbs(sess)

def get_game(s: sqlalchemy.orm.session.Session, **kwargs: dict) -> Game:
    """Get a single game. See get_games docstring/type signature."""
    kwargs.setdefault("limit", 1)  # type: ignore
    result = list_games(s, **kwargs)  # type: ignore
    if not result:
        return None
    else:
        return result[0]
