import html
import json
import os
import re
import shutil
import threading
import urllib.request
from urllib.parse import parse_qs, parse_qsl, urlencode, urljoin, urlparse, urlunparse

import yt_dlp

try:
    from gallery_dl import config as gallery_config
    from gallery_dl import job as gallery_job
except ImportError:
    gallery_config = None
    gallery_job = None


class Downloader:
    BROWSER_COOKIE_SOURCES = (
        ("edge", ("LOCALAPPDATA", "Microsoft", "Edge", "User Data")),
        ("chrome", ("LOCALAPPDATA", "Google", "Chrome", "User Data")),
        ("brave", ("LOCALAPPDATA", "BraveSoftware", "Brave-Browser", "User Data")),
        ("firefox", ("APPDATA", "Mozilla", "Firefox", "Profiles")),
    )
    NAVER_BLOG_HOSTS = ("blog.naver.com", "m.blog.naver.com")
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

    def _download_text(self, url, headers=None):
        request_headers = dict(self.DEFAULT_REQUEST_HEADERS)
        if headers:
            request_headers.update(headers)

        request = urllib.request.Request(url, headers=request_headers)
        with urllib.request.urlopen(request) as response:
            payload = response.read()
            charset = response.headers.get_content_charset() or "utf-8"

        try:
            return payload.decode(charset, errors="replace")
        except LookupError:
            return payload.decode("utf-8", errors="replace")

    def _download_json_url(self, url, headers=None):
        return json.loads(self._download_text(url, headers=headers))

    def _clean_text(self, value):
        text = html.unescape(value or "")
        return re.sub(r"\s+", " ", text).strip()

    def _int_or_none(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _safe_filename(self, name, fallback="video"):
        cleaned = re.sub(r'[<>:"/\\|?*]+', "_", self._clean_text(name))
        cleaned = cleaned.strip(" .")
        return cleaned or fallback

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

        normalized["title"] = title
        normalized["thumbnail"] = self._extract_thumbnail_url(normalized)
        normalized["duration"] = normalized.get("duration") or (primary.get("duration") if primary else None)
        normalized.setdefault("formats", [])
        normalized.setdefault("webpage_url", url)
        normalized.setdefault("extractor", "instagram")
        return normalized

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

    def _naver_blog_outtmpl(self, entry, index, total):
        prefix = f"{index:03d}_" if total > 1 else ""
        safe_title = self._safe_filename(entry.get("title") or entry.get("post_title") or f"naver_blog_{index}")
        return os.path.join(self.download_dir, f"{prefix}{safe_title}.%(ext)s")

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

    def _download_instagram_with_gallery_dl(self, url, progress_hook):
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

    def fetch_info(self, url, info_callback, error_callback):
        """Fetches video info asynchronously."""

        def fetch():
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

    def _download_naver_blog_post(self, url, format_type, resolution, progress_hook, overwrite):
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
                "outtmpl": self._naver_blog_outtmpl(entry, index, total_entries),
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
    ):
        """Starts download asynchronously."""

        def download():
            instagram_gallery_error = None
            primary_error = None
            try:
                self._ensure_download_dir()

                if self._is_naver_blog_url(url):
                    self._download_naver_blog_post(url, format_type, resolution, progress_hook, overwrite)
                    finished_hook()
                    return

                is_playlist = self._is_playlist_url(url)
                has_ffmpeg = self.ffmpeg_location is not None

                base_outtmpl = (
                    os.path.join(self.download_dir, "%(playlist_index)03d_%(title)s.%(ext)s")
                    if is_playlist
                    else os.path.join(self.download_dir, "%(title)s.%(ext)s")
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
                            self._download_instagram_with_gallery_dl(url, progress_hook)
                            finished_hook()
                            return
                        except Exception as gallery_exc:
                            instagram_gallery_error = gallery_exc
                    raise primary_error
            except Exception as e:
                message = str(e)
                if instagram_gallery_error is not None:
                    message = f"yt-dlp failed: {message} | gallery-dl failed: {instagram_gallery_error}"
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