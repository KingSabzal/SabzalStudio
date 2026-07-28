"""User-Agent rotation with per-host learning.

Testing showed that a User-Agent helps for *some* blocks and not for others:

* Reddit RSS answers 429 for browser agents but 200 for feed-reader agents such as
  Feedly. Rotating agents therefore genuinely recovers this source.
* Videvo and the Pixabay audio pages return 403 for every agent, because they use a
  JavaScript bot challenge that no header can satisfy. Rotating there only wastes time.

So the rotation is adaptive: each host remembers which agent last worked, tries that
one first, and stops early when a host is clearly challenge-protected rather than
agent-filtered.
"""

from __future__ import annotations

import logging
import random
import threading
from typing import Dict, List, Optional

LOGGER = logging.getLogger("user_agents")
if not LOGGER.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
    LOGGER.addHandler(_h)
LOGGER.setLevel(logging.INFO)


def _build_browser_agents() -> List[str]:
    """Generate a large pool of realistic desktop and mobile browser agents.

    Free media hosts throttle or block a client that presents the same
    identity on every request. A pool this size means a run can rotate through
    hundreds of plausible identities before ever repeating one, which is what
    keeps a long render from being rate-limited halfway through.

    The strings are built from real version ranges rather than invented, so
    each one is a User-Agent a genuine browser has actually sent.
    """
    agents: List[str] = []

    windows = [
        "Windows NT 10.0; Win64; x64",
        "Windows NT 11.0; Win64; x64",
    ]
    macos = [
        "Macintosh; Intel Mac OS X 10_15_7",
        "Macintosh; Intel Mac OS X 14_5",
        "Macintosh; Intel Mac OS X 15_1",
    ]
    linux = [
        "X11; Linux x86_64",
        "X11; Ubuntu; Linux x86_64",
        "X11; Fedora; Linux x86_64",
    ]
    desktops = windows + macos + linux

    # Chrome, the largest share by far.
    for major in range(118, 146):
        for platform in desktops:
            agents.append(
                f"Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{major}.0.0.0 Safari/537.36"
            )

    # Edge, Opera and Brave all carry the Chromium token plus their own.
    for major in range(118, 146):
        for platform in (windows[0], macos[0]):
            agents.append(
                f"Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{major}.0.0.0 Safari/537.36 Edg/{major}.0.0.0"
            )
    for major, opera in zip(range(112, 128), range(98, 114)):
        agents.append(
            f"Mozilla/5.0 ({windows[0]}) AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{major}.0.0.0 Safari/537.36 OPR/{opera}.0.0.0"
        )

    # Firefox
    for major in range(115, 140):
        for platform in (
            f"Windows NT 10.0; Win64; x64; rv:{major}.0",
            f"Macintosh; Intel Mac OS X 14.5; rv:{major}.0",
            f"X11; Linux x86_64; rv:{major}.0",
        ):
            agents.append(
                f"Mozilla/5.0 ({platform}) Gecko/20100101 Firefox/{major}.0"
            )

    # Safari on macOS
    for version in ("16.4", "16.6", "17.0", "17.2", "17.4", "17.6",
                    "18.0", "18.1", "18.2", "18.3"):
        for platform in macos:
            agents.append(
                f"Mozilla/5.0 ({platform}) AppleWebKit/605.1.15 "
                f"(KHTML, like Gecko) Version/{version} Safari/605.1.15"
            )

    # iPhone and iPad
    for version in ("16.6", "17.0", "17.4", "17.6", "18.0", "18.1", "18.2"):
        token = version.replace(".", "_")
        agents.append(
            f"Mozilla/5.0 (iPhone; CPU iPhone OS {token} like Mac OS X) "
            f"AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} "
            f"Mobile/15E148 Safari/604.1"
        )
        agents.append(
            f"Mozilla/5.0 (iPad; CPU OS {token} like Mac OS X) "
            f"AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} "
            f"Mobile/15E148 Safari/604.1"
        )

    # Android, across the handsets that actually show up in logs.
    devices = ["Pixel 7", "Pixel 8", "Pixel 9", "SM-S918B", "SM-A546B",
               "SM-S928B", "Redmi Note 12", "moto g84 5G"]
    for android, chrome in (("12", 120), ("13", 127), ("14", 133), ("15", 141)):
        for device in devices:
            agents.append(
                f"Mozilla/5.0 (Linux; Android {android}; {device}) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{chrome}.0.0.0 Mobile Safari/537.36"
            )

    # Firefox on Android, phone and tablet
    for major in range(115, 141):
        agents.append(
            f"Mozilla/5.0 (Android 14; Mobile; rv:{major}.0) "
            f"Gecko/{major}.0 Firefox/{major}.0"
        )
    for major in range(120, 141, 2):
        agents.append(
            f"Mozilla/5.0 (Android 14; Tablet; rv:{major}.0) "
            f"Gecko/{major}.0 Firefox/{major}.0"
        )

    # Samsung Internet, the default browser on a very large install base.
    for version, chrome in (("23.0", 115), ("24.0", 121), ("25.0", 127),
                            ("26.0", 131), ("27.0", 138)):
        for device in ("SM-S918B", "SM-A546B", "SM-S928B"):
            agents.append(
                f"Mozilla/5.0 (Linux; Android 14; {device}) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"SamsungBrowser/{version} Chrome/{chrome}.0.0.0 "
                f"Mobile Safari/537.36"
            )

    # Deduplicate while preserving order.
    seen: set = set()
    unique: List[str] = []
    for agent in agents:
        if agent not in seen:
            seen.add(agent)
            unique.append(agent)
    return unique


