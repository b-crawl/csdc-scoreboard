"""Utility functions for the model."""

import re
import logging
import datetime
from typing import Optional

import orm
import constants

def logline_to_dict(logline: str) -> dict:
    """Convert a logline into a sanitized dict"""
    data = {}
    pairs = re.split('(?<!:):(?!:)', logline.strip())
    for p in pairs:
        p = p.replace('::',':')
        keyval = p.split('=')
        try:
            data[keyval[0]] = keyval[1]
        except IndexError as e:
            logging.error('error "{}" in keyval "{}", logline "{}"'.format(e,keyval,logline))
    data["v"] = re.match(r"(0.\d+)", game["v"]).group()
    if "god" not in data:
        data["god"] = "GOD_NO_GOD"

    data["god"] = const.GOD_NAME_FIXUPS.get(data["god"],data["god"])
    data["ktyp"] = const.KTYP_FIXUPS.get(data["ktyp"], data["ktyp"])
    if "end" in data:
        data["verb"] = "death.final"
        data["milestone"] = data["tmsg"]

    return data

def crawl_date_to_datetime(d: str) -> datetime.datetime:
    """Converts a crawl date string to a datetime object.

    Note: crawl dates use a 0-indexed month... I think you can blame struct_tm
    for this.
    """
    # Increment the month by one
    d = d[:4] + "%02d" % (int(d[4:6]) + 1) + d[6:]
    return datetime.datetime(
        year=int(d[:4]),
        month=int(d[4:6]),
        day=int(d[6:8]),
        hour=int(d[8:10]),
        minute=int(d[10:12]),
        second=int(d[12:14]),
    )


def _morgue_prefix(src: str, version: str) -> Optional[str]:
    src = src.lower()
    if src == "cao":
        prefix = "http://crawl.akrasiac.org/rawdata"
    elif src == "cdo":
        prefix = "http://crawl.develz.org/morgues"
        prefix += "/" + version_url(version)
    elif src == "cszo":
        prefix = "http://dobrazupa.org/morgue"
    elif src == "cue" or src == "clan":
        prefix = "http://underhound.eu:81/crawl/morgue"
    elif src == "cbro":
        prefix = "http://crawl.berotato.org/crawl/morgue"
    elif src == "cxc":
        prefix = "http://crawl.xtahua.com/crawl/morgue"
    elif src == "lld":
        prefix = "http://lazy-life.ddo.jp:8080/morgue"
        prefix += "/" + version_url(version)
    elif src == "cpo":
        prefix = "https://crawl.project357.org/morgue"
    elif src == "cjr":
        prefix = "http://www.jorgrun.rocks/morgue"
    elif src == "cwz":
        prefix = "http://webzook.net/soup/morgue/"
        prefix += "/" + version_url(version)
    elif src in ("ckr", "csn", "rhf"):
        return None
    else:
        raise ValueError("No prefix for %s" % src)
    return prefix


def morgue_url(game: orm.Game) -> Optional[str]:
    """Generates a morgue URL from a game."""
    src = game.account.server.name
    prefix = _morgue_prefix(src, game.version.v)
    if not prefix:
        return None

    name = game.account.name
    timestamp = game.end.strftime("%Y%m%d-%H%M%S")
    return "%s/%s/morgue-%s-%s.txt" % (prefix, name, name, timestamp)


def version_url(version: str) -> str:
    """Cleans up version strings for use in morgue URLs."""
    if version[-2:] == "a0":
        return "trunk"
    if len(version) > 4:
        for i in range(len(version)):
            if version[-(i + 1)] == ".":
                return version[: -(i + 1)]
    return version
