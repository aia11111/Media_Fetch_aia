import html
import http.cookiejar
import json
import os
import re
import shutil
import subprocess
import threading
import urllib.request
from urllib.parse import parse_qs, parse_qsl, urlencode, urljoin, urlparse, urlunparse

import yt_dlp

try:
    from gallery_dl import config as gallery_config
    from gallery_dl import cookies as gallery_cookies
    from gallery_dl import job as gallery_job
except ImportError:
    gallery_config = None
    gallery_cookies = None
    gallery_job = None


class Downloader:
    BROWSER_COOKIE_SOURCES = (
        ("firefox", ("APPDATA", "Mozilla", "Firefox", "Profiles")),
        ("edge", ("LOCALAPPDATA", "Microsoft", "Edge", "User Data")),
        ("chrome", ("LOCALAPPDATA", "Google", "Chrome", "User Data")),
        ("brave", ("LOCALAPPDATA", "BraveSoftware", "Brave-Browser", "User Data")),
    )
    BROWSER_PROCESS_NAMES = {
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "chrome": "chrome.exe",
        "brave": "brave.exe",
    }
    INSTAGRAM_APP_ID = "936619743392459"
    NAVER_BLOG_HOSTS = ("blog.naver.com", "m.blog.naver.com")
    THREADS_HOSTS = ("threads.com", "www.threads.com", "threads.net", "www.threads.net")
    THREADS_APP_ID = "238260118697367"
    THREADS_GRAPHQL_DOC_ID = "26603434399279533"
    THREADS_CURL_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    THREADS_SHORTCODE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    THREADS_RELAY_PROVIDER_DEFAULTS = {
        "__relay_internal__pv__BarcelonaHasInlineReplyComposerrelayprovider": False,
        "__relay_internal__pv__BarcelonaHasDearAlgoConsumptionrelayprovider": False,
        "__relay_internal__pv__BarcelonaIsLoggedInrelayprovider": False,
        "__relay_internal__pv__BarcelonaHasEventBadgerelayprovider": False,
        "__relay_internal__pv__BarcelonaIsSearchDiscoveryEnabledrelayprovider": False,
        "__relay_internal__pv__BarcelonaHasCommunitiesrelayprovider": False,
        "__relay_internal__pv__BarcelonaHasGameScoreSharerelayprovider": False,
        "__relay_internal__pv__BarcelonaHasPublicViewCountCardrelayprovider": False,
        "__relay_internal__pv__BarcelonaHasCommunityEntityCardrelayprovider": False,
        "__relay_internal__pv__BarcelonaHasScorecardCommunityrelayprovider": False,
        "__relay_internal__pv__BarcelonaHasMusicrelayprovider": False,
        "__relay_internal__pv__BarcelonaHasNewspaperLinkStylerelayprovider": False,
        "__relay_internal__pv__BarcelonaHasMessagingrelayprovider": False,
        "__relay_internal__pv__BarcelonaHasGhostPostEmojiActivationrelayprovider": False,
        "__relay_internal__pv__BarcelonaOptionalCookiesEnabledrelayprovider": False,
        "__relay_internal__pv__BarcelonaHasDearAlgoWebProductionrelayprovider": False,
        "__relay_internal__pv__BarcelonaIsCrawlerrelayprovider": False,
        "__relay_internal__pv__BarcelonaHasCommunityTopContributorsrelayprovider": False,
        "__relay_internal__pv__BarcelonaCanSeeSponsoredContentrelayprovider": False,
        "__relay_internal__pv__BarcelonaShouldShowFediverseM075Featuresrelayprovider": False,
        "__relay_internal__pv__BarcelonaIsInternalUserrelayprovider": False,
    }
    DEFAULT_REQUEST_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    def __init__(self, download_dir="downloads"):
        self.download_dir = download_dir
        self._ensure_download_dir()
        self.ffmpeg_location = self._detect_ffmpeg_location()
        self._ensure_js_runtime_on_path()
        self._gallery_dl_lock = threading.Lock()

    def _ensure_download_dir(self):
        os.makedirs(self.download_dir, exist_ok=True)

    def _ensure_js_runtime_on_path(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        deno_path = os.path.join(script_dir, "deno.exe")
        if os.path.isfile(deno_path):
            path_entries = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
            if script_dir not in path_entries:
                path_entries.append(script_dir)
                os.environ["PATH"] = os.pathsep.join(path_entries)

    def _detect_ffmpeg_location(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidate_dirs = [
            script_dir,
            os.path.join(script_dir, "ffmpeg"),
            os.path.join(script_dir, "bin"),
        ]

        for candidate in candidate_dirs:
            if os.path.isfile(os.path.join(candidate, "ffmpeg.exe")):
                return candidate

        if shutil.which("ffmpeg"):
            return ""

        return None

    def _download_text(self, url, headers=None, data=None, opener=None):
        request_headers = dict(self.DEFAULT_REQUEST_HEADERS)
        if headers:
            for key, value in headers.items():
                if value is None:
                    request_headers.pop(key, None)
                else:
                    request_headers[key] = value

        request_data = None
        if data is not None:
            if isinstance(data, dict):
                request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
                request_data = urlencode(data).encode("utf-8")
            elif isinstance(data, str):
                request_data = data.encode("utf-8")
            else:
                request_data = data

        request = urllib.request.Request(url, data=request_data, headers=request_headers)
        open_request = opener.open if opener else urllib.request.urlopen
        with open_request(request) as response:
            payload = response.read()
            charset = response.headers.get_content_charset() or "utf-8"

        try:
            return payload.decode(charset, errors="replace")
        except LookupError:
            return payload.decode("utf-8", errors="replace")

    def _download_json_url(self, url, headers=None):
        return json.loads(self._download_text(url, headers=headers))

    def _download_text_with_curl(self, url, headers=None):
        curl_path = shutil.which("curl.exe") or shutil.which("curl")
        if not curl_path:
            raise RuntimeError("curl is not available.")

        command = [
            curl_path,
            "-L",
            "-sS",
            "--max-time",
            "30",
            "-A",
            self.THREADS_CURL_USER_AGENT,
        ]
        for key, value in (headers or {}).items():
            if value is None:
                continue
            command.extend(["-H", f"{key}: {value}"])
        command.append(url)
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(command, capture_output=True, creationflags=creationflags, timeout=35)
        if result.returncode != 0:
            error_text = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(error_text or f"curl exited with code {result.returncode}.")
        return result.stdout.decode("utf-8", errors="replace")

    def _post_form_with_curl(self, url, headers, data):
        curl_path = shutil.which("curl.exe") or shutil.which("curl")
        if not curl_path:
            raise RuntimeError("curl is not available.")

        command = [
            curl_path,
            "-L",
            "-sS",
            "--max-time",
            "30",
            "-A",
            self.THREADS_CURL_USER_AGENT,
        ]
        for key, value in (headers or {}).items():
            if value is None:
                continue
            command.extend(["-H", f"{key}: {value}"])

        for key, value in (data or {}).items():
            command.extend(["--data-urlencode", f"{key}={value}"])

        command.append(url)
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(command, capture_output=True, creationflags=creationflags, timeout=35)
        if result.returncode != 0:
            error_text = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(error_text or f"curl exited with code {result.returncode}.")
        return result.stdout.decode("utf-8", errors="replace")

    def _clean_text(self, value):
        text = html.unescape(value or "")
        return re.sub(r"\s+", " ", text).strip()

    def _int_or_none(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _count_or_none(self, value):
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, dict):
            return self._count_or_none(value.get("count"))
        if isinstance(value, (int, float)):
            count = int(value)
            return count if count >= 0 else None

        text = self._clean_text(value).replace(",", "")
        match = re.match(r"^(\d+(?:\.\d+)?)([kmb])?$", text, re.IGNORECASE)
        if not match:
            return None

        number = float(match.group(1))
        multiplier = {
            "k": 1_000,
            "m": 1_000_000,
            "b": 1_000_000_000,
        }.get((match.group(2) or "").lower(), 1)
        count = int(number * multiplier)
        return count if count >= 0 else None

    def _safe_filename(self, name, fallback="video"):
        cleaned = re.sub(r'[<>:"/\\|?*]+', "_", self._clean_text(name))
        cleaned = cleaned.strip(" .")
        return cleaned or fallback

    def _safe_filename_suffix(self, suffix):
        text = re.sub(r"\s+", " ", html.unescape(str(suffix or "")))
        cleaned = re.sub(r'[<>:"/\\|?*]+', "_", text)
        cleaned = cleaned.rstrip(".")
        return cleaned if cleaned.strip() else ""

    def _next_available_path(self, path):
        base, ext = os.path.splitext(path)
        index = 1
        candidate = f"{base} ({index}){ext}"
        while os.path.exists(candidate):
            index += 1
            candidate = f"{base} ({index}){ext}"
        return candidate

    def _update_url_query(self, url, query):
        parsed = urlparse(url)
        merged = dict(parse_qsl(parsed.query, keep_blank_values=True))
        for key, value in (query or {}).items():
            merged[key] = value
        return urlunparse(parsed._replace(query=urlencode(merged, doseq=True)))

    def _is_playlist_url(self, url):
        try:
            query = parse_qs(urlparse(url).query)
            return bool(query.get("list"))
        except Exception:
            return "list=" in url

    def _is_instagram_url(self, url):
        try:
            host = (urlparse(url).netloc or "").lower()
        except Exception:
            return "instagram.com" in (url or "").lower()
        return host == "instagram.com" or host.endswith(".instagram.com")

    def _is_threads_url(self, url):
        try:
            host = (urlparse(url).netloc or "").lower()
        except Exception:
            return "threads.com" in (url or "").lower() or "threads.net" in (url or "").lower()
        return host in self.THREADS_HOSTS

    def _is_naver_blog_url(self, url):
        try:
            host = (urlparse(url).netloc or "").lower()
        except Exception:
            host = ""
        return host in self.NAVER_BLOG_HOSTS

    def _instagram_shortcode(self, url):
        try:
            parts = [part for part in urlparse(url).path.split("/") if part]
        except Exception:
            return ""
        for idx, part in enumerate(parts):
            if part == "stories" and idx + 2 < len(parts):
                return f"{parts[idx + 1]}_{parts[idx + 2]}"
            if part in {"reel", "p", "tv", "stories"} and idx + 1 < len(parts):
                return parts[idx + 1]
        return parts[-1] if parts else ""

    def _build_instagram_placeholder_info(self, url):
        shortcode = self._instagram_shortcode(url)
        title = f"Instagram {shortcode}" if shortcode else "Instagram Post"
        return {
            "id": shortcode or url,
            "title": title,
            "thumbnail": None,
            "duration": None,
            "formats": [],
            "is_playlist": False,
            "webpage_url": url,
            "extractor": "instagram",
        }

    def _instagram_username_from_title(self, title):
        match = re.match(r"^(?:video|photo|post|reel) by ([^\s]+)$", self._clean_text(title), re.IGNORECASE)
        if not match:
            return ""
        return self._safe_filename(match.group(1), "")

    def _instagram_metadata_value(self, info, primary, *keys):
        for source in (info, primary):
            if not isinstance(source, dict):
                continue
            for key in keys:
                value = self._clean_text(source.get(key))
                if value:
                    return value
        return ""

    def _instagram_like_count(self, info=None, primary=None):
        keys = (
            "like_count",
            "likes",
            "num_likes",
            "edge_media_preview_like",
            "edge_liked_by",
        )
        for source in (info, primary):
            if not isinstance(source, dict):
                continue
            for key in keys:
                count = self._count_or_none(source.get(key))
                if count is not None:
                    return count

            entries = source.get("entries") or []
            if isinstance(entries, list):
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    count = self._instagram_like_count(entry)
                    if count is not None:
                        return count
        return None

    def _instagram_like_filename_suffix(self, info=None, primary=None):
        count = self._instagram_like_count(info, primary)
        if count is None:
            return ""
        if count >= 10000:
            return f"_likes{int((count / 10000) + 0.5)}\ub9cc"
        if count >= 1000:
            value = f"{count / 1000:.1f}".rstrip("0").rstrip(".")
            return f"_likes{value}\ucc9c"
        return f"_likes{count}"

    def _instagram_username_candidate(self, url, info, primary, fallback_title):
        username = self._instagram_username_from_title(fallback_title)
        if username and not username.isdigit():
            return username

        username = self._instagram_metadata_value(info, primary, "uploader", "creator", "channel", "uploader_id")
        safe_username = self._safe_filename(username, "")
        if safe_username and not safe_username.isdigit():
            return safe_username

        try:
            parts = [part for part in urlparse(url).path.split("/") if part]
            if len(parts) >= 3 and parts[0] == "stories":
                return self._safe_filename(parts[1], "")
        except Exception:
            pass

        return ""

    def _instagram_normalized_title(self, url, info, primary, fallback_title):
        shortcode = (
            self._instagram_shortcode(url)
            or self._instagram_metadata_value(info, primary, "display_id", "id")
        )
        username = self._instagram_username_candidate(url, info, primary, fallback_title)

        parts = ["Instagram"]
        if username and not (shortcode and shortcode.startswith(f"{username}_")):
            parts.append(self._safe_filename(username))
        if shortcode:
            parts.append(self._safe_filename(shortcode))

        if len(parts) > 1:
            return "_".join(parts)
        return fallback_title or self._build_instagram_placeholder_info(url).get("title")

    def _instagram_ytdlp_outtmpl(self, url, filename_suffix="", info=None):
        suffix = self._safe_filename_suffix(filename_suffix)
        like_suffix = self._instagram_like_filename_suffix(info)
        media_key = self._safe_filename(self._instagram_shortcode(url) or "%(id)s", "instagram")
        return os.path.join(self.download_dir, f"Instagram_{media_key}{suffix}{like_suffix}.%(ext)s")

    def _instagram_public_url(self, url):
        parsed = urlparse(url)
        segments = [part for part in parsed.path.split("/") if part]
        container = "p"
        shortcode = ""

        for idx, part in enumerate(segments):
            if part == "stories" and idx + 2 < len(segments):
                return f"https://www.instagram.com/stories/{segments[idx + 1]}/{segments[idx + 2]}/"
            if part in {"reel", "p", "tv", "stories"} and idx + 1 < len(segments):
                container = part
                shortcode = segments[idx + 1]
                break

        if not shortcode:
            shortcode = self._instagram_shortcode(url)

        if not shortcode:
            return url

        return f"https://www.instagram.com/{container}/{shortcode}/"

    def _probe_instagram_oembed(self, url):
        public_url = self._instagram_public_url(url)
        oembed_url = f"https://www.instagram.com/api/v1/oembed/?{urlencode({'url': public_url})}"
        headers = {
            "Accept": "application/json",
            "X-IG-App-ID": self.INSTAGRAM_APP_ID,
        }
        try:
            payload = self._download_text_with_curl(oembed_url, headers=headers)
            data = json.loads(payload)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _is_browser_running(self, browser):
        process_name = self.BROWSER_PROCESS_NAMES.get(browser)
        if not process_name or os.name != "nt":
            return False

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/NH"],
                capture_output=True,
                text=True,
                creationflags=creationflags,
                timeout=5,
            )
        except Exception:
            return False

        output = f"{result.stdout}\n{result.stderr}".lower()
        return process_name.lower() in output

    def _instagram_cookie_diagnostics(self):
        if gallery_cookies is None:
            return False, [], []

        has_instagram_cookies = False
        diagnostics = []
        running_locked_browsers = []

        for browser in dict.fromkeys(browser for browser, _ in self.BROWSER_COOKIE_SOURCES):
            browser_label = browser.title()
            browser_running = self._is_browser_running(browser)
            try:
                jar = gallery_cookies.load_cookies((browser, None, None, None, "instagram.com"))
                cookie_count = len(jar)
                if cookie_count > 0:
                    has_instagram_cookies = True
                    suffix = " (browser still running)" if browser_running else ""
                    diagnostics.append(f"{browser_label}: {cookie_count} Instagram cookies found{suffix}")
                else:
                    diagnostics.append(f"{browser_label}: no Instagram cookies found")
            except PermissionError:
                if browser_running:
                    running_locked_browsers.append(browser_label)
                    diagnostics.append(f"{browser_label}: cookie DB is locked because the browser is still running")
                else:
                    diagnostics.append(f"{browser_label}: cookie DB is locked by the browser")
            except Exception as exc:
                text = self._clean_text(str(exc))
                lowered = text.lower()
                if "dpapi" in lowered or "decrypt" in lowered:
                    diagnostics.append(f"{browser_label}: cookies could not be decrypted")
                elif "permission denied" in lowered or "winerror 32" in lowered:
                    if browser_running:
                        running_locked_browsers.append(browser_label)
                        diagnostics.append(f"{browser_label}: cookie DB is locked because the browser is still running")
                    else:
                        diagnostics.append(f"{browser_label}: cookie DB is locked by the browser")
                else:
                    diagnostics.append(f"{browser_label}: {text or exc.__class__.__name__}")

        return has_instagram_cookies, diagnostics, running_locked_browsers

    def _summarize_instagram_error(self, error, label):
        text = self._clean_text(str(error))
        lowered = text.lower()
        if "empty media response" in lowered:
            return f"{label}: empty media response"
        if "could not copy" in lowered or "permission denied" in lowered:
            return f"{label}: browser cookie DB was locked"
        if "dpapi" in lowered or "decrypt" in lowered:
            return f"{label}: browser cookies could not be decrypted"
        if "status 4" in lowered:
            return f"{label}: no accessible media or cookies"
        return f"{label}: {text}"

    def _build_instagram_failure_message(self, url, primary_error, gallery_error=None):
        details = []
        probe = self._probe_instagram_oembed(url)
        probe_status = self._clean_text(str(probe.get("status")))
        probe_title = self._clean_text(probe.get("title") or probe.get("message"))
        probe_description = self._clean_text(probe.get("description"))

        if probe_status == "fail":
            reason = probe_title or "This post is not accessible while logged out."
            if probe_description and probe_description not in reason:
                reason = f"{reason} {probe_description}"
            details.append(f"Instagram says this post needs a logged-in account: {reason}")

        has_cookies, cookie_diagnostics, running_locked_browsers = self._instagram_cookie_diagnostics()
        if cookie_diagnostics:
            prefix = "Readable Instagram cookies:" if has_cookies else "Browser cookie check:"
            details.append(f"{prefix} {'; '.join(cookie_diagnostics)}")

        if running_locked_browsers:
            names = ", ".join(running_locked_browsers)
            details.append(
                f"Close these browsers completely before retrying: {names}. "
                "If they stay in the system tray or background, the app still cannot read their Instagram cookies."
            )
        elif has_cookies:
            details.append("A readable Instagram session exists. Fully close that browser, then try again.")
        else:
            details.append("Sign into Instagram in Firefox or Edge on this PC, then fully close that browser and try again.")

        technical = [self._summarize_instagram_error(primary_error, "yt-dlp")]
        if gallery_error is not None:
            technical.append(self._summarize_instagram_error(gallery_error, "gallery-dl"))
        details.append(f"Technical details: {' | '.join(technical)}")
        return "Instagram download failed. " + " | ".join(details)

    def _threads_shortcode(self, url):
        try:
            parts = [part for part in urlparse(url).path.split("/") if part]
        except Exception:
            return ""

        for idx, part in enumerate(parts):
            if part in {"post", "t"} and idx + 1 < len(parts):
                return parts[idx + 1]

        return parts[-1] if parts else ""

    def _threads_shortcode_to_media_id(self, shortcode):
        media_id = 0
        if not shortcode:
            return ""

        for char in shortcode:
            index = self.THREADS_SHORTCODE_ALPHABET.find(char)
            if index < 0:
                return ""
            media_id = media_id * 64 + index

        return str(media_id)

    def _build_threads_placeholder_info(self, url):
        shortcode = self._threads_shortcode(url)
        title = f"Threads {shortcode}" if shortcode else "Threads Post"
        return {
            "id": shortcode or url,
            "title": title,
            "thumbnail": None,
            "duration": None,
            "formats": [],
            "entries": [],
            "is_playlist": False,
            "webpage_url": url,
            "extractor": "threads",
        }

    def _extract_thumbnail_url(self, info):
        if not isinstance(info, dict):
            return None

        thumbnail = info.get("thumbnail")
        if thumbnail:
            return thumbnail

        thumbnails = info.get("thumbnails") or []
        if isinstance(thumbnails, list):
            for candidate in reversed(thumbnails):
                if isinstance(candidate, dict) and candidate.get("url"):
                    return candidate["url"]

        entries = info.get("entries") or []
        if isinstance(entries, list):
            for entry in entries:
                thumbnail = self._extract_thumbnail_url(entry)
                if thumbnail:
                    return thumbnail

        return None

    def _normalize_instagram_info(self, url, info):
        if not isinstance(info, dict):
            return self._build_instagram_placeholder_info(url)

        normalized = dict(info)
        entries = normalized.get("entries") or []
        primary = next((entry for entry in entries if isinstance(entry, dict)), None) if isinstance(entries, list) else None

        title = self._clean_text(normalized.get("title"))
        if not title and primary:
            title = self._clean_text(primary.get("title"))
        if not title:
            title = self._build_instagram_placeholder_info(url).get("title")

        normalized["title"] = self._instagram_normalized_title(url, normalized, primary, title)
        normalized["thumbnail"] = self._extract_thumbnail_url(normalized)
        normalized["duration"] = normalized.get("duration") or (primary.get("duration") if primary else None)
        like_count = self._instagram_like_count(normalized, primary)
        if like_count is not None:
            normalized["like_count"] = like_count
        normalized.setdefault("formats", [])
        normalized.setdefault("webpage_url", url)
        normalized.setdefault("extractor", "instagram")
        return normalized

    def _threads_public_url(self, url):
        parsed = urlparse(url)
        return urlunparse(parsed._replace(scheme="https", netloc="www.threads.com", query="", fragment=""))

    def _threads_jazoest(self, token):
        return "2" + str(sum(ord(char) for char in token or ""))

    def _extract_threads_config(self, webpage):
        token_match = re.search(r'"LSD",\[\],\{"token":"([^"]+)"', webpage or "")
        token = token_match.group(1) if token_match else ""

        app_match = re.search(r'"X-IG-App-ID":"([^"]+)"', webpage or "")
        app_id = app_match.group(1) if app_match else self.THREADS_APP_ID

        return token, app_id

    def _threads_graphql_variables(self, media_id):
        variables = {"postID": media_id}
        variables.update(self.THREADS_RELAY_PROVIDER_DEFAULTS)
        return variables

    def _threads_graphql_payload(self, url):
        shortcode = self._threads_shortcode(url)
        media_id = self._threads_shortcode_to_media_id(shortcode)
        if not media_id:
            raise RuntimeError("Could not read the Threads post id from this URL.")

        public_url = self._threads_public_url(url)
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
        try:
            webpage = self._download_text_with_curl(public_url)
        except Exception:
            webpage = self._download_text(public_url, headers={"Accept-Language": None}, opener=opener)
        lsd_token, app_id = self._extract_threads_config(webpage)
        if not lsd_token:
            raise RuntimeError("Could not read the Threads session token.")

        variables = self._threads_graphql_variables(media_id)
        form = {
            "__a": "1",
            "__user": "0",
            "__comet_req": "29",
            "lsd": lsd_token,
            "jazoest": self._threads_jazoest(lsd_token),
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "BarcelonaPostColumnPageQuery",
            "variables": json.dumps(variables, separators=(",", ":")),
            "server_timestamps": "true",
            "doc_id": self.THREADS_GRAPHQL_DOC_ID,
        }
        headers = {
            "Accept": "*/*",
            "Accept-Language": None,
            "Origin": "https://www.threads.com",
            "Referer": public_url,
            "X-FB-LSD": lsd_token,
            "X-IG-App-ID": app_id,
        }

        try:
            response_text = self._post_form_with_curl("https://www.threads.com/api/graphql/", headers, form)
        except Exception:
            response_text = self._download_text("https://www.threads.com/api/graphql/", headers=headers, data=form, opener=opener)
        if response_text.startswith("for (;;);"):
            response_text = response_text[len("for (;;);") :]

        payload = json.loads(response_text)
        media = ((payload.get("data") or {}).get("media") or {})
        if not media:
            errors = payload.get("errors") or []
            if errors and isinstance(errors, list):
                first_error = errors[0] if isinstance(errors[0], dict) else {}
                message = first_error.get("summary") or first_error.get("description") or first_error.get("message")
                if message:
                    raise RuntimeError(f"Threads API failed: {message}")
            raise RuntimeError("Threads API did not return a downloadable post.")

        return media

    def _threads_caption_text(self, media):
        caption = media.get("caption")
        if isinstance(caption, dict):
            text = self._clean_text(caption.get("text"))
            if text:
                return text

        info = media.get("text_post_app_info")
        fragments = ((info or {}).get("text_fragments") or {}).get("fragments") if isinstance(info, dict) else []
        if isinstance(fragments, list):
            text = self._clean_text(" ".join(fragment.get("plaintext") or "" for fragment in fragments if isinstance(fragment, dict)))
            if text:
                return text

        return ""

    def _threads_media_title(self, media, fallback):
        username = self._clean_text(((media.get("user") or {}).get("username") if isinstance(media.get("user"), dict) else ""))
        caption = self._threads_caption_text(media)
        snippet = caption.splitlines()[0] if caption else ""
        snippet = snippet[:80].rstrip()

        if username and snippet:
            return f"Threads {username} - {snippet}"
        if username:
            return f"Threads {username} {fallback}".strip()
        return f"Threads {fallback}".strip()

    def _threads_thumbnail_url(self, media):
        candidates = ((media.get("image_versions2") or {}).get("candidates") or [])
        if not isinstance(candidates, list):
            return None

        best = None
        best_area = -1
        for candidate in candidates:
            if not isinstance(candidate, dict) or not candidate.get("url"):
                continue
            area = (self._int_or_none(candidate.get("width")) or 0) * (self._int_or_none(candidate.get("height")) or 0)
            if area >= best_area:
                best = candidate
                best_area = area

        return best.get("url") if best else None

    def _threads_video_entry_from_media(self, media, fallback_title):
        versions = media.get("video_versions") or []
        if not isinstance(versions, list):
            return None

        video_url = ""
        for version in versions:
            if isinstance(version, dict) and version.get("url"):
                video_url = version["url"]
                break

        if not video_url:
            return None

        title = self._threads_media_title(media, fallback_title)
        return {
            "id": media.get("pk") or media.get("id") or fallback_title,
            "title": title,
            "url": video_url,
            "thumbnail": self._threads_thumbnail_url(media),
            "duration": media.get("video_duration") or media.get("duration"),
            "width": media.get("original_width"),
            "height": media.get("original_height"),
            "ext": "mp4",
        }

    def _threads_video_entries(self, media, fallback_title):
        entries = []
        seen_media = set()

        def visit(candidate):
            if not isinstance(candidate, dict):
                return

            media_key = candidate.get("id") or candidate.get("pk") or id(candidate)
            if media_key in seen_media:
                return
            seen_media.add(media_key)

            entry = self._threads_video_entry_from_media(candidate, fallback_title)
            if entry:
                entries.append(entry)

            carousel = candidate.get("carousel_media") or []
            if isinstance(carousel, list):
                for child in carousel:
                    visit(child)

            share_info = ((candidate.get("text_post_app_info") or {}).get("share_info") or {})
            if isinstance(share_info, dict):
                for key in ("quoted_attachment_post", "quoted_post", "reposted_post"):
                    visit(share_info.get(key))

        visit(media)
        return entries

    def _fetch_threads_info(self, url):
        media = self._threads_graphql_payload(url)
        shortcode = media.get("code") or self._threads_shortcode(url)
        fallback_title = shortcode or (media.get("pk") or "")
        title = self._threads_media_title(media, fallback_title)
        entries = self._threads_video_entries(media, fallback_title)
        thumbnail = self._threads_thumbnail_url(media)
        if entries and entries[0].get("thumbnail"):
            thumbnail = entries[0]["thumbnail"]

        formats = [
            {
                "format_id": f"threads-{index}",
                "url": entry["url"],
                "ext": "mp4",
                "width": entry.get("width"),
                "height": entry.get("height"),
            }
            for index, entry in enumerate(entries, start=1)
        ]

        return {
            "id": media.get("pk") or shortcode or url,
            "title": title,
            "thumbnail": thumbnail,
            "duration": entries[0].get("duration") if entries else None,
            "formats": formats,
            "entries": entries,
            "is_playlist": len(entries) > 1,
            "webpage_url": url,
            "extractor": "threads",
        }

    def _naver_blog_identity(self, url):
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        blog_id = (query.get("blogId") or [""])[0]
        log_no = (query.get("logNo") or [""])[0]
        if blog_id and log_no:
            return blog_id, log_no

        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) >= 2 and re.fullmatch(r"\d+", path_parts[-1]):
            return path_parts[-2], path_parts[-1]

        return "", ""

    def _extract_meta_title(self, webpage):
        patterns = [
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']',
            r"<title>(.*?)</title>",
        ]
        for pattern in patterns:
            match = re.search(pattern, webpage, flags=re.IGNORECASE | re.DOTALL)
            if match:
                title = self._clean_text(match.group(1))
                if title:
                    return title
        return ""

    def _naver_blog_postview_url(self, url):
        blog_id, log_no = self._naver_blog_identity(url)
        if blog_id and log_no:
            return (
                "https://blog.naver.com/PostView.naver?"
                f"blogId={blog_id}&logNo={log_no}&redirect=Dlog&widgetTypeCall=true"
                "&noTrackingCode=true&directAccess=false"
            )

        frameset_html = self._download_text(url)
        match = re.search(r'<iframe[^>]+id=["\']mainFrame["\'][^>]+src=["\']([^"\']+)["\']', frameset_html, re.IGNORECASE)
        if not match:
            raise RuntimeError("Could not locate the Naver Blog article frame.")
        return urljoin("https://blog.naver.com", html.unescape(match.group(1)))

    def _parse_naver_blog_video_modules(self, webpage, fallback_title, source_url):
        entries = []
        seen = set()
        module_patterns = [
            r"data-module-v2='([^']+)'",
            r'data-module-v2="([^"]+)"',
            r"data-module='([^']+)'",
            r'data-module="([^"]+)"',
        ]

        for pattern in module_patterns:
            for match in re.finditer(pattern, webpage):
                payload = html.unescape(match.group(1))
                try:
                    module = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                if module.get("type") != "v2_video":
                    continue

                data = module.get("data") or {}
                vid = (data.get("vid") or "").strip()
                inkey = (data.get("inkey") or data.get("inKey") or "").strip()
                if not vid or not inkey or vid in seen:
                    continue

                media_meta = data.get("mediaMeta") or {}
                title = self._clean_text(media_meta.get("title")) or fallback_title
                entries.append(
                    {
                        "title": title,
                        "thumbnail": data.get("thumbnail"),
                        "vid": vid,
                        "inkey": inkey,
                        "post_title": fallback_title,
                        "referer": source_url,
                    }
                )
                seen.add(vid)

        if entries:
            return entries

        direct_seen = set()
        for match in re.finditer(r'<video[^>]+src="([^"]+)"', webpage, re.IGNORECASE):
            direct_url = html.unescape(match.group(1)).strip()
            if not direct_url or direct_url in direct_seen:
                continue
            if "mblogvideo-phinf.pstatic.net" not in direct_url:
                continue
            direct_seen.add(direct_url)
            entries.append(
                {
                    "title": fallback_title if len(entries) == 0 else f"{fallback_title} {len(entries) + 1}",
                    "thumbnail": None,
                    "direct_url": direct_url,
                    "post_title": fallback_title,
                    "referer": source_url,
                }
            )

        return entries

    def _extract_naver_blog_videos(self, url):
        postview_url = self._naver_blog_postview_url(url)
        webpage = self._download_text(postview_url, headers={"Referer": url})
        blog_id, log_no = self._naver_blog_identity(postview_url)
        fallback_title = self._extract_meta_title(webpage) or f"Naver Blog {log_no or blog_id or 'Video'}"
        entries = self._parse_naver_blog_video_modules(webpage, fallback_title, postview_url)
        if not entries:
            raise RuntimeError("No downloadable video was found in this Naver Blog post.")
        return entries

    def _build_naver_blog_placeholder_info(self, url):
        entries = self._extract_naver_blog_videos(url)
        playlist_title = entries[0].get("post_title") or entries[0].get("title") or "Naver Blog Video"
        title = playlist_title if len(entries) == 1 else f"{playlist_title} ({len(entries)} videos)"
        return {
            "id": url,
            "title": title,
            "thumbnail": entries[0].get("thumbnail"),
            "duration": None,
            "formats": [],
            "is_playlist": len(entries) > 1,
            "webpage_url": url,
            "extractor": "naver_blog",
            "entries": entries,
        }

    def _download_naver_video_data(self, vid, inkey, referer):
        headers = {"Referer": referer or "https://blog.naver.com"}
        urls = [
            f"https://play.rmcnmv.naver.com/vod/play/v2.0/{vid}?{urlencode({'key': inkey})}",
            f"http://play.rmcnmv.naver.com/vod/play/v2.0/{vid}?{urlencode({'key': inkey})}",
        ]
        last_error = None
        for api_url in urls:
            try:
                return self._download_json_url(api_url, headers=headers)
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"Could not resolve the Naver Blog video stream: {last_error}") from last_error

    def _naver_video_formats(self, vid, inkey, referer):
        video_data = self._download_naver_video_data(vid, inkey, referer)
        meta = video_data.get("meta") or {}
        formats = []

        for stream in ((video_data.get("videos") or {}).get("list") or []):
            source = stream.get("source")
            if not source:
                continue
            encoding_option = stream.get("encodingOption") or {}
            formats.append(
                {
                    "url": source,
                    "width": self._int_or_none(encoding_option.get("width")),
                    "height": self._int_or_none(encoding_option.get("height")),
                    "protocol": None,
                }
            )

        for stream_set in video_data.get("streams") or []:
            query = {
                param.get("name"): param.get("value")
                for param in (stream_set.get("keys") or [])
                if param.get("name") and param.get("value") is not None
            }
            stream_type = (stream_set.get("type") or "").upper()
            videos = stream_set.get("videos") or []
            if videos:
                for stream in videos:
                    source = stream.get("source")
                    if not source:
                        continue
                    encoding_option = stream.get("encodingOption") or {}
                    formats.append(
                        {
                            "url": self._update_url_query(source, query),
                            "width": self._int_or_none(encoding_option.get("width")),
                            "height": self._int_or_none(encoding_option.get("height")),
                            "protocol": "m3u8" if stream_type == "HLS" else None,
                        }
                    )
                continue

            if stream_type == "HLS" and stream_set.get("source"):
                formats.append(
                    {
                        "url": self._update_url_query(stream_set["source"], query),
                        "width": None,
                        "height": None,
                        "protocol": "m3u8",
                    }
                )

        if not formats:
            raise RuntimeError("No playable stream was returned for this Naver Blog video.")

        return meta, formats

    def _select_naver_blog_format(self, formats, resolution):
        if not formats:
            raise RuntimeError("No available stream could be selected.")

        candidates = [fmt for fmt in formats if fmt.get("url")]
        progressive = [fmt for fmt in candidates if fmt.get("protocol") != "m3u8"]
        preferred = progressive or candidates

        def sort_key(fmt):
            return (fmt.get("height") or 0, fmt.get("width") or 0, 1 if fmt.get("protocol") != "m3u8" else 0)

        if resolution == "Best":
            return max(preferred, key=sort_key)

        target = self._int_or_none(str(resolution).replace("p", "")) or 0
        under_target = [fmt for fmt in preferred if (fmt.get("height") or 0) and (fmt.get("height") or 0) <= target]
        if under_target:
            return max(under_target, key=sort_key)

        with_height = [fmt for fmt in preferred if fmt.get("height")]
        if with_height:
            return min(with_height, key=lambda fmt: (abs((fmt.get("height") or target) - target), -(fmt.get("height") or 0)))

        return preferred[0]

    def _naver_blog_outtmpl(self, entry, index, total, filename_suffix=""):
        prefix = f"{index:03d}_" if total > 1 else ""
        safe_title = self._safe_filename(entry.get("title") or entry.get("post_title") or f"naver_blog_{index}")
        suffix = self._safe_filename_suffix(filename_suffix)
        return os.path.join(self.download_dir, f"{prefix}{safe_title}{suffix}.%(ext)s")

    def _wrap_naver_blog_progress_hook(self, progress_hook, index, total):
        if not progress_hook:
            return None

        def wrapped(progress):
            payload = dict(progress)
            payload.setdefault("playlist_index", index)
            payload.setdefault("playlist_count", total)
            progress_hook(payload)

        return wrapped

    def _available_browser_cookie_sources(self):
        available = []
        for browser, path_parts in self.BROWSER_COOKIE_SOURCES:
            env_name, *suffix = path_parts
            base_dir = os.environ.get(env_name)
            if not base_dir:
                continue
            if os.path.exists(os.path.join(base_dir, *suffix)):
                available.append(browser)
        return available

    def _augment_instagram_error(self, message, attempted_browsers, available_browsers):
        if available_browsers:
            browser_names = ", ".join(browser.title() for browser in available_browsers)
            attempted_names = ", ".join(browser.title() for browser in attempted_browsers) if attempted_browsers else browser_names
            return (
                f"{message} | Instagram often needs a logged-in browser session. "
                f"Make sure Instagram opens normally in {attempted_names}, then fully close that browser and try again. "
                f"Detected browsers: {browser_names}."
            )

        return (
            f"{message} | Instagram often needs browser cookies, but no supported browser profile was found. "
            "Sign into Instagram in Edge or Chrome on this PC and try again."
        )

    def _run_ydl(self, url, ydl_opts, action):
        if not self._is_instagram_url(url):
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return action(ydl)

        available_browsers = self._available_browser_cookie_sources()
        attempted_browsers = []
        attempts = [(None, dict(ydl_opts))]
        last_exc = None

        for browser in available_browsers:
            retry_opts = dict(ydl_opts)
            retry_opts["cookiesfrombrowser"] = (browser, None, None, None)
            attempts.append((browser, retry_opts))


        for browser, attempt_opts in attempts:
            try:
                with yt_dlp.YoutubeDL(attempt_opts) as ydl:
                    return action(ydl)
            except Exception as exc:
                last_exc = exc
                if browser:
                    attempted_browsers.append(browser)

        raise RuntimeError(
            self._augment_instagram_error(str(last_exc), attempted_browsers, available_browsers)
        ) from last_exc

    def _gallery_dl_available(self):
        return gallery_config is not None and gallery_job is not None

    def _snapshot_download_dir(self, download_dir):
        snapshot = {}
        if not download_dir or not os.path.isdir(download_dir):
            return snapshot

        for root, _, files in os.walk(download_dir):
            for name in files:
                path = os.path.abspath(os.path.join(root, name))
                try:
                    snapshot[path] = os.path.getmtime(path)
                except OSError:
                    pass
        return snapshot

    def _resolve_new_download(self, before_snapshot, download_dir):
        newest_path = ""
        newest_mtime = -1.0

        if not download_dir or not os.path.isdir(download_dir):
            return ""

        for root, _, files in os.walk(download_dir):
            for name in files:
                path = os.path.abspath(os.path.join(root, name))
                try:
                    mtime = os.path.getmtime(path)
                except OSError:
                    continue

                previous = before_snapshot.get(path)
                is_candidate = previous is None or mtime >= previous
                if is_candidate and mtime >= newest_mtime:
                    newest_path = path
                    newest_mtime = mtime

        if newest_path:
            return newest_path

        for root, _, files in os.walk(download_dir):
            for name in files:
                path = os.path.abspath(os.path.join(root, name))
                try:
                    mtime = os.path.getmtime(path)
                except OSError:
                    continue
                if mtime >= newest_mtime:
                    newest_path = path
                    newest_mtime = mtime

        return newest_path

    def _gallery_dl_settings(self, browser=None):
        settings = [
            ((), "base-directory", self.download_dir),
            ((), "directory", ()),
            (("output",), "mode", "null"),
            (("downloader",), "progress", None),
        ]
        if browser:
            settings.append(((), "cookies", (browser, None, None, None, "instagram.com")))
        return settings

    def _rename_instagram_gallery_download(self, url, source_path, filename_suffix="", overwrite=False, info=None):
        if not source_path or not os.path.exists(source_path):
            return source_path

        shortcode = self._instagram_shortcode(url)
        if not shortcode:
            return source_path

        _, ext = os.path.splitext(source_path)
        base_name = self._safe_filename(f"Instagram_{shortcode}", "Instagram")
        target_path = os.path.join(
            self.download_dir,
            f"{base_name}{self._safe_filename_suffix(filename_suffix)}{self._instagram_like_filename_suffix(info)}{ext}",
        )

        if os.path.normcase(os.path.abspath(source_path)) == os.path.normcase(os.path.abspath(target_path)):
            return source_path

        if os.path.exists(target_path):
            if overwrite:
                os.remove(target_path)
            else:
                target_path = self._next_available_path(target_path)

        os.replace(source_path, target_path)
        return target_path

    def _download_instagram_with_gallery_dl(self, url, progress_hook, filename_suffix="", overwrite=False, info=None):
        if not self._gallery_dl_available():
            raise RuntimeError("Instagram fallback is unavailable because gallery-dl is not installed.")

        available_browsers = self._available_browser_cookie_sources()
        attempted_browsers = []
        before_snapshot = self._snapshot_download_dir(self.download_dir)
        attempts = [(browser, self._gallery_dl_settings(browser)) for browser in available_browsers]
        attempts.append((None, self._gallery_dl_settings(None)))
        last_error = None

        with self._gallery_dl_lock:
            for browser, settings in attempts:
                label = browser.title() if browser else "No cookies"
                try:
                    with gallery_config.apply(settings):
                        status = gallery_job.DownloadJob(url).run()
                    if status == 0:
                        path = self._resolve_new_download(before_snapshot, self.download_dir)
                        if not path or not os.path.exists(path):
                            last_error = RuntimeError(f"gallery-dl reported success via {label}, but no file was created.")
                            continue
                        path = self._rename_instagram_gallery_download(url, path, filename_suffix, overwrite, info)
                        if progress_hook:
                            progress_hook(
                                {
                                    "status": "finished",
                                    "filename": path,
                                    "info_dict": {"_filename": path},
                                }
                            )
                        return path
                    last_error = RuntimeError(f"gallery-dl returned status {status} via {label}")
                except Exception as exc:
                    last_error = exc
                if browser:
                    attempted_browsers.append(browser)

        raise RuntimeError(
            self._augment_instagram_error(str(last_error), attempted_browsers, available_browsers)
        ) from last_error

    def _threads_outtmpl(self, entry, index, total, filename_suffix=""):
        prefix = f"{index:03d}_" if total > 1 else ""
        safe_title = self._safe_filename(entry.get("title") or f"threads_{index}")
        suffix = self._safe_filename_suffix(filename_suffix)
        return os.path.join(self.download_dir, f"{prefix}{safe_title}{suffix}.%(ext)s")

    def _download_threads_post(self, url, format_type, progress_hook, overwrite, filename_suffix=""):
        info = self._fetch_threads_info(url)
        entries = info.get("entries") or []
        if not entries:
            raise RuntimeError("No downloadable video was found in this Threads post.")

        total_entries = len(entries)
        has_ffmpeg = self.ffmpeg_location is not None

        for index, entry in enumerate(entries, start=1):
            media_url = entry.get("url")
            if not media_url:
                continue

            wrapped_hook = self._wrap_naver_blog_progress_hook(progress_hook, index, total_entries)
            ydl_opts = {
                "outtmpl": self._threads_outtmpl(entry, index, total_entries, filename_suffix),
                "progress_hooks": [wrapped_hook] if wrapped_hook else [],
                "quiet": True,
                "no_warnings": True,
                "nooverwrites": not overwrite,
                "overwrites": overwrite,
                "http_headers": {
                    **self.DEFAULT_REQUEST_HEADERS,
                    "Referer": self._threads_public_url(url),
                },
            }

            if self.ffmpeg_location:
                ydl_opts["ffmpeg_location"] = self.ffmpeg_location

            if format_type == "Audio" and has_ffmpeg:
                ydl_opts["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ]

            self._run_ydl(media_url, ydl_opts, lambda ydl, target=media_url: ydl.download([target]))

    def fetch_info(self, url, info_callback, error_callback):
        """Fetches video info asynchronously."""

        def fetch():
            if self._is_threads_url(url):
                try:
                    info_callback(self._fetch_threads_info(url))
                except Exception:
                    info_callback(self._build_threads_placeholder_info(url))
                return

            if self._is_instagram_url(url):
                try:
                    info = self._run_ydl(
                        url,
                        {
                            "quiet": True,
                            "no_warnings": True,
                        },
                        lambda ydl: ydl.extract_info(url, download=False),
                    )
                    info_callback(self._normalize_instagram_info(url, info))
                except Exception:
                    info_callback(self._build_instagram_placeholder_info(url))
                return

            if self._is_naver_blog_url(url):
                info_callback(self._build_naver_blog_placeholder_info(url))
                return

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": "in_playlist",
            }
            try:
                info = self._run_ydl(url, ydl_opts, lambda ydl: ydl.extract_info(url, download=False))
                info_callback(info)
            except Exception as e:
                error_callback(str(e))

        threading.Thread(target=fetch, daemon=True).start()

    def _download_naver_blog_post(self, url, format_type, resolution, progress_hook, overwrite, filename_suffix=""):
        entries = self._extract_naver_blog_videos(url)
        total_entries = len(entries)
        has_ffmpeg = self.ffmpeg_location is not None

        for index, entry in enumerate(entries, start=1):
            selected_format = None
            media_url = entry.get("direct_url")
            if not media_url:
                meta, formats = self._naver_video_formats(entry["vid"], entry["inkey"], entry.get("referer") or url)
                meta_title = self._clean_text(meta.get("subject"))
                if meta_title:
                    entry["title"] = meta_title
                cover = (meta.get("cover") or {}).get("source") if isinstance(meta.get("cover"), dict) else None
                if cover and not entry.get("thumbnail"):
                    entry["thumbnail"] = cover
                selected_format = self._select_naver_blog_format(formats, resolution if format_type == "Video" else "Best")
                media_url = selected_format["url"]

            request_headers = dict(self.DEFAULT_REQUEST_HEADERS)
            request_headers["Referer"] = entry.get("referer") or url
            wrapped_hook = self._wrap_naver_blog_progress_hook(progress_hook, index, total_entries)

            ydl_opts = {
                "outtmpl": self._naver_blog_outtmpl(entry, index, total_entries, filename_suffix),
                "progress_hooks": [wrapped_hook] if wrapped_hook else [],
                "quiet": True,
                "no_warnings": True,
                "nooverwrites": not overwrite,
                "overwrites": overwrite,
                "http_headers": request_headers,
            }

            if self.ffmpeg_location:
                ydl_opts["ffmpeg_location"] = self.ffmpeg_location

            if format_type == "Audio":
                if has_ffmpeg:
                    ydl_opts["postprocessors"] = [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }
                    ]
            elif selected_format and selected_format.get("protocol") == "m3u8" and has_ffmpeg:
                ydl_opts["merge_output_format"] = "mp4"

            self._run_ydl(media_url, ydl_opts, lambda ydl, target=media_url: ydl.download([target]))

    def start_download(
        self,
        url,
        format_type,
        resolution,
        download_subtitles,
        progress_hook,
        finished_hook,
        error_callback,
        overwrite=False,
        filename_suffix="",
        info=None,
    ):
        """Starts download asynchronously."""

        def download():
            instagram_gallery_error = None
            primary_error = None
            try:
                self._ensure_download_dir()

                if self._is_naver_blog_url(url):
                    self._download_naver_blog_post(url, format_type, resolution, progress_hook, overwrite, filename_suffix)
                    finished_hook()
                    return

                if self._is_threads_url(url):
                    self._download_threads_post(url, format_type, progress_hook, overwrite, filename_suffix)
                    finished_hook()
                    return

                is_playlist = self._is_playlist_url(url)
                has_ffmpeg = self.ffmpeg_location is not None

                if self._is_instagram_url(url):
                    base_outtmpl = self._instagram_ytdlp_outtmpl(url, filename_suffix, info)
                else:
                    base_outtmpl = (
                        os.path.join(self.download_dir, f"%(playlist_index)03d_%(title)s{self._safe_filename_suffix(filename_suffix)}.%(ext)s")
                        if is_playlist
                        else os.path.join(self.download_dir, f"%(title)s{self._safe_filename_suffix(filename_suffix)}.%(ext)s")
                    )

                ydl_opts = {
                    "outtmpl": base_outtmpl,
                    "progress_hooks": [progress_hook],
                    "quiet": True,
                    "no_warnings": True,
                    "extract_flat": False,
                    "noplaylist": not is_playlist,
                    "nooverwrites": not overwrite,
                    "overwrites": overwrite,
                }

                if self.ffmpeg_location:
                    ydl_opts["ffmpeg_location"] = self.ffmpeg_location

                if format_type == "Audio":
                    ydl_opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
                    if has_ffmpeg:
                        ydl_opts["postprocessors"] = [
                            {
                                "key": "FFmpegExtractAudio",
                                "preferredcodec": "mp3",
                                "preferredquality": "192",
                            }
                        ]
                else:
                    if resolution == "Best":
                        format_str = "bestvideo*+bestaudio/best" if has_ffmpeg else "best[ext=mp4]/best"
                    else:
                        res_val = resolution.replace("p", "")
                        if has_ffmpeg:
                            format_str = f"bestvideo*[height<={res_val}]+bestaudio/best[height<={res_val}]"
                        else:
                            format_str = f"best[height<={res_val}][ext=mp4]/best[height<={res_val}]/best"

                    ydl_opts["format"] = format_str
                    if has_ffmpeg:
                        ydl_opts["merge_output_format"] = "mp4"

                    if download_subtitles:
                        ydl_opts.update(
                            {
                                "writesubtitles": True,
                                "subtitleslangs": ["ko", "en"],
                                "writeautomaticsub": False,
                            }
                        )

                try:
                    self._run_ydl(url, ydl_opts, lambda ydl: ydl.download([url]))
                    finished_hook()
                    return
                except Exception as exc:
                    primary_error = exc
                    if self._is_instagram_url(url):
                        try:
                            self._download_instagram_with_gallery_dl(url, progress_hook, filename_suffix, overwrite, info)
                            finished_hook()
                            return
                        except Exception as gallery_exc:
                            instagram_gallery_error = gallery_exc
                    raise primary_error
            except Exception as e:
                if self._is_instagram_url(url):
                    message = self._build_instagram_failure_message(url, e, instagram_gallery_error)
                else:
                    message = str(e)
                if "ffmpeg" in message.lower() and self.ffmpeg_location is None:
                    message += " | ffmpeg is missing, so merge/convert failed."
                error_callback(message)

        thread = threading.Thread(target=download, daemon=True)
        thread.start()
        return thread


if __name__ == "__main__":
    dl = Downloader()

    def on_info(info):
        print(f"Title: {info.get('title')}")

    def on_error(err):
        print(f"Error: {err}")

    print("Fetching info for a test video...")
    dl.fetch_info("https://www.youtube.com/watch?v=BaW_jenozKc", on_info, on_error)

    import time

    time.sleep(3)
