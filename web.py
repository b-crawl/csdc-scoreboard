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


version = '0.22'

def logoblock(subhead):
    sh = "<h2>{}</h2>".format(subhead) if subhead != None else ""
    return """<div id="title">
    <img id="logo" src="static/logo.png">
    <h1 id="sdc">{} sudden death challenges</h1>
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
        sp += '<span class="menu">{}</span>'.format(menuitem.format("Week " +
            w.number))
    return sp


def wkinfo(wk):
    sp = ""
    sp += '<div id="times"><span class="label">Week of '
    sp += wk.start.strftime(DATEFMT) + '</span></div>'
    sp += ('<div id="combo"><span class="label">Character: </span>' +
            '{0} {1}</div>\n'.format(wk.species.name, wk.background.name))
    sp += ('<div id="bonus"><span class="label">Tier I Bonus: </span>'
            + wk.tier1.description + '<br/>\n'
            + '<span class="label">Tier II Bonus: </span>'
            + wk.tier2.description +'</div>\n')
    sp += ('<div id="gods"><span class="label">Gods: </span>')
    sp += ", ".join([ g.name for g in wk.gods])
    sp += '</div>'

    return sp


def wkurl(wk):
    return '<a href="'+ wk.number + '.html">{}</a>'


def description(wk, url):
    s = ""

    if wk.start > datetime.datetime.now():
        s += "Week {0}"
    else:
        s += "Week {0}&mdash;{1}{2}"

    if url and wk.start <= datetime.datetime.now():
        s = wkurl(wk).format(s)

    return s.format(wk.number, wk.species.short,
                wk.background.short)



def scoretable(wk, div):
    sp = ""
    sp += ("""<table><tr class="head">
    <th>Player</th>
    <th>Unique Kill</th>
    <th>Branch Enter</th>
    <th>Branch End</th>
    <th>Champion God</th>
    <th>Collect a Rune</th>
    <th>Collect 3 Runes</th>
    <th>Win</th>
    <th>Bonus I</th>
    <th>Bonus II</th>
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
            sp += ( (('<td class="pt">{}</td>' * 9) 
                + '<td class="total">{}</td>').format(
                g.uniq,
                g.brenter,
                g.brend,
                g.god,
                g.rune,
                g.threerune,
                g.win,
                g.bonusone,
                g.bonustwo,
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
        sp +='<th>15 Rune Win</th><th>Win &lt;50k Turns</th><th>Zig:$</th>'
        sp +='<th>Zot @ XL20</th><th>No Lair Win</th><th>Ascetic Rune</th>'
        sp += '<th>Score</th></tr>'
        for p in csdc.overview().with_session(s).all():
            sp += '<tr>'
            sp += '<td class="name">{}</td>'.format(p.CsdcContestant.player.name)
            sp += ('<td class="pt">{}</td>' * len(csdc.weeks)).format(
                    *[ _ifnone(getattr(p, "wk" + wk.number), "") for wk in csdc.weeks])
            sp += '<td class="pt"></td>' * 6
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
_You are suddenly pulled into a different region of the Abyss!
_A floating eye, a glowing orange brain, 4 small abominations and 8 large
 abominations come into view.</pre>
<p>The Crawl Sudden Death Challenges is a competition that aims to fill a
Crawl niche not currently filled by the biannual version release tournaments.
The idea is for players to compete by trying to do as well as possible in a
game of Crawl with one attempt only; if you die, that challenge is over (thus
"sudden death", though you may&mdash;<em>will</em>&mdash;also die suddenly). This competition is
a lower time commitment event that aims to challenge players while
simultaneously encouraging unusual characters and play styles that you might
not normally consider.</p>

<p>Milestones from CSDC games will be announced in the IRC channel
<code>##csdc</code> on <a href="http://freenode.net">freenode</a>. 
It's a great place to hang out if you want to live spectate ongoing games or
talk with other people about the competition.</p>

<h2>Competition Format</h2>

<ul>
<li>Each challenge consists of playing a randomly chosen Crawl combo.</li>
<li>You get <em>one</em>  attempt to play each combo.</li>
<li>The goal is to advance as far as possible (and win!) in each game, scoring
points by reaching various in-game milestones.</li>
<li>Details on rules and scoring are available on the <a
href="rules.html">rules page</a>.</li>
</ul>

<h2>Schedule</h2>

{}

<h2>Sign Up</h2>

<p>In order to sign up, set the first line of your 0.22 rcfile to</p> <pre
id="rc"># csdc</pre><p>on <a
href="https://crawl.develz.org/play.htm">any of the official online servers</a>
before the start of the first week. Your name will appear in the standings once
you've done this correctly.</p>

<h2>Credits</h2>

<p>Original CSDC rules and organization by <a
href="http://crawl.akrasiac.org/scoring/players/walkerboh.html">WalkerBoh</a>.
Postquell IRC support by <a
href="http://crawl.akrasiac.org/scoring/players/kramin.html">Kramin</a>. Dungeon
Crawl Stone Soup by the <a
href="https://github.com/crawl/crawl/blob/master/crawl-ref/CREDITS.txt">Stone
Soup Team</a>. Thank you to all the players who made runs in the beta. I am your host, <a
href="http://crawl.akrasiac.org/scoring/players/ebering.html">ebering</a>."""

    wklist = "<ul id=schedule>"
    for wk in csdc.weeks:
        wklist += '<li><span class=label>{}:</span> {} to {}'.format(description(wk,True),
                wk.start.strftime(DATEFMT),
                wk.end.strftime(DATEFMT))
    wklist += "</ul>"

    return page( static = True, content = pagestr.format(wklist))

def rulespage():
    pagestr ="""
    <ol>
<li>Each challenge consists of playing a randomly chosen Crawl race/class
combo (e.g. MiBe). The combo for each week of the competition will be announced
at 00:00 UTC on the Thursday starting that week. All players have one week to
finish a game using that combo. Only milestones recorded during the week will
count for scoring.</li>
<li>Your first {} game started on an official server during the week will count
for scoring. This is the only allowed attempt, subject to rule 3 below.</li>
<li>One redo per week is allowed if player XL < 5 (i.e., no redo once you hit
XL 5). The highest CSDC score of the two games is counted towards your score.</li>
<li>Each challenge has an optional bonus challenge in addition to the
race/class combo. Each bonus will have two tiers; the second tier is more
difficult and worth more points.</li>
<li>Each challenge includes a list of gods. A bonus point can be earned upon
reaching ****** piety (or on worship with Gozag or Xom) with one of the listed
gods (but only if it is the first god worshipped that game, and you don't
abandon or get excommunicated later). If the combo for the week is a zealot
background or demigod, no god points are available.</li>
<li>The season consists of 7 challenges total (i.e., 7 different combos). Each
race and background will be selected at most once during the competition.</li>
<li>The final rankings will be tallied at the end of week 7 and represent the
final outcome. The player with the highest CSDC score is the champion.</li>
<li>Tiebreakers are (in order): number of weekly bonus points, highest in-game
score.</li>
</ol>

<h2>Scoring</h2>

<p>Scoring is divided into two parts, weekly points assigned to each game
played, and one-time points awarded once per season regardless of how many
games achieve them.</p>

<table class="info"><tr class="head"><th>Weekly points (can be earned each
week)</th><th></th></tr>
<tr><td class="name">Kill a unique:</td><td class="pt">1</td></tr>
<tr><td class="name">Enter a multi-level branch of the dungeon:</td><td class="pt">1</td></tr>
<tr><td class="name">Reach the end of a multi-level branch (including D):</td><td class="pt">1</td></tr>
<tr><td class="name">Champion a listed god:</td><td class="pt">1</td></tr>
<tr><td class="name">Collect a rune:</td><td class="pt">1</td></tr>
<tr><td class="name">Collect 3 or more runes:</td><td class="pt">1</td></tr>
<tr><td class="name">Win:</td><td class="pt">1</td></tr>
<tr><td class="name">Complete a Tier I bonus:</td><td class="pt">1</td></tr>
<tr><td class="name">Complete a Tier II bonus:</td><td class="pt">2</td></tr>
<tr class="head" id="onetime"><th>One-time points (earned once in the
competition)</th><th></th></tr>
<tr><td class="name">Win a game with 15 runes:</td><td class="pt">3</td></tr>
<tr><td class="name">Win a game in under 50,000 turns:</td><td class="pt">3</td></tr>
<tr><td class="name">Clear a Zigguraut:</td><td class="pt">3</td></tr>
<tr><td class="name">Enter Zot at XL 20 or lower:</td><td class="pt">6</td></tr>
<tr><td class="name">Win a game without entering lair:</td><td class="pt">6</td></tr>
<tr><td class="name">Get a rune without using potions or scrolls:</td><td class="pt">6</td></tr>
</table>

<p class="notes"> It will not always be the case that earning a
Tier II bonus implies that you have earned a Tier I bonus, these points can be
awarded separately. Unless specified, a bonus or one time point does not
require you to win to earn the point.</p>

<h2>Fair Crawling</h2>

<p>All contestants will compete with commonly recognized principles of
sportsmanship and fair play. Failure to do so will result in disqualification
without recourse and your entry will be deleted from the scoring database. If
you are uncertain if something is "fair play" then ask for clarification before
doing it. Ignorance and negligence are not excuses for poor behavior.</p>

<p>All contestants acknowledge an obligation not to commit misconduct in
relation to their participation.  Misconduct is any act that is a breach of
good manners, a breach of good sportsmanship, or unethical behavior. Misconduct
will also result in disqualification without recourse and your entry will be
deleted from the scoring database. Sever misconduct will lead to exclusion from
future CSDC events.</p>
"""
    return page(static=True, subhead="Rules", content = pagestr)


def page(**kwargs):
    """static, title, subhead, content"""
    return """<html>{}<body>{}<div id="content">{}</div>
    <div id="bottomtext">{}</div></body></html>""".format(
            head(kwargs["static"],kwargs.get("title",kwargs.get("subhead",""))),
            logoblock(kwargs.get("subhead","")),
            kwargs["content"],
            mainmenu() + kwargs.get("menu", wkmenu(None)) + (updated() if not kwargs["static"] else
                ""))
