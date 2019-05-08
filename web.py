import datetime
from orm import get_session
from modelutils import morgue_url
import csdc

TIMEFMT = "%H:%M %Z"
DATEFMT = "%Y-%m-%d"
DATETIMEFMT = DATEFMT + " " + TIMEFMT

def updated():
	now = datetime.datetime.now(datetime.timezone.utc).strftime(DATETIMEFMT)
	return '<span id="updated"><span class="label">Updated: </span>{}</span></div>'.format(now)


def head(static, title):
	refresh = '<meta http-equiv="refresh" content="300">' if not static else ""
	return """<head><title>{0}</title>
	<link rel="stylesheet" href="static/score.css">
	{1}</head>""".format(title, refresh)


version = '1.12'

def logoblock(subhead):
	sh = "<h2>{}</h2>".format(subhead) if subhead != None else ""
	return """<div id="title">
	<br><img id="logo" src="static/logo.png"><br><br><br>
	<h1 id="sdc">{} sudden death tournament<br><br></h1>
	{}</div>""".format(version, sh)


def mainmenu():
	return ('<span class="menu"><a href="index.html">Overview</a></span>' +
		'<span class="menu"><a href="rules.html">Rules</a></span>' + 
		'<span class="menu"><a href="standings.html">Standings</a></span>' +
		'<span class="menuspacer"></span>')


def wkmenu(wk):
	sp = ""
	for w in csdc.weeks:
		menuitem = ""
		if ((wk is None or 
			w.number != wk.number)
			and w.start <= datetime.datetime.now()):
			menuitem += wkurl(w)
		else:
			menuitem += '{}'
		sp += '<span class="menu">{}</span>'.format(menuitem.format("Combo " +
			w.number))
	return sp


def wkinfo(wk):
	sp = ""
	sp += ('<div id="combo">' +
			'{0} {1}</div>\n'.format(wk.species.name, wk.background.name))
	sp += ", ".join([ g.name for g in wk.gods])
	sp += '</div>'

	return sp


def wkurl(wk):
	return '<a href="'+ wk.number + '.html">{}</a>'


def description(wk, url):
	s = ""

	if wk.start > datetime.datetime.now():
		s += "Character {0}"
	else:
		s += "Character {0}&mdash;{1}{2}"

	if url and wk.start <= datetime.datetime.now():
		s = wkurl(wk).format(s)

	return s.format(wk.number, wk.species.short,
				wk.background.short)



def scoretable(wk, div):
	sp = ""
	sp += ("""<table><tr class="head">
	<th>Player</th>
	<th>Reach L12</th>
	<th>Win</th>
	<th>Total</th>
	</tr>""")

	with get_session() as s:
		for g in wk.scorecard().with_session(s).all():
			if g.Game == None:
				sp += """<tr class="{}"><td class="name">{}</td>
				<td colspan="9"></td><td class="total">0</td></tr>""".format(
						"none", g.Player.name)
				continue

			sp += ('<tr class="{}">'.format(
				"won" if g.Game.won and g.Game.end <= wk.end else
				"alive" if g.Game.alive else
				"dead"))
			sp += ('<td class="name"><a href="{}">{}</a></td>'.format(
				morgue_url(g.Game), g.Game.player.name))
			sp += ( (('<td class="pt">{}</td>' * 2) 
				+ '<td class="total">{}</td>').format(
				g.xl,
				g.win,
				g.total))
			sp += ('</tr>\n')

	sp += '</table>'

	return sp


def _ifnone(x, d):
	"""this should be a language builtin like it is in sql"""
	return x if x is not None else d


def standingstable():
	with get_session() as s:
		sp = "<table>"
		sp += '<tr class="head"><th>Player</th>'
		sp += ''.join(['<th>' + description(wk, True) +'</th>' for wk in csdc.weeks
			])
		sp +='<th>Runes</th><th>Gods</th><th>Speed</th>'
		sp += '<th>Score</th></tr>'
		for p in csdc.overview().with_session(s).all():
			sp += '<tr>'
			sp += '<td class="name">{}</td>'.format(p.CsdcContestant.player.name)
			sp += ('<td class="pt">{}</td>' * len(csdc.weeks)).format(
					*[ _ifnone(getattr(p, "wk" + wk.number), "") for wk in csdc.weeks])
			sp += '<td class="pt"></td>' * 3
			sp += '<td class="total">{}</td>'.format(p.grandtotal)
			sp += '</tr>'

		return sp


