import datetime
from collections import namedtuple
from model import (
    latestmilestones,
    get_species,
    get_background,
    get_branch,
    get_place_from_string,
    get_god,
    get_ktyp,
    get_verb
)
from modelutils import morgue_url
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
    Skill,
    CsdcContestant,
    get_session,
)

from sqlalchemy import asc, desc, func, type_coerce, Integer, literal
from sqlalchemy.sql import and_, or_
from sqlalchemy.orm.query import (
    aliased,
    Query
)

CsdcBonus = namedtuple("CsdcBonus", ["name", "description", "query", "pts"])
# The query here must be a scalar query, see no bonus for the example.

NoBonus = CsdcBonus("NoBonus","No bonus",[literal(False)], "0")

def _champion_god(milestones, god):
    """Query if the supplied god get championed in the provided milestone set"""
    with get_session() as s:
        worship_id = get_verb(s, "god.worship").id
        champ_id = get_verb(s, "god.maxpiety").id
    maxpiety = milestones.filter(
                Milestone.god_id == god.id,
                Milestone.verb_id == champ_id
            ).exists()
    worship = milestones.filter(
                Milestone.god_id == god.id,
                Milestone.verb_id == worship_id
            ).exists()
    neverworship = ~milestones.filter(
                Milestone.verb_id == worship_id
            ).exists()

    champion_conditions = {
        "GOD_NO_GOD" : neverworship,
        "Xom" : worship,
        "Gozag" : worship
    }

    return champion_conditions.get(god.name, maxpiety)


class CsdcWeek:
    """A csdc week

    This object generates the queries needed to score a csdc week"""

    def _valid_games(self, alias):
        """Query the gids in an alias for the Games table for the valid ones

        There are a lot of games but not that many in a given time window,
        there is a good index for this filter, so even if it is implied one
        should endavour to use it.
 
        add_columns can specify further columns, but as-is this is hit by a
        covering index"""
        return Query(alias.gid).filter(
                alias.species_id == self.species.id,
                alias.background_id == self.background.id,
                alias.start >= self.start,
                alias.start <= self.end
            )


    def __init__(self, **kwargs):
        with get_session() as s:
            self.number = kwargs["number"]
            self.species = get_species(s, kwargs["species"])
            self.background = get_background(s, kwargs["background"])
            self.gods = [ get_god(s, g) for g in kwargs["gods"] ]
            self.start = kwargs["start"]
            self.end = kwargs["end"]
            self.tier1 = kwargs.get("bonus1", NoBonus)
            self.tier2 = kwargs.get("bonus2", NoBonus)

        g1 = aliased(Game)
        g2 = aliased(Game)
        possiblegames = self._valid_games(g1).add_columns(
                g1.player_id,
                g1.start,
                g1.end
            ).filter(g1.gid.in_(
                self._valid_games(g2).filter(
                    g2.player_id == g1.player_id
                ).order_by(g2.start).limit(2))
            ).join(latestmilestones, g1.gid == latestmilestones.c.gid
            ).add_column(latestmilestones.c.xl).cte()
        pg2 = possiblegames.alias()
        self.gids = Query(possiblegames.c.gid).outerjoin(pg2,
                and_(pg2.c.player_id == possiblegames.c.player_id,
                    possiblegames.c.start > pg2.c.start)
                ).filter(or_(pg2.c.gid == None,
                    and_(pg2.c.end != None, pg2.c.xl < 5)))


    def _valid_milestone(self):
        return Query(Milestone).filter(Milestone.gid == Game.gid,
                Milestone.time <= self.end);

    def _uniq(self):
        with get_session() as s:
            verb_ids = [ get_verb(s, u).id for u in ["uniq", "uniq.ban",
            "uniq.pac", "uniq.slime"]]

        return self._valid_milestone().filter(Milestone.verb_id.in_(verb_ids)).exists()

    def _brenter(self):
        with get_session() as s:
            verb_id = get_verb(s, "br.enter").id
            d_id = get_branch(s, "D").id
            multilevel_places = Query(Place.id).join(Branch).filter(
                    Branch.id != d_id, Branch.multilevel)

        return self._valid_milestone().filter(
            Milestone.place_id.in_(multilevel_places),
            Milestone.verb_id == verb_id
        ).exists()

    def _brend(self):
        with get_session() as s:
            verb_id = get_verb(s, "br.end").id
            multilevel_places = Query(Place.id).join(Branch).filter(Branch.multilevel)

        return self._valid_milestone().filter(
            Milestone.place_id.in_(multilevel_places),
            Milestone.verb_id == verb_id
        ).exists()

    def _god(self):
        with get_session() as s:
            worship_id = get_verb(s, "god.worship").id
            champ_id = get_verb(s, "god.maxpiety").id
            abandon_id = get_verb(s, "god.renounce").id
        god_ids = [g.id for g in self.gods]
        return and_(
            or_(*[_champion_god(self._valid_milestone(), g) for g in
                self.gods]),
            ~self._valid_milestone().filter(
                Milestone.verb_id == abandon_id
            ).exists())

    def _rune(self, n):
        return self._valid_milestone().filter(
            Milestone.runes >= n
        ).exists()

    def _win(self):
        with get_session() as s:
            ktyp_id = get_ktyp(s, "winning").id

        return type_coerce(and_(Game.ktyp_id != None, 
            Game.ktyp_id == ktyp_id,
            Game.end <= self.end), Integer)

    def _bonus(self, bonus):
        """in principle we support more than two bonuses"""
        return type_coerce(self._valid_milestone().filter(
                *bonus.query
            ).exists(), Integer).__mul__(bonus.pts)

    def scorecard(self):
        sc = Query([Game.gid,
            Game.player_id,
            type_coerce(self._uniq(), Integer).label("uniq"),
            type_coerce(self._brenter(), Integer).label("brenter"),
            type_coerce(self._brend(), Integer).label("brend"),
            type_coerce(self._god(), Integer).label("god"),
            type_coerce(self._rune(1), Integer).label("rune"),
            type_coerce(self._rune(3), Integer).label("threerune"),
            self._win().label("win"),
            self._bonus(self.tier1).label("bonusone"),
            self._bonus(self.tier2).label("bonustwo"),
        ]).filter(Game.gid.in_(self.gids)).subquery()

        return Query( [Player, Game]).select_from(CsdcContestant).join(Player
                ).outerjoin(sc, CsdcContestant.player_id ==
                        sc.c.player_id).outerjoin(Game,
                Game.gid == sc.c.gid).add_columns(
                    sc.c.uniq,
                    sc.c.brenter,
                    sc.c.brend,
                    sc.c.god,
                    sc.c.rune,
                    sc.c.threerune,
                    sc.c.win,
                    sc.c.bonusone,
                    sc.c.bonustwo,
                    func.max(
                        sc.c.uniq
                        + sc.c.brenter
                        + sc.c.brend
                        + sc.c.god
                        + sc.c.rune
                        + sc.c.threerune
                        + sc.c.win
                        + sc.c.bonusone
                        + sc.c.bonustwo
                    ).label("total")
            ).group_by(CsdcContestant.player_id).order_by(desc("total"),Game.start)

