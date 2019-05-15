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
			type_coerce(self._XL(12) * 12, Integer).label("xl"),
			type_coerce(self._win() * 20, Integer).label("win"),
			
			type_coerce(self._realtime(3000) * 25, Integer).label("time"),
			type_coerce(self._turncount("Dis:1", 40000) * 20, Integer).label("turns"),
			
			type_coerce(self._rune("Slime:5") * 10, Integer).label("slimy"),
			type_coerce(self._rune("Vaults:3") * 10, Integer).label("silver"),
			type_coerce(self._rune("Dis:2") * 10, Integer).label("iron"),
			type_coerce(self._rune("Tar:2") * 10, Integer).label("bone"),
			type_coerce(self._rune("Geh:2") * 10, Integer).label("obsidian"),
			type_coerce(self._rune("Coc:2") * 10, Integer).label("icy"),
			
			type_coerce(self._god("Vehumet") * 4, Integer).label("veh"),
			type_coerce(self._god("Cheibriados") * 4, Integer).label("chei"),
			type_coerce(self._god("Dithmenos") * 4, Integer).label("dith"),
			type_coerce(self._god("Fedhas") * 4, Integer).label("fedhas"),
			type_coerce(self._god("Nemelex Xobeh") * 4, Integer).label("nemelex"),
			type_coerce(self._god("Wu Jian") * 4, Integer).label("wu"),
			type_coerce(self._god("Sif Muna") * 4, Integer).label("sif"),
			type_coerce(self._god("Uskayaw") * 4, Integer).label("usk"),
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
					
					sc.c.veh,
					sc.c.chei,
					sc.c.dith,
					sc.c.fedhas,
					sc.c.nemelex,
					sc.c.wu,
					sc.c.sif,
					sc.c.usk,
					
					func.max(sc.c.xl + sc.c.win).label("subtotal"),
					func.max(sc.c.xl + sc.c.win + 
					sc.c.time + sc.c.turns + 
					sc.c.slimy + sc.c.silver + sc.c.iron + sc.c.bone + sc.c.obsidian + sc.c.icy + 
					sc.c.veh + sc.c.chei + sc.c.dith + sc.c.fedhas + sc.c.nemelex + sc.c.wu + sc.c.sif + sc.c.usk).label("total")
			).group_by(sc.c.player_id).order_by(desc("total"),Game.start)

weeks = []

def initialize_weeks():
	with get_session() as s:
		
		start_date = datetime.datetime(2018,10,4)
		end_date = datetime.datetime(2019,10,11)
		
		weeks.append(CsdcWeek(
			number = "1",
			species = "Dg",
			background = "Gl",
			gods = (),
			start = start_date,
			end = end_date))
		weeks.append(CsdcWeek(
			number = "2",
			species = "Mi",
			background = "SA",
			gods = (),
			start = start_date,
			end = end_date))
		weeks.append(CsdcWeek(
			number = "3",
			species = "Vp",
			background = "Rg",
			gods = (),
			start = start_date,
			end = end_date))
		weeks.append(CsdcWeek(
			number = "4",
			species = "Fe",
			background = "Mo",
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
			species = "Na",
			background = "VM",
			gods = (),
			start = start_date,
			end = end_date))
		weeks.append(CsdcWeek(
			number = "8",
			species = "Av",
			background = "Re",
			gods = (),
			start = start_date,
			end = end_date))


def overview():
	q = Query(Player)
	totalcols = []
	for wk in weeks:
		wk_n = "wk" + wk.number
		a = wk.scorecard().subquery()
		q = q.outerjoin(a, Player.id == a.c.player_id).add_column(a.c.subtotal.label(wk_n)).add_column(a.c.time.label(wk_n + "time")).add_column(a.c.turns.label(wk_n + "turns")).add_column(a.c.slimy.label(wk_n + "slimy")).add_column(a.c.silver.label(wk_n + "silver")).add_column(a.c.iron.label(wk_n + "iron")).add_column(a.c.bone.label(wk_n + "bone")).add_column(a.c.obsidian.label(wk_n + "obsidian")).add_column(a.c.icy.label(wk_n + "icy")).add_column(a.c.veh.label(wk_n + "veh")).add_column(a.c.chei.label(wk_n + "chei")).add_column(a.c.dith.label(wk_n + "dith")).add_column(a.c.fedhas.label(wk_n + "fedhas")).add_column(a.c.nemelex.label(wk_n + "nemelex")).add_column(a.c.wu.label(wk_n + "wu")).add_column(a.c.sif.label(wk_n + "sif")).add_column(a.c.usk.label(wk_n + "usk"))

	return q

divisions = [1]
