import datetime
from model import (
    latestmilestones,
    get_species,
    get_background,
    get_branch,
    get_god,
    get_ktyp,
    get_verb
)
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
    get_session,
)

from sqlalchemy import asc, desc, func
from sqlalchemy.sql import and_, or_
from sqlalchemy.orm.query import (
    aliased,
    Query
)

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


    def __init__(self, number, species, background, gods, start, end):
        with get_session() as s:
            self.number = number
            self.species = get_species(s, species)
            self.background = get_background(s, background)
            self.gods = [ get_god(s, g) for g in gods ]
            self.start = start
            self.end = end

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
            self._valid_milestone().filter(
                ~Milestone.god_id.in_(god_ids),
                Milestone.verb_id == worship_id
            ).exists(),
            self._valid_milestone().filter(
                Milestone.god_id.in_(god_ids),
                Milestone.verb_id == champ_id
            ).exists(),
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

        return Query(Game.ktyp_id == ktyp_id)

    def scorecard(self):
        return Query([Game.gid, Game.player_id, 
            self._uniq().label("uniq"),
            self._brenter().label("brenter"),
            self._brend().label("brend"),
            self._god().label("god"),
            self._rune(1).label("rune"),
            self._rune(3).label("threerune"),
            self._win().label("win")]
        ).filter(Game.gid.in_(self.gids))

if __name__=='__main__':
    wk = CsdcWeek(1, "DE", "En", ("Sif Muna", "Xom", "GOD_NO_GOD"),
            datetime.datetime(2018,9,4), datetime.datetime(2018,9,11));

    with get_session() as s:
        print(wk.scorecard().with_session(s).all())
