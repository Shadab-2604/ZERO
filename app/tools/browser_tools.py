"""
Safe allowlisted browser tools for Zero AI.
Detects Google Chrome on Windows, handles searches with URL encoding,
validates URLs, and executes safely via subprocess without arbitrary shell calls.
"""

import logging
import os
import shutil
import subprocess
import urllib.parse
from app.tools.registry import ActionRegistry, ToolResult

logger = logging.getLogger(__name__)


def find_chrome_executable() -> str | None:
    """
    Locate Google Chrome executable using Windows registry, standard installation directories,
    and system PATH.
    """
    # 1. Check system PATH
    direct = shutil.which("chrome") or shutil.which("google-chrome")
    if direct and os.path.isfile(direct):
        return direct

    # 2. Check Windows Registry
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
        ) as key:
            val, _ = winreg.QueryValueEx(key, "")
            if val and os.path.isfile(val):
                return val
    except Exception:
        pass

    # 3. Check standard Windows filesystem paths
    candidates = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]

    for p in candidates:
        if p and os.path.isfile(p):
            return p

    return None


def open_chrome() -> ToolResult:
    """
    Launch Google Chrome browser or bring existing window to front.
    """
    chrome_path = find_chrome_executable()
    if not chrome_path:
        # Fallback to system default browser
        try:
            import webbrowser
            launched = webbrowser.open("about:blank")
            if launched:
                return ToolResult(
                    success=True,
                    summary="Chrome was not found, so I opened your default system web browser.",
                    detailed_text="**Browser Launched:** Google Chrome executable was not located in standard paths; launched the default system browser (`about:blank`).",
                    data={"browser": "default", "fallback": True},
                )
        except Exception as e:
            logger.error("Failed to launch default browser: %s", e)

        return ToolResult(
            success=False,
            summary="Google Chrome is not installed or could not be found.",
            detailed_text="**Launch Failed:** Google Chrome executable was not detected in standard installation paths (`Program Files`, `Local AppData`).",
            error="Chrome executable not found",
        )

    try:
        # Launch Chrome without shell=True
        proc = subprocess.Popen([chrome_path], shell=False)
        return ToolResult(
            success=True,
            summary="I have opened Google Chrome for you.",
            detailed_text=f"**Browser Action:** Successfully launched Google Chrome.\n- **Executable:** `{chrome_path}`\n- **Process ID:** `{proc.pid}`",
            data={"executable": chrome_path, "pid": proc.pid},
        )
    except Exception as e:
        logger.error("Failed to launch Chrome at %s: %s", chrome_path, e)
        return ToolResult(
            success=False,
            summary=f"Failed to open Google Chrome: {str(e)}",
            detailed_text=f"**Launch Error:** Error executing Chrome at `{chrome_path}`: {str(e)}",
            error=str(e),
        )


def open_browser_search(query: str | None = None) -> ToolResult:
    """
    Open Google Chrome with a URL-encoded Google search query.
    If query is empty, launches Chrome and prompts for the search term.
    """
    query_str = (query or "").strip()

    # If query is missing, open Chrome and ask user what to search for
    if not query_str or query_str.lower() in ("search", "and search", "search for me"):
        chrome_res = open_chrome()
        if chrome_res.success:
            return ToolResult(
                success=True,
                summary="I opened Chrome for you. What would you like to search for?",
                detailed_text="**Browser Action:** Opened Google Chrome. Awaiting your search query. Please specify what you'd like to find.",
                data={"query": None, "state": "AWAITING_QUERY"},
            )
        return chrome_res

    encoded_query = urllib.parse.quote_plus(query_str)
    search_url = f"https://www.google.com/search?q={encoded_query}"

    chrome_path = find_chrome_executable()
    if chrome_path:
        try:
            proc = subprocess.Popen([chrome_path, search_url], shell=False)
            return ToolResult(
                success=True,
                summary=f"Opened Chrome searching for '{query_str}'.",
                detailed_text=(
                    f"**Browser Search Launched:**\n"
                    f"- **Query:** `{query_str}`\n"
                    f"- **Target URL:** [{search_url}]({search_url})\n"
                    f"- **Executable:** `{chrome_path}` (PID: {proc.pid})\n\n"
                    f"*Note: Search request was dispatched to Google via your local browser.*"
                ),
                data={"query": query_str, "url": search_url, "pid": proc.pid},
            )
        except Exception as e:
            logger.error("Error executing Chrome search: %s", e)

    # Fallback to webbrowser module
    try:
        import webbrowser
        webbrowser.open(search_url)
        return ToolResult(
            success=True,
            summary=f"Opened search for '{query_str}' in your web browser.",
            detailed_text=(
                f"**Browser Search Launched:**\n"
                f"- **Query:** `{query_str}`\n"
                f"- **Target URL:** [{search_url}]({search_url})"
            ),
            data={"query": query_str, "url": search_url, "fallback": True},
        )
    except Exception as e:
        return ToolResult(
            success=False,
            summary=f"Failed to execute browser search: {str(e)}",
            detailed_text=f"**Search Error:** Could not launch browser for query `{query_str}`: {str(e)}",
            error=str(e),
        )


def open_url(url: str) -> ToolResult:
    """
    Open a validated HTTP or HTTPS URL in Google Chrome.
    """
    clean_url = (url or "").strip()
    if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        return ToolResult(
            success=False,
            summary="Invalid web address. URLs must begin with http:// or https://.",
            detailed_text=f"**Validation Error:** Rejected URL `{clean_url}`. Only validated `http://` and `https://` protocols are permitted.",
            error="Invalid URL scheme",
        )

    chrome_path = find_chrome_executable()
    if chrome_path:
        try:
            proc = subprocess.Popen([chrome_path, clean_url], shell=False)
            return ToolResult(
                success=True,
                summary=f"Opened web page in Chrome: {clean_url}",
                detailed_text=f"**Browser Navigation:** Navigated to `{clean_url}` via Chrome PID {proc.pid}.",
                data={"url": clean_url, "pid": proc.pid},
            )
        except Exception as e:
            logger.error("Failed to open URL in Chrome: %s", e)

    try:
        import webbrowser
        webbrowser.open(clean_url)
        return ToolResult(
            success=True,
            summary=f"Opened web page in default browser: {clean_url}",
            detailed_text=f"**Browser Navigation:** Navigated to `{clean_url}`.",
            data={"url": clean_url, "fallback": True},
        )
    except Exception as e:
        return ToolResult(
            success=False,
            summary=f"Could not open URL: {str(e)}",
            detailed_text=f"**Navigation Error:** Failed to open `{clean_url}`: {str(e)}",
            error=str(e),
        )


def register_browser_tools(registry: ActionRegistry) -> None:
    """Register all browser actions with the ActionRegistry."""
    registry.register(
        name="open_chrome",
        description="Launch Google Chrome browser on Windows",
        handler=open_chrome,
        parameters={},
    )
    registry.register(
        name="open_browser_search",
        description="Launch Google Chrome with a URL-encoded Google search query",
        handler=open_browser_search,
        parameters={"query": {"type": "string", "description": "Search terms to look up"}},
    )
    registry.register(
        name="open_url",
        description="Open a validated HTTP or HTTPS web address in Google Chrome",
        handler=open_url,
        parameters={"url": {"type": "string", "description": "Full URL starting with http:// or https://"}},
    )
