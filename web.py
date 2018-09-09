import datetime
from orm import get_session
from modelutils import morgue_url
import csdc

def updated():
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M %Z")
    return '<div id="updatetime"><span class="label">Updated: </span>{}</div>'.format(now)

def head(static, title):
    refresh = '<meta http-equiv="refresh" content="300">' if not static else ""
    return """<head><title>{0}</title>
    <link rel="stylesheet" href="static/score.css">
    {1}</head>""".format(title, refresh)

def logoblock(subhead):
    sh = "<h2>{}</h2>".format(subhead) if subhead != None else ""
    return """<div id="title">
    <img id="logo" src="static/logo.png">
    <h1 id="sdc">sudden death challenges</h1>
    {}</div>""".format(sh)

def wkinfo(wk):
    sp = ""
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


def scoretable(wk, div):
    sp = ""
    sp += ("""<table><tr class="head">
    <th>Player</th>
    <th>Unique Kill</th>
    <th>Branch Enter</th>
    <th>Branch End</th>
    <th>Champion God</th>
    <th>Collect 1 Rune</th>
    <th>Collect 3 Runes</th>
    <th>Win</th>
    <th>Bonus I</th>
    <th>Bonus II</th>
    <th>Total</th>
    </tr>""")

    with get_session() as s:
        for g in wk.scorecard().with_session(s).all():
            sp += ('<tr class="{}">'.format(
                "won" if g.Game.won else
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


def scorepage(wk):
    combo = "{}{}".format(wk.species.short, wk.background.short)
    titlestr = "Week {}&mdash;{}".format(wk.number, combo)
    return page( static=False, title = "CSDC " + titlestr, subhead = titlestr,
            content = wkinfo(wk) + 
            " ".join([ scoretable(wk, d) for d in csdc.divisions]))


def page(**kwargs):
    """static, title, subhead, content"""
    return '<html>{}<body>{}<div id="content">{}</div>{}</body></html>'.format(
            head(kwargs["static"],kwargs["title"]),
            logoblock(kwargs.get("subhead",None)),
            kwargs["content"],
            updated() if not kwargs["static"] else None)

