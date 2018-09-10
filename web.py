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


def description(wk, url):
    s = ""

    if wk.start > datetime.datetime.now():
        s += "Week {0}"
    else:
        s += "Week {0}&mdash;{1}{2}"

    if url:
        s = '<a href="{0}.html">' + s + '</a>'

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


def overviewtable():
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
            " ".join([ scoretable(wk, d) for d in csdc.divisions]))


def overviewpage():
    return page( static=False,
            subhead = "Scoring Overview",
            #for now. want to have the wk info up top or at least links
            content = overviewtable())


def page(**kwargs):
    """static, title, subhead, content"""
    return '<html>{}<body>{}<div id="content">{}</div>{}</body></html>'.format(
            head(kwargs["static"],kwargs.get("title",kwargs.get("subhead",None))),
            logoblock(kwargs.get("subhead",None)),
            kwargs["content"],
            updated() if not kwargs["static"] else None)