weeks = []

def initialize_weeks():
    with get_session() as s:
        m2 = aliased(Milestone)
        lairbonus = CsdcBonus("RuneInBranch",
            "Get a rune without leaving any branch (other than D).",
            [ Milestone.runes > 0,
                Milestone.id.in_(Query(m2.id).filter(
                    Milestone.gid == m2.gid,
                    m2.verb_id == get_verb(s, "br.exit").id,
                    ~m2.place_id.in_(Query(Place.id).join(Branch).filter(
                        Branch.id != get_branch(s, "D").id))
                    ).order_by(m2.time).limit(1)) ],
            1)
        lair1 = get_place_from_string(s, "Lair:1")
        alllairbonus = CsdcBonus("LairRunesInLair",
            "Enter Lair with no runes and leave with at least three.",
            [ Milestone.runes >= 3,
                Milestone.verb_id == get_verb(s, "br.exit").id,
                Milestone.oplace_id == lair1.id,
                Query(m2).filter(
                    m2.gid == Milestone.gid,
                    m2.verb_id == get_verb(s, "br.enter").id,
                    m2.place_id == lair1.id,
                    m2.runes == 0).exists() ],
            "2")

        weeks.append(CsdcWeek(
                number = "1",
                species = "DD",
                background = "Fi",
                gods = ("Makhleb", "Trog", "Okawaru"),
                start = datetime.datetime(2018,10,4),
                end = datetime.datetime(2018,10,11)))
        weeks.append(CsdcWeek(
                number = "2",
                species = "DD",
                background = "Fi",
                gods = ("Makhleb", "Trog", "Okawaru"),
                start = datetime.datetime(2018,10,11),
                end = datetime.datetime(2018,10,18)))
        weeks.append(CsdcWeek(
                number = "3",
                species = "DD",
                background = "Fi",
                gods = ("Makhleb", "Trog", "Okawaru"),
                start = datetime.datetime(2018,10,18),
                end = datetime.datetime(2018,10,25)))
        weeks.append(CsdcWeek(
                number = "4",
                species = "DD",
                background = "Fi",
                gods = ("Makhleb", "Trog", "Okawaru"),
                start = datetime.datetime(2018,10,25),
                end = datetime.datetime(2018,11,1)))
        weeks.append(CsdcWeek(
                number = "5",
                species = "DD",
                background = "Fi",
                gods = ("Makhleb", "Trog", "Okawaru"),
                start = datetime.datetime(2018,11,8),
                end = datetime.datetime(2018,11,15)))
        weeks.append(CsdcWeek(
                number = "6",
                species = "DD",
                background = "Fi",
                gods = ("Makhleb", "Trog", "Okawaru"),
                start = datetime.datetime(2018,11,15),
                end = datetime.datetime(2018,11,22)))
        weeks.append(CsdcWeek(
                number = "7",
                species = "DD",
                background = "Fi",
                gods = ("Makhleb", "Trog", "Okawaru"),
                start = datetime.datetime(2018,11,22),
                end = datetime.datetime(2018,11,29)))


def overview():
    q = Query(CsdcContestant)
    totalcols = []
    for wk in weeks:
        a = wk.scorecard().subquery()
        totalcols.append(func.ifnull(a.c.total, 0))
        q = q.outerjoin(a, CsdcContestant.player_id == a.c.player_id
                ).add_column( a.c.total.label("wk" + wk.number))

    return q.add_column(
            sum(totalcols).label("grandtotal")
        ).order_by(desc("grandtotal"))

divisions = [1]