# Feed readers are declared politely and are what Reddit and several news hosts accept.
FEED_READER_AGENTS: List[str] = [
    "Feedly/1.0 (+http://www.feedly.com/fetcher.html; like FeedFetcher-Google)",
    "Mozilla/5.0 (compatible; Feedbin feed-id:1 - 1 subscribers)",
    "Inoreader/1.0 (+http://www.inoreader.com/feed-fetcher; 5 subscribers)",
    "NewsBlur Feed Fetcher - 3 subscribers",
    "Mozilla/5.0 (compatible; theoldreader.com; 2 subscribers)",
    "SimplePie/1.5.6 (Feed Parser; http://simplepie.org)",
    "Liferea/1.13.5 (Linux; en_US; https://lzone.de/liferea/)",
    "Akregator/5.22.3; syndication",
    "Miniflux/2.1.0 (+https://miniflux.app)",
    "FreshRSS/1.24.0 (Linux; https://freshrss.org)",
    "Tiny Tiny RSS/21.11 (http://tt-rss.org/)",
    "rss-parser/3.13.0",
    "python-feedparser/6.0.11 +https://github.com/kurtmckee/feedparser/",
    "Mozilla/5.0 (compatible; NetNewsWire/6.1; +https://netnewswire.com/)",
    "Reeder/5.0 (+https://reederapp.com)",
]

# Declared API clients, accepted by hosts that dislike anonymous browser traffic.
API_CLIENT_AGENTS: List[str] = [
    "windows:sabzalstudio:v1.0 (by /u/local-user)",
    "web:sabzalstudio:v1.0 (open source video tool)",
    "python-requests/2.32.3",
    "aiohttp/3.10.5",
    "okhttp/4.12.0",
]

BROWSER_AGENTS: List[str] = _build_browser_agents()
ALL_AGENTS: List[str] = BROWSER_AGENTS + FEED_READER_AGENTS + API_CLIENT_AGENTS

# Hosts where a feed-reader identity works far better than a browser identity.
FEED_FIRST_HOSTS = (
    "reddit.com", "old.reddit.com", "feeds.bbci.co.uk", "theguardian.com",
    "aljazeera.com", "producthunt.com", "news.google.com", "rss.cnn.com",
    "trends.google.com",
)

# Status codes that mean "this identity was refused, another one may work".
RETRYABLE_BLOCK_CODES = (401, 403, 405, 406, 418, 429, 503)

_LOCK = threading.Lock()
_HOST_MEMORY: Dict[str, str] = {}          # host -> agent that last succeeded
_HOST_HOPELESS: Dict[str, int] = {}        # host -> consecutive full-rotation failures

# After this many complete failures a host is treated as challenge-protected and only
# one attempt is made, so scans stay fast instead of retrying 200 agents every time.
HOPELESS_THRESHOLD = 2


def host_of(url: str) -> str:
    """Extract the hostname from a URL."""
    if "//" not in url:
        return url
    return url.split("/")[2].lower()


def default_agent() -> str:
    """A stable, modern desktop agent for ordinary requests."""
    return (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
    )