def scorepage(wk):
	return page( static=False, subhead = description(wk, False),
			content = wkinfo(wk) + 
			" ".join([ scoretable(wk, d) for d in csdc.divisions]),
			menu = wkmenu(wk))


def standingspage():
	return page( static=False,
			subhead = "Standings",
			content = standingstable())

def standingsplchold():
	return page( static=True,
			subhead = "Registrations are not yet being processed. Check back soon.",
			content = "" )

def overviewpage():
	pagestr = """
	<pre id="cover">
Near the exit of the stairs, a rune flashes!
You find yourself in a tournament!
Yermak, Manman, Dynast, and Ultraviolent4 come into view.</pre>
<br><br>

<h2>Competition Format</h2>

<ul>
<li>8 interesting combos to play have been selected for this competition.</li>
<li>They can be played in any order.</li>
<li>You get <em>one</em> attempt to play each combo, but can retry <em>once</em> if you have not reached level 5 with that combo.</li>
<li>The goal is to advance as far as possible (and win!) in each game, scoring
points by reaching various in-game milestones.</li>
<li>Details on rules and scoring are available on the <a
href="rules.html">rules page</a>.</li>
</ul>

<h2>Tournament Combos</h2>

{}

<h2>How to Participate</h2>

<p>To participate, just play bcrawl online on <a href="https://crawl.develz.org/play.htm">CKO (New York)</a> or <a href="https://crawl.develz.org/play.htm">CPO (Australia)</a> during the tournament period.</p>

<h2>Credits</h2>
<p>hosting, rules: bhauth<br>
programming: bhauth, doesnty<br>
based on code by: <a href="https://github.com/ebering/csdc-scoreboard">ebering</a>, zxc, Kramin<br>
logo design: <a href="https://www.youtube.com/channel/UCzmCTHcYFM5nnAPBYE26Fng">Demise</a><br></p>
"""

	wklist = "<ul id=schedule>"
	for wk in csdc.weeks:
		wklist += '<li><span class=label>{}:</span> {} to {}'.format(description(wk,True),
				wk.start.strftime(DATEFMT),
				wk.end.strftime(DATEFMT))
	wklist += "</ul>"

	return page( static = True, title="bcrawl tournament", content = pagestr.format(wklist))

def rulespage():
	pagestr ="""
	<ol>
<li>Each challenge consists of playing a specific race/class
combo (e.g. MiBe). Only milestones recorded during the tournament period will count for scoring.</li>
<li>Your first game of each combo that's started on an official server during the tournament period will count
for scoring. This is the only allowed attempt, subject to rule 3 below.</li>
<li>One redo per week is allowed if player XL < 5 (i.e., no redo once you hit
XL 5). The highest score of the two games is counted towards your score.</li>
<li>Tiebreakers are (in order): number of weekly bonus points, highest in-game
score.</li>
</ol>

<h2>Scoring</h2>

<p>Scoring is divided into two parts, game points assigned to each game
played, and one-time points awarded once regardless of how many
games achieve them.</p>

<table class="info"><tr class="head"><th>Game points (can be earned for each combo)</th><th></th></tr>
<tr><td class="name">reach level 12: 12 points</td></tr>
<tr><td class="name">win: 20 points</td></tr>
</table>
<table class="info"><tr class="head" id="onetime"><th>One-time points (earned once in the
competition)</th><th></th></tr>
<tr><td class="name">1000/(fastest realtime win in minutes) points</td></tr>
<tr><td class="name">10 points each for the following runes: slimy, silver, iron, icy, obsidian, bone</td></tr>
<tr><td class="name">4 points for each of these gods you reach ****** piety with: Dithmenos, Fedhas, Nemelex, Wu Jian, Sif Muna, Uskayaw</td></tr>
</table>

<h2>Fair Crawling</h2>

<p>Players using multiple accounts for extra attempts may be disqualified. Macros (including for multiple tabs/autoattacks) are allowed, but accounts playing at speeds implausible for humans may be disqualified. bhauth reserves the right to disqualify players for any reason.</p>
<p></p>
"""
	return page(static=True, subhead="Rules", content = pagestr.format("0.22"))


def page(**kwargs):
	"""static, title, subhead, content"""
	return """<html>{}<body>{}<div id="content">{}</div>
	<div id="bottomtext">{}</div></body></html>""".format(
			head(kwargs["static"],kwargs.get("title",kwargs.get("subhead",""))),
			logoblock(kwargs.get("subhead","")),
			kwargs["content"],
			mainmenu() + kwargs.get("menu", wkmenu(None)) + (updated() if not kwargs["static"] else
				""))
