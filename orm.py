from calendar import timegm

import sqlalchemy
from sqlalchemy import (
    Table,
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import enum
import json

from . import model

SQLALCHEMY_DATABASE_URI = "sqlite:///crawl.db"

Base = declarative_base()

@characteristic.with_repr(["name"])  # pylint: disable=too-few-public-methods
class Server(Base):
    """A DCSS server -- a source of logfiles/milestones.

    Columns:
        name: Server's short name (eg CAO, CPO).
    """

    __tablename__ = "servers"
    id = Column(Integer, primary_key=True, nullable=False)  # type: int
    name = Column(String(4), nullable=False, index=True, unique=True)  # type: str

@characteristic.with_repr(["name", "server"])  # pylint: disable=too-few-public-methods
class Account(Base):
    """An account -- a single username on a single server.

    Columns:
        name: name of the account on the server
        blacklisted: if the account has been blacklisted. Accounts started as
            streak griefers/etc are blacklisted.
    """

    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, nullable=False)  # type: int
    name = Column(String(20), nullable=False, index=True)  # type: str
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)  # type: int
    server = relationship("Server")
    blacklisted = Column(Boolean, nullable=False, default=False)  # type: bool
    player_id = Column(
        Integer, ForeignKey("players.id"), nullable=False, index=True
    )  # type: int
    player = relationship("Player", back_populates="accounts")

    @property
    def canonical_name(self) -> str:
        """Canonical name.

        Crawl names are case-insensitive, we preserve the account's
        preferred capitalisation, but store them uniquely using the canonical
        name.
        """
        return self.name.lower()

    __table_args__ = (UniqueConstraint("name", "server_id", name="name-server_id"),)

@characteristic.with_repr(["name"])  # pylint: disable=too-few-public-methods
class Player(Base):
    """A player -- a collection of accounts with shared metadata.

    Columns:
        name: Player's name. For now, this is the same as the accounts that
            make up the player. In future, it could be changed so that
            differently-named accounts can make up a single player (eg
            Sequell nick mapping).
    """

    __tablename__ = "players"
    id = Column(Integer, primary_key=True, nullable=False)  # type: int
    name = Column(String(20), unique=True, nullable=False)  # type: str
    page_updated = Column(DateTime, nullable=False, index=True)  # type: DateTime
    accounts = relationship("Account", back_populates="player")  # type: list

    @property
    def url_name(self):
        return self.name.lower()

@characteristic.with_repr(["short"])  # pylint: disable=too-few-public-methods
class Species(Base):
    """A DCSS player species.

    Columns:
        short: short species name, eg 'HO', 'Mi'.
        name: long species name, eg 'Hill Orc', 'Minotaur'.
        playable: if the species is playable in the current version.
            Not quite sure what to do in the case of a mismatch between stable
            and trunk...
    """

    __tablename__ = "species"
    id = Column(Integer, primary_key=True, nullable=False)  # type: int
    short = Column(String(2), nullable=False, index=True, unique=True)  # type: str
    name = Column(String(15), nullable=False, unique=True)  # type: str


@characteristic.with_repr(["short"])  # pylint: disable=too-few-public-methods
class Background(Base):
    """A DCSS player background.

    Columns:
        short: short background name, eg 'En', 'Be'.
        name: long background name, eg 'Enchanter', 'Berserker'.
        playable: if the background is playable in the current version.
            Not quite sure what to do in the case of a mismatch between stable
            and trunk...
    """

    __tablename__ = "backgrounds"
    id = Column(Integer, primary_key=True, nullable=False)  # type: int
    short = Column(String(2), nullable=False, index=True, unique=True)  # type: str
    name = Column(String(20), nullable=False, index=True, unique=True)  # type: str


@characteristic.with_repr(["name"])  # pylint: disable=too-few-public-methods
class God(Base):
    """A DCSS god.

    Columns:
        name: full god name, eg 'Nemelex Xobeh', 'Trog'.
        playable: if the god is playable in the current version.
            Not quite sure what to do in the case of a mismatch between stable
            and trunk...
    """

    __tablename__ = "gods"
    id = Column(Integer, primary_key=True, nullable=False)  # type: int
    name = Column(String(20), nullable=False, index=True, unique=True)  # type: str


@characteristic.with_repr(["v"])  # pylint: disable=too-few-public-methods
class Version(Base):
    """A DCSS version.

    Columns:
        v: version string, eg '0.17', '0.18'.
    """

    __tablename__ = "versions"
    id = Column(Integer, primary_key=True, nullable=False)  # type: int
    v = Column(String(10), nullable=False, index=True, unique=True)  # type: str


@characteristic.with_repr(["short"])  # pylint: disable=too-few-public-methods
class Branch(Base):
    """A DCSS Branch (Dungeon, Lair, etc).

    Columns:
        short: short code, eg 'D', 'Wizlab'.
        name: full name, eg 'Dungeon', 'Wizard\'s Laboratory'.
        multilevel: Is the branch multi-level? Note: Pandemonium is not
            considered multilevel, since its levels are not numbered ingame.
        playable: Is it playable in the current version?
            Not quite sure what to do in the case of a mismatch between stable
            and trunk...
    """

    __tablename__ = "branches"
    id = Column(Integer, primary_key=True, nullable=False)  # type: int
    short = Column(String(10), nullable=False, index=True, unique=True)  # type: str
    name = Column(String(20), nullable=False, index=True, unique=True)  # type: str
    multilevel = Column(Boolean, nullable=False)  # type: bool