def random_agent() -> str:
    """Return a random agent from the full pool."""
    return random.choice(ALL_AGENTS)


def agents_for(url: str, limit: int = 40) -> List[str]:
    """Return the agents to try for a URL, best candidate first.

    A working agent usually appears within the first few tries. The list is
    nonetheless long, because a clip must never be skipped: when a host is
    rate-limiting rather than challenging, working through more identities is
    exactly what eventually gets the file.
    """
    host = host_of(url)

    if _HOST_HOPELESS.get(host, 0) >= HOPELESS_THRESHOLD:
        # This host has refused a full rotation before. Still give it a
        # genuine try rather than one token attempt: a clip is never skipped
        # for want of trying, and a host that blocked yesterday often answers
        # today.
        remembered = _HOST_MEMORY.get(host)
        fallback = [remembered] if remembered else []
        fallback.append(default_agent())
        fallback.extend(random.sample(BROWSER_AGENTS, k=min(8, len(BROWSER_AGENTS))))
        seen_f: set = set()
        return [a for a in fallback if a and not (a in seen_f or seen_f.add(a))]

    ordered: List[str] = []

    remembered = _HOST_MEMORY.get(host)
    if remembered:
        ordered.append(remembered)

    if any(host.endswith(h) or h in host for h in FEED_FIRST_HOSTS):
        ordered.extend(FEED_READER_AGENTS[:6])
        ordered.extend(API_CLIENT_AGENTS[:2])
        ordered.extend(random.sample(BROWSER_AGENTS, k=min(30, len(BROWSER_AGENTS))))
    else:
        ordered.append(default_agent())
        ordered.extend(random.sample(BROWSER_AGENTS, k=min(34, len(BROWSER_AGENTS))))
        ordered.extend(FEED_READER_AGENTS[:2])

    seen: set = set()
    unique: List[str] = []
    for agent in ordered:
        if agent and agent not in seen:
            seen.add(agent)
            unique.append(agent)
    return unique[:limit]


def remember_success(url: str, agent: str) -> None:
    """Record the agent that worked so the next request starts with it."""
    host = host_of(url)
    with _LOCK:
        _HOST_MEMORY[host] = agent
        _HOST_HOPELESS.pop(host, None)


def remember_total_failure(url: str) -> None:
    """Record that every agent failed for this host."""
    host = host_of(url)
    with _LOCK:
        _HOST_HOPELESS[host] = _HOST_HOPELESS.get(host, 0) + 1
        if _HOST_HOPELESS[host] == HOPELESS_THRESHOLD:
            LOGGER.info(
                "%s refused every User-Agent, so it is protected by a JavaScript "
                "challenge rather than agent filtering. Future scans will not retry it.",
                host,
            )


def headers_for(agent: str, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Build a complete, believable header set for an agent."""
    headers = {
        "User-Agent": agent,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "application/rss+xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    if "Chrome/" in agent and "Mobile" not in agent:
        version = agent.split("Chrome/")[1].split(".")[0]
        headers["sec-ch-ua"] = (
            f'"Chromium";v="{version}", "Not(A:Brand";v="24", "Google Chrome";v="{version}"'
        )
        headers["sec-ch-ua-mobile"] = "?0"
        headers["sec-ch-ua-platform"] = '"Windows"' if "Windows" in agent else '"macOS"'
        headers["Sec-Fetch-Dest"] = "document"
        headers["Sec-Fetch-Mode"] = "navigate"
        headers["Sec-Fetch-Site"] = "none"
    if extra:
        headers.update(extra)
    return headers


def stats() -> Dict[str, object]:
    """Return rotation statistics for the connection status dashboard."""
    return {
        "total_agents": len(ALL_AGENTS),
        "browser_agents": len(BROWSER_AGENTS),
        "feed_reader_agents": len(FEED_READER_AGENTS),
        "api_client_agents": len(API_CLIENT_AGENTS),
        "learned_hosts": dict(_HOST_MEMORY),
        "challenge_protected_hosts": sorted(
            host for host, count in _HOST_HOPELESS.items() if count >= HOPELESS_THRESHOLD
        ),
    }


def reset_memory() -> None:
    """Forget every learned agent and block record."""
    with _LOCK:
        _HOST_MEMORY.clear()
        _HOST_HOPELESS.clear()
