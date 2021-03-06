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

	def _god(self, name):
		with get_session() as s:
			god_id = get_god(s, name).id
			rune_verb = get_verb(s, "rune").id
			return self._valid_milestone().filter(
				Milestone.god_id == god_id, Milestone.verb_id == rune_verb, Milestone.runes == 1
			).exists()

	def _rune(self, name):
		with get_session() as s:
			place = get_place_from_string(s, name)
			rune_verb = get_verb(s, "rune").id
			return self._valid_milestone().filter(
				Milestone.place_id == place.id, Milestone.verb_id == rune_verb
			).exists()

	def _realtime(self, seconds):
		with get_session() as s:
			orb_verb = get_verb(s, "orb").id
			return self._valid_milestone().filter(
				Milestone.dur <= seconds, Milestone.verb_id == orb_verb
			).exists()

	def _turncount(self, name, turns):
		with get_session() as s:
			place = get_place_from_string(s, name)
			return self._valid_milestone().filter(
				Milestone.place_id == place.id, Milestone.turn <= turns
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
			type_coerce(self._XL(10) * 10, Integer).label("xl"),
			type_coerce(self._win() * 15, Integer).label("win"),
			
			type_coerce(self._realtime(6000) * 20, Integer).label("time"),
			type_coerce(self._turncount("Dis:1", 30000) * 20, Integer).label("turns"),
			
			type_coerce(self._rune("Slime:5") * 10, Integer).label("slimy"),
			type_coerce(self._rune("Vaults:3") * 10, Integer).label("silver"),
			type_coerce(self._rune("Dis:2") * 10, Integer).label("iron"),
			type_coerce(self._rune("Tar:2") * 10, Integer).label("bone"),
			type_coerce(self._rune("Geh:2") * 10, Integer).label("obsidian"),
			type_coerce(self._rune("Coc:2") * 10, Integer).label("icy"),
			type_coerce(self._rune("Pan") * 20, Integer).label("pan"),
			
			type_coerce(self._god("Qazlal") * 6, Integer).label("qaz"),
			type_coerce(self._god("Jiyva") * 6, Integer).label("jiyva"),
			type_coerce(self._god("Lugonu") * 6, Integer).label("lucy"),
			type_coerce(self._god("Cheibriados") * 6, Integer).label("chei"),
		]).filter(Game.gid.in_(self.gids)).subquery()

		return Query( [Player, Game]).select_from(Player).outerjoin(Game,
				Game.gid == sc.c.gid).add_columns(
					sc.c.xl,
					sc.c.win,
					
					sc.c.time,
					sc.c.turns,
					
					sc.c.slimy,
					sc.c.silver,
					sc.c.iron,
					sc.c.bone,
					sc.c.obsidian,
					sc.c.icy,
					sc.c.pan,
					
					sc.c.qaz,
					sc.c.chei,
					sc.c.lucy,
					sc.c.jiyva,
					
					func.max(sc.c.xl + sc.c.win).label("subtotal"),
					func.max(sc.c.xl + sc.c.win + 
					sc.c.time + sc.c.turns + 
					sc.c.slimy + sc.c.silver + sc.c.iron + sc.c.bone + sc.c.obsidian + sc.c.icy + sc.c.pan + 
					sc.c.qaz + sc.c.chei + sc.c.lucy + sc.c.jiyva).label("total")
			).group_by(sc.c.player_id).order_by(desc("total"),Game.start)

weeks = []

def initialize_weeks():
	with get_session() as s:
		
		weeks.append(CsdcWeek(
			number = "1",
			species = "Sk",
			background = "AK",
			gods = (),
			start = datetime.datetime(2019,12,20),
			end = datetime.datetime(2019,12,29)))
		weeks.append(CsdcWeek(
			number = "2",
			species = "On",
			background = "VM",
			gods = (),
			start = datetime.datetime(2019,12,23),
			end = datetime.datetime(2020,1,1)))
		weeks.append(CsdcWeek(
			number = "3",
			species = "VS",
			background = "Rg",
			gods = (),
			start = datetime.datetime(2019,12,26),
			end = datetime.datetime(2020,1,4)))
		weeks.append(CsdcWeek(
			number = "4",
			species = "Dj",
			background = "Cj",
			gods = (),
			start = datetime.datetime(2019,12,29),
			end = datetime.datetime(2020,1,7)))
		weeks.append(CsdcWeek(
			number = "5",
			species = "SD",
			background = "SA",
			gods = (),
			start = datetime.datetime(2020,1,1),
			end = datetime.datetime(2020,1,10)))
		weeks.append(CsdcWeek(
			number = "6",
			species = "Hu",
			background = "Wz",
			gods = (),
			start = datetime.datetime(2020,1,4),
			end = datetime.datetime(2020,1,13)))


def overview():
	q = Query(Player)
	totalcols = []
	for wk in weeks:
		wk_n = "wk" + wk.number
		a = wk.scorecard().subquery()
		q = q.outerjoin(a, Player.id == a.c.player_id).add_column(a.c.subtotal.label(wk_n)).add_column(a.c.time.label(wk_n + "time")).add_column(a.c.turns.label(wk_n + "turns")).add_column(a.c.slimy.label(wk_n + "slimy")).add_column(a.c.silver.label(wk_n + "silver")).add_column(a.c.iron.label(wk_n + "iron")).add_column(a.c.bone.label(wk_n + "bone")).add_column(a.c.obsidian.label(wk_n + "obsidian")).add_column(a.c.icy.label(wk_n + "icy")).add_column(a.c.pan.label(wk_n + "pan")).add_column(a.c.qaz.label(wk_n + "qaz")).add_column(a.c.chei.label(wk_n + "chei")).add_column(a.c.lucy.label(wk_n + "lucy")).add_column(a.c.jiyva.label(wk_n + "jiyva"))

	return q

divisions = [1]