@characteristic.with_repr(["branch", "level"])  # pylint: disable=too-few-public-methods
class Place(Base):
    """A DCSS Place (D:8, Pan:1, etc).

    Note that single-level branches have a single place with level=1 (eg
        Temple:1, Pan:1).
    """

    __tablename__ = "places"
    id = Column("id", Integer, primary_key=True, nullable=False)  # type: int
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)  # type: int
    branch = relationship("Branch")
    level = Column(Integer, nullable=False, index=True)  # type: int

    @property
    def as_string(self) -> str:
        """Return the Place with a pretty name, like D:15 or Temple."""
        # TODO: should specify name in 'normal' form eg 'Gehenna' etc
        if self.branch.multilevel:
            return "%s:%s" % (self.branch.short, self.level)
        else:
            return "%s" % self.branch.short

    __table_args__ = (UniqueConstraint("branch_id", "level", name="branch_id-level"),)


@characteristic.with_repr(["name"])  # pylint: disable=too-few-public-methods
class Ktyp(Base):
    """A DCSS ktyp (mon, beam, etc)."""

    __tablename__ = "ktyps"
    id = Column(Integer, primary_key=True, nullable=False)  # type: int
    name = Column(String(20), nullable=False, index=True, unique=True)  # type: str

@characteristic.with_repr(["name"])  # pylint: disable=too-few-public-methods
class Verb(Base):
    """A DCSS milestone verb (rune, orb, etc)."""

    __tablename__ = "verbs"
    id = Column(Integer, primary_key=True, nullable=False)  # type: int
    name = Column(String(20), nullable=False, index=True, unique=True)  # type: str

@characteristic.with_repr(["gid"])  # pylint: disable=too-few-public-methods
class Game(Base):
    """A single DCSS game.

    Columns (most are self-explanatory):
        gid: unique id for the game, comprised of "name:server:start". For
            compatibility with sequell.
        xl
        tmsg: description of game end
        turn
        dur
        runes
        score
        start: start time for the game (in UTC)
        end: end time for the game (in UTC)
        potions_used
        scrolls_used
    """

    __tablename__ = "games"
    gid = Column(String(50), primary_key=True, nullable=False)  # type: str

    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)  # type: int
    account = relationship("Account")

    # Denormalised data. Set on game record insertion
    player_id = Column(Integer, nullable=False, index=True)  # type: int

    version_id = Column(Integer, ForeignKey("versions.id"), nullable=False)  # type: int
    version = relationship("Version")

    species_id = Column(Integer, ForeignKey("species.id"), nullable=False)  # type: int
    species = relationship("Species")

    background_id = Column(
        Integer, ForeignKey("backgrounds.id"), nullable=False
    )  # type: int
    background = relationship("Background")

    place_id = Column(Integer, ForeignKey("places.id"), nullable=True)  # type: int
    place = relationship("Place")

    god_id = Column(Integer, ForeignKey("gods.id"), nullable=True)  # type: int
    god = relationship("God")

    xl = Column(Integer, nullable=True)  # type: int
    dam = Column(Integer, nullable=True)  # type: int
    sdam = Column(Integer, nullable=True)  # type: int
    tdam = Column(Integer, nullable=True)  # type: int
    tmsg = Column(String(1000), nullable=True)  # type: str
    turn = Column(Integer, nullable=True)  # type: int
    dur = Column(Integer, nullable=True)  # type: int
    runes = Column(Integer, nullable=True)  # type: int
    score = Column(Integer, nullable=True, index=True)  # type: int
    start = Column(DateTime, nullable=False, index=True)  # type: DateTime
    end = Column(DateTime, nullable=True, index=True)  # type: DateTime
    potions_used = Column(Integer, nullable=True)  # type: int
    scrolls_used = Column(Integer, nullable=True)  # type: int

    ktyp_id = Column(Integer, ForeignKey("ktyps.id"), nullable=True)  # type: int
    ktyp = relationship("Ktyp")

    __table_args__ = (
        # Used to find various highscores in model
        # XXX: these indexes should have a sqlite_where=ktyp_id == 'winning'
        # But these indexes can then only be added after the 'winning' ktyp is
        # added.... chicken & egg.
        Index("species_highscore_index", species_id, score),
        Index("background_highscore_index", background_id, score),
        Index("combo_highscore_index", species_id, background_id, score),
        Index("fastest_highscore_index", ktyp_id, dur),
        Index("shortest_highscore_index", ktyp_id, turn),
        # Used by scoring.score_games
        Index("unscored_games", scored, end),
        # Used by scoring.is_grief
        Index("first_game_index", account_id, end),
    )

    @property
    def player(self) -> Player:
        """Convenience shortcut."""
        return self.account.player

    @property
    def won(self) -> bool:
        """Was this game won."""
        return self.ktyp.name == "winning"

    @property
    def quit(self) -> bool:
        """Was this game quit."""
        return self.ktyp.name == "quitting"

    @property
    def boring(self) -> bool:
        """Was this game was quit, left, or wizmoded."""
        return self.ktyp.name in ("quitting", "leaving", "wizmode")

    @property
    def char(self) -> str:
        """Character code eg 'MiFi'."""
        return "{}{}".format(self.species.short, self.background.short)

    @property
    def pretty_tmsg(self) -> str:
        """Pretty tmsg, more suitable for scoreboard display."""
        msg = self.tmsg
        if not msg:
            return msg
        if msg == "escaped with the Orb":
            msg += "!"
        # We don't use str.capitalize because it lower-cases all letters but
        # the first. We just want to specifically capitalise the first letter.
        return msg[0].upper() + msg[1:]

    def as_dict(self) -> dict:
        """Convert to a dict, for public consumption."""
        return {
            "gid": self.gid,
            "account_name": self.account.name,
            "player_name": self.player.name,
            "server_name": self.account.server.name,
            "version": self.version.v,
            "species": self.species.name,
            "background": self.background.name,
            "char": self.char,
            "place": self.place.as_string,
            "god": self.god.name,
            "xl": self.xl,
            "tmsg": self.tmsg,
            "turns": self.turn,
            "dur": self.dur,
            "runes": self.runes,
            "score": self.score,
            "start": self.start.timestamp(),
            "end": self.end.timestamp(),
        }

