import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Type, TypeVar, Union
from urllib.parse import urljoin

import primp
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag
from camoufox.async_api import AsyncCamoufox

from app import MYDRAMALIST_WEBSITE

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="Parser")


ScrapeTypes = {
    "search": urljoin(MYDRAMALIST_WEBSITE, "search?q="),
    "page": MYDRAMALIST_WEBSITE,
}


class Parser:
    """Main Parser"""

    headers: Dict[str, str] = {
        "Referer": MYDRAMALIST_WEBSITE,
    }

    def __init__(
        self, soup: BeautifulSoup | None, query: str, code: int, ok: bool
    ) -> None:
        self.soup = soup
        self.query = query
        self.status_code = code
        self.ok = ok

    @classmethod
    async def scrape(cls: Type[T], query: str, t: str) -> T:
        if t not in ScrapeTypes.keys():
            raise Exception("Invalid type")

        # parse url
        url = urljoin(ScrapeTypes[t], query)
        if t == "search":
            url = ScrapeTypes[t] + query

        ok = True
        code = 500  # default to 500, internal server error
        soup = None

        try:

            def _primp_get() -> primp.Response:
                client = primp.Client(impersonate="chrome", impersonate_os="linux")
                return client.get(url)

            resp = await asyncio.to_thread(_primp_get)
            code = resp.status_code

            if 200 <= code < 300 and "app-body" in resp.text:
                soup = BeautifulSoup(resp.text, "html.parser")
                ok = True
            else:
                logger.warning(
                    "primp returned %s for %s — falling back to camoufox", code, url
                )
                async with AsyncCamoufox(headless=True) as browser:
                    page = await browser.new_page()
                    await page.goto(url, wait_until="domcontentloaded")
                    html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                code = 200
                ok = True

        except Exception as exc:
            logger.error("scrape failed for %s: %s", url, exc, exc_info=True)
            ok = False

        return cls(soup, query, code, ok)

    # get page err, if possible
    def res_get_err(self) -> Dict[str, Any]:
        if self.soup is None:
            return {}

        container = self.soup.find("div", class_="app-body")

        # if the page was not found,
        # or there was a problem with scraping,
        # try to get the error and return the err message
        err: Dict[str, Any] = {}

        if container is None:
            return err

        try:
            box_body = container.find("div", class_="box-body")
            if box_body is not None:
                err["code"] = self.status_code
                err["error"] = True
                h1_elem = box_body.find("h1")
                p_elem = box_body.find("p")
                err["description"] = {
                    "title": h1_elem.get_text().strip() if h1_elem else "",
                    "info": p_elem.get_text().strip() if p_elem else "",
                }

        except Exception as exc:
            logger.debug("res_get_err parsing failed for %s: %s", self.query, exc)

        return err


class BaseSearch(Parser):
    def __init__(self, soup: BeautifulSoup, query: str, code: int, ok: bool) -> None:
        super().__init__(soup, query, code, ok)

        self.search_results: Dict[str, List] = {}  # search

    def search(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "results": self.search_results,
            "scrape_date": datetime.now(timezone.utc),
        }


class BaseFetch(Parser):
    def __init__(self, soup: BeautifulSoup, query: str, code: int, ok: bool) -> None:
        super().__init__(soup, query, code, ok)

        self.info: Dict[str, Any] = {
            "link": urljoin(MYDRAMALIST_WEBSITE, query)  # add `link` first data
        }  # fetch

        self._img_attrs = ["src", "data-cfsrc", "data-src"]

    def fetch(self) -> Dict[str, Any]:
        return {
            "slug_query": self.query,
            "data": self.info,
            "scrape_date": datetime.now(timezone.utc),
        }

    def _get(self) -> None:
        """handler for parser, override in subclass"""

    def _get_poster(self, container: Union[Tag, NavigableString]) -> Union[str, Any]:
        poster = container.find("img")

        if poster is None:
            return ""

        for i in self._img_attrs:
            if poster.has_attr(i):  # type: ignore
                return poster[i]  # type: ignore

        # blank if none
        return ""

    # get the drama details <= statistics section is added in here
    def _get_details(self, classname: str) -> None:
        if self.soup is None:
            return

        details = self.soup.find("ul", class_=classname)
        if details is None:
            return

        try:
            self.info["details"] = {}
            all_details = details.find_all("li")

            for i in all_details:
                # get each li from <ul>
                b_tag = i.find("b")
                if b_tag is None:
                    continue
                _title = b_tag.text.strip()

                # append each to sub object
                self.info["details"][
                    _title.replace(":", "").replace(" ", "_").lower()
                ] = i.text.replace(
                    _title + " ", ""
                ).strip()  # remove leading and trailing white spaces

        except Exception as exc:
            logger.debug("_get_details failed for %s: %s", self.query, exc)

    # rating handler, (since it could be N/A which is not convertable to float)
    def _handle_rating(
        self, component: Union[Tag, NavigableString, None]
    ) -> Union[str, float, Any]:
        if component is None:
            return ""
        try:
            return float(component.text)
        except Exception:
            pass

        return component.text
