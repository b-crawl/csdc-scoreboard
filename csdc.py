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

# todo: clean up the retry removal
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
				).filter(pg2.c.gid == None)

	def _valid_milestone(self):
		return Query(Milestone).filter(Milestone.gid == Game.gid,
				Milestone.time <= self.end);

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

	def _XL(self, n):
		return self._valid_milestone().filter(
			Milestone.xl >= n
		).exists()

	def _win(self):
		with get_session() as s:
			ktyp_id = get_ktyp(s, "winning").id

		return and_(Game.ktyp_id != None, 
			Game.ktyp_id == ktyp_id,
			Game.end <= self.end)

	def scorecard(self):
		sc = Query([Game.gid,
			Game.player_id,
			type_coerce(self._XL(12) * 12, Integer).label("xl"),
			type_coerce(self._win() * 20, Integer).label("win"),
		]).filter(Game.gid.in_(self.gids)).subquery()

		return Query( [Player, Game]).select_from(Player).outerjoin(Game,
				Game.gid == sc.c.gid).add_columns(
					sc.c.xl,
					sc.c.win,
					func.max(
						sc.c.xl
						+ sc.c.win
					).label("total")
			).group_by(sc.c.player_id).order_by(desc("total"),Game.start)

weeks = []

def initialize_weeks():
	with get_session() as s:
		
		start_date = datetime.datetime(2018,10,4)
		end_date = datetime.datetime(2019,10,11)
		
		weeks.append(CsdcWeek(
			number = "1",
			species = "Mi",
			background = "SA",
			gods = (),
			start = start_date,
			end = end_date))
		weeks.append(CsdcWeek(
			number = "2",
			species = "Dg",
			background = "Gl",
			gods = (),
			start = start_date,
			end = end_date))
		weeks.append(CsdcWeek(
			number = "3",
			species = "Fe",
			background = "Mo",
			gods = (),
			start = start_date,
			end = end_date))
		weeks.append(CsdcWeek(
			number = "4",
			species = "Vp",
			background = "Rg",
			gods = (),
			start = start_date,
			end = end_date))
		weeks.append(CsdcWeek(
			number = "5",
			species = "SD",
			background = "Sk",
			gods = (),
			start = start_date,
			end = end_date))
		weeks.append(CsdcWeek(
			number = "6",
			species = "Fo",
			background = "AM",
			gods = (),
			start = start_date,
			end = end_date))
		weeks.append(CsdcWeek(
			number = "7",
			species = "Av",
			background = "Re",
			gods = (),
			start = start_date,
			end = end_date))
		weeks.append(CsdcWeek(
			number = "8",
			species = "Na",
			background = "VM",
			gods = (),
			start = start_date,
			end = end_date))


def overview():
	q = Query(Player)
	totalcols = []
	for wk in weeks:
		a = wk.scorecard().subquery()
		totalcols.append(func.ifnull(a.c.total, 0))
		q = q.outerjoin(a, Player.id == a.c.player_id
				).add_column( a.c.total.label("wk" + wk.number))

	return q.add_column(
			sum(totalcols).label("grandtotal")
		).filter(sum(totalcols) > 0).order_by(desc("grandtotal"))

divisions = [1]
