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
        if (wk is None or 
            w.number != wk.number
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

    if url:
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
        sp += '<th>Score</th></tr>'
        for p in csdc.overview().with_session(s).all():
            sp += '<tr>'
            sp += '<td class="name">{}</td>'.format(p.CsdcContestant.player.name)
            sp += ('<td class="pt">{}</td>' * len(csdc.weeks)).format(
                    *[ _ifnone(getattr(p, "wk" + wk.number), "") for wk in csdc.weeks])
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
            #for now. want to have the wk info up top or at least links
            content = standingstable())

def overviewpage():
    pagestr = """
<p>The Crawl Sudden Death Challenges is a competition that aims to fill a
Crawl niche not currently filled by the biannual version release tournaments.
The idea is for players to compete by trying to do as well as possible in a
game of Crawl with one attempt only; if you die, that challenge is over (thus
"sudden death", though you may - will - also die suddenly). This competition is
a lower time commitment event that aims to challenges players, while
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

<p>In order to sign up, place <code># csdc</code> as the first line of your
0.22 rcfile on <a href="https://crawl.develz.org/play.htm">any of the official
online servers</a> before the start of the first week. Your name will appear in
the standings once you've done this correctly.</p>

<h2>Credits</h2>

<p>Original CSDC rules and organization by <a
href="http://crawl.akrasiac.org/scoring/players/walkerboh.html">WalkerBoh</a>.
Postquell IRC support by <a
href="http://crawl.akrasiac.org/scoring/players/kramin.html">Kramin</a>. Dungeon
Crawl Stone Soup by the <a
href="https://github.com/crawl/crawl/blob/master/crawl-ref/CREDITS.txt">Sonte
Soup Team</a>. I am your host, <a
href="http://crawl.akrasiac.org/scoring/players/ebering.html">ebering</a>.""".format("lel")
    return page( static = True, content = pagestr)


def page(**kwargs):
    """static, title, subhead, content"""
    return """<html>{}<body>{}<div id="content">{}</div>
    <div id="bottomtext">{}</div></body></html>""".format(
            head(kwargs["static"],kwargs.get("title",kwargs.get("subhead",""))),
            logoblock(kwargs.get("subhead","")),
            kwargs["content"],
            mainmenu() + kwargs.get("menu", wkmenu(None)) + (updated() if not kwargs["static"] else
                ""))