@characteristic.with_repr(["gid"])  # pylint: disable=too-few-public-methods
class Milestone(Base):
    """A single DCSS game.

    Columns (most are self-explanatory):
        gid: unique id for the game, comprised of "name:server:start". For
            compatibility with sequell.
        xl
        place
        god
        turn
        time
        dur
        runes
        potions_used
        scrolls_used
    """

    __tablename__ = "milestones"
    id = Column(Integer, Primary_Key=True)
    gid = Column(String(50), ForeignKey("games.id", nullable=False)  # type: str
    game = relationship(Game, backref=backref('milestones', uselist=True))

    place_id = Column(Integer, ForeignKey("places.id"), nullable=True)  # type: int
    place = relationship("Place")

    god_id = Column(Integer, ForeignKey("gods.id"), nullable=True)  # type: int
    god = relationship("God")

    xl = Column(Integer, nullable=True)  # type: int
    turn = Column(Integer, nullable=True)  # type: int
    dur = Column(Integer, nullable=True)  # type: int
    runes = Column(Integer, nullable=True)  # type: int
    time = Column(DateTime, nullable=False, index=True)  # type: DateTime
    potions_used = Column(Integer, nullable=True)  # type: int
    scrolls_used = Column(Integer, nullable=True)  # type: int

    verb_id = Column(Integer, ForeignKey("types.id"), nullable=True)  # type: int
    verb = relationship("Type")

    noun = Column(String(1000), nullable=True) # type:str

    def as_dict(self) -> dict:
        """Convert to a dict, for public consumption."""
        return {
            "game": self.game.as_dict,
            "place": self.place.as_string,
            "god": self.god.name,
            "xl": self.xl,
            "turn": self.turn,
            "dur": self.dur,
            "runes": self.runes,
            "verb" : self.verb.name,
            "noun" : self.noun,
            "time" : self.time.timestamp(),
        }

class EventType(enum.Enum):
    game = 'game'
    milestone = 'milestone'

# Object defs

class Event(Base):
    __tablename__ = 'event'
    id = Column(Integer, primary_key=True)
    type = Column(Enum(EventType), nullable=False, index=True)
    data = Column(Text, nullable=False)
    time = Column(DateTime, nullable=False)
    src_abbr = Column(String(10), nullable=False)

    def __repr__(self):
        return "<Event(id={event.id}, type={event.type}, time={event.time}, src_abbr={event.src_abbr}, data={event.data})>".format(event=self)

    def getDict(self):
        return {'id': self.id,
                'type': self.type.value,
                'data': json.loads(self.data),
                'time': timegm(self.time.timetuple()),
                'src_abbr': self.src_abbr}

class Logfile(Base):
    __tablename__ = 'logfile'
    path = Column(String(1000), primary_key=True)
    offset = Column(Integer, default=0, nullable=False)

    def __repr__(self):
        return "<Logfile(path={logfile.path}, offset={logfile.offset})>".format(logfile=self)


# End Object defs

engine = create_engine(SQLALCHEMY_DATABASE_URI)

session_factory = sessionmaker(bind=engine, expire_on_commit=False, autocommit=False)
Base.metadata.create_all(engine)

if os.environ.get('SCOREBOARD_SKIP_DB_SETUP') == None:
    model.setup_species(sess)
    model.setup_backgrounds(sess)
    model.setup_gods(sess)
    model.setup_branches(sess)
    model.setup_achievements(sess)
    model.setup_ktyps(sess)

@contextmanager
def get_session():
    Session = scoped_session(session_factory)
    yield Session()
    Session.remove()
