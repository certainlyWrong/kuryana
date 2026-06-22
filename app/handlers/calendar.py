import asyncio
import logging
import re
from typing import Any, Dict, List, Tuple

import primp
from bs4 import BeautifulSoup
from camoufox.async_api import AsyncCamoufox

from app import MYDRAMALIST_WEBSITE

logger = logging.getLogger(__name__)


async def _get_calendar_html(url: str) -> Tuple[int, str]:
    """Two-layer HTML fetcher for MDL calendar pages.

    Layer 1 — primp: fast TLS-impersonating GET. Calendar pages are
               server-rendered, so no JS is needed on the happy path.
    Layer 2 — camoufox: headless Firefox navigation when primp is blocked
               by a Cloudflare challenge.
    """

    def _primp_get() -> primp.Response:
        client = primp.Client(impersonate="chrome", impersonate_os="linux")
        return client.get(url)

    r = await asyncio.to_thread(_primp_get)
    if 200 <= r.status_code < 300 and "episode-calendar-results" in r.text:
        return r.status_code, r.text

    logger.warning(
        "primp returned %s for %s — falling back to camoufox", r.status_code, url
    )

    async with AsyncCamoufox(headless=True) as browser:
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        html = await page.content()

    return 200, html


class FetchSeasonal:
    @classmethod
    async def scrape(cls, url: str) -> Tuple[int, List[Dict[str, Any]]]:
        status, html = await _get_calendar_html(url)
        return status, cls._parse(html)

    @staticmethod
    def _parse(html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        results_div = soup.find(id="episode-calendar-results")
        if not results_div:
            return []

        items: List[Dict[str, Any]] = []
        current_category = ""

        for row in results_div.find_all("div", class_="row", recursive=False):
            for child in row.children:
                if not hasattr(child, "get"):
                    continue
                classes = child.get("class") or []

                if "col-md-12" in classes:
                    h2 = child.find("h2")
                    if h2:
                        current_category = h2.get_text(strip=True)

                elif "col-md-6" in classes:
                    card = child.find("div", class_="episode-card-large")
                    if not card:
                        continue

                    cover = card.find("div", class_="cover-large")
                    ep_info = card.find("div", class_="episode-info")
                    manage_btn = card.find("button", attrs={"data-id": True})

                    link_el = cover.find("a") if cover else None
                    img_el = cover.find("img") if cover else None
                    title_el = cover.find("div", class_="title") if cover else None
                    ctype_el = (
                        cover.find("div", class_="content-type") if cover else None
                    )
                    release_el = (
                        ep_info.find("div", class_="release-time") if ep_info else None
                    )
                    synopsis_el = (
                        ep_info.find("p", class_="synopsis") if ep_info else None
                    )
                    genre_els = (
                        ep_info.find_all("div", class_="genre") if ep_info else []
                    )

                    href = (link_el.get("href") or "") if link_el else ""
                    items.append(
                        {
                            "id": manage_btn.get("data-id", "") if manage_btn else "",
                            "title": title_el.get_text(strip=True) if title_el else "",
                            "slug": href.strip("/"),
                            "url": f"{MYDRAMALIST_WEBSITE.rstrip('/')}{href}"
                            if href
                            else "",
                            "cover": img_el.get("src", "") if img_el else "",
                            "content_type": ctype_el.get_text(strip=True)
                            if ctype_el
                            else "",
                            "release_date": release_el.get_text(strip=True)
                            if release_el
                            else "",
                            "synopsis": synopsis_el.get_text(strip=True)
                            if synopsis_el
                            else "",
                            "genres": [g.get_text(strip=True) for g in genre_els],
                            "category": current_category,
                        }
                    )

        return items


class FetchSchedule:
    @classmethod
    async def scrape(cls, url: str) -> Tuple[int, Dict[str, Any]]:
        status, html = await _get_calendar_html(url)
        return status, cls._parse(html)

    @staticmethod
    def _parse(html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")
        results_div = soup.find(id="episode-calendar-results")
        if not results_div:
            return {"days": []}

        days = []
        for day_div in results_div.find_all("div", id=re.compile(r"^d\d+$")):
            date_el = day_div.find("small")
            day_el = day_div.find("h2")

            items = []
            for card in day_div.find_all("div", class_="el-card"):
                cover_sm = card.find("div", class_="cover-sm")
                ep_card = card.find("div", class_="episode-card-sm")
                if not ep_card:
                    continue

                img_el = cover_sm.find("img") if cover_sm else None
                drama_link = cover_sm.find("a") if cover_sm else None
                manage_btn = card.find("button", attrs={"data-id": True})

                drama_href = (drama_link.get("href") or "") if drama_link else ""

                release_div = ep_card.find("div", class_="release-time")
                if release_div:
                    for icon in release_div.find_all("i"):
                        icon.decompose()
                display_time = release_div.get_text(strip=True) if release_div else ""

                popover = ep_card.find("div", class_="calendar-popover-content")
                timezone = ""
                episode_entries = []
                if popover:
                    tz_el = popover.find("div", class_="calendar-popover-title")
                    timezone = tz_el.get_text(strip=True) if tz_el else ""
                    for line in popover.find_all("div", class_="calendar-popover-line"):
                        ep_link = line.find("a")
                        time_bold = line.find("b")
                        utc_span = line.find("span", class_="text-muted")
                        episode_entries.append(
                            {
                                "url": f"{MYDRAMALIST_WEBSITE.rstrip('/')}{ep_link.get('href', '')}"
                                if ep_link
                                else "",
                                "number": ep_link.get_text(strip=True)
                                if ep_link
                                else "",
                                "air_time": time_bold.get_text(strip=True)
                                if time_bold
                                else "",
                                "utc_time": utc_span.get_text(strip=True).strip("()")
                                if utc_span
                                else None,
                            }
                        )

                items.append(
                    {
                        "id": manage_btn.get("data-id", "") if manage_btn else "",
                        "title": img_el.get("alt", "") if img_el else "",
                        "slug": drama_href.strip("/"),
                        "drama_url": f"{MYDRAMALIST_WEBSITE.rstrip('/')}{drama_href}"
                        if drama_href
                        else "",
                        "thumbnail": img_el.get("src", "") if img_el else "",
                        "display_time": display_time,
                        "timezone": timezone,
                        "episodes": episode_entries,
                    }
                )

            days.append(
                {
                    "date": date_el.get_text(strip=True) if date_el else "",
                    "day_name": day_el.get_text(strip=True) if day_el else "",
                    "items": items,
                }
            )

        return {"days": days}
