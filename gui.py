import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, font as tkfont
from PIL import Image, ImageOps
import threading
import urllib.request
import io
import queue
import os
import glob
import re
import json
import time
import sys
import webbrowser
from datetime import datetime

from downloader import Downloader

# Windows DPI awareness is enabled in main.py before tkinter starts.
# Keep customtkinter from re-scaling every widget when crossing monitors;
# that automatic full-window re-layout is what makes dual-monitor dragging lag.
if sys.platform == "win32":
    ctk.deactivate_automatic_dpi_awareness()
    ctk.set_widget_scaling(1.0)
    ctk.set_window_scaling(1.0)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    FONT_SIZE_OPTIONS = {
        "Normal": 1.10,
        "Large": 1.25,
        "XL": 1.35,
        "XXL": 1.50,
    }
    DEFAULT_FONT_SIZE_LABEL = "XL"

    def __init__(self, initial_url=None):
        super().__init__()

        self.colors = {
            "bg_app": "#101319",
            "panel": "#181d25",
            "surface": "#202633",
            "surface_2": "#2a3241",
            "surface_3": "#364154",
            "border": "#3f4a5e",
            "text_primary": "#F4F7FB",
            "text_secondary": "#A9B3C4",
            "accent": "#2F8CFF",
            "accent_hover": "#1B78EA",
            "success": "#31C26B",
            "warning": "#F4B23F",
            "danger": "#FF5A73",
        }

        app_dir = os.path.join(os.path.expanduser("~"), ".new_youtube_downloader")
        os.makedirs(app_dir, exist_ok=True)
        self.history_file = os.path.join(app_dir, "download_history.json")
        self.settings_file = os.path.join(app_dir, "settings.json")
        self.settings = self.load_settings()

        self.ui_font_family = self._resolve_ui_font_family()
        self._font_registry = []
        self.font_size_label = self._font_size_label_from_settings()
        self.font_scale = self.FONT_SIZE_OPTIONS[self.font_size_label]
        self.font_size_var = tk.StringVar(value=self.font_size_label)
        self.font_h1 = self._make_font(28, weight="bold")
        self.font_h2 = self._make_font(18, weight="bold")
        self.font_body = self._make_font(13)
        self.font_small = self._make_font(12)
        self.font_release = self._make_font(11)
        self.font_metric = self._make_font(18, weight="bold")
        self.font_url_entry = self._make_font(15)
        self.font_primary_button = self._make_font(17, weight="bold")
        self.font_badge = self._make_font(11, weight="bold")
        self.font_link = self._make_font(11, underline=True)
        self.font_preview_title = self._make_video_title_font(17, weight="bold")
        self.font_live_title = self._make_video_title_font(13, weight="bold")
        self.font_item_title = self._make_video_title_font(14, weight="bold")

        self.configure(fg_color=self.colors["bg_app"])

        self.release_version, self.release_updated_at = self._load_release_metadata()

        self.title("Video Downloader")
        self._apply_window_icon()
        self.geometry("1040x860")
        self.minsize(920, 700)
        self.resizable(True, True)

        self.downloader = Downloader()
        self.current_info = None
        self.current_thumbnail_token = 0
        self.info_request_token = 0
        
        self.download_queue = []
        self.is_downloading = False
        self.current_download_item = None
        self.active_download_thread = None
        self.active_download_callback_pending = False
        self.active_download_started_at = 0.0
        self.active_download_last_event_at = 0.0
        self._last_progress_dispatch_at = 0.0
        self._last_progress_value = -1.0
        self._ui_task_queue = queue.Queue()
        self.history_query_var = tk.StringVar(value="")
        
        self.history = self.load_history()
        self.default_download_path = self.resolve_default_download_path()
        self.downloader.download_dir = self.default_download_path

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Tabview ---
        self.tabview = ctk.CTkTabview(self, corner_radius=18, fg_color=self.colors["panel"])
        self.tabview.grid(row=0, column=0, padx=18, pady=18, sticky="nsew")
        self.tabview.configure(
            segmented_button_fg_color=self.colors["surface_2"],
            segmented_button_selected_color=self.colors["accent"],
            segmented_button_selected_hover_color=self.colors["accent_hover"],
            segmented_button_unselected_color=self.colors["surface_2"],
            segmented_button_unselected_hover_color=self.colors["surface_3"],
            text_color=self.colors["text_primary"],
        )
        self.tabview.add("Downloader")
        self.tabview.add("History")

        self.setup_downloader_tab()
        self.setup_history_tab()
        self.after(100, self._maximize_on_launch)
        self.bind("<Control-l>", self.focus_url_entry)
        self.bind("<Control-L>", self.focus_url_entry)
        self.bind("<Return>", self.handle_enter_key)
        self.after(50, self._drain_ui_task_queue)
        self.after(500, self._monitor_active_download)

        if initial_url:
            self.after(500, lambda: self.auto_start_download_from_url(initial_url))

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving history: {e}")

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_settings(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def _font_size_label_from_settings(self):
        label = str(self.settings.get("font_size", "")).strip()
        if label in self.FONT_SIZE_OPTIONS:
            return label

        legacy_scale = self.settings.get("font_scale")
        try:
            legacy_scale = float(legacy_scale)
        except (TypeError, ValueError):
            legacy_scale = None

        if legacy_scale:
            return min(
                self.FONT_SIZE_OPTIONS,
                key=lambda option: abs(self.FONT_SIZE_OPTIONS[option] - legacy_scale),
            )

        return self.DEFAULT_FONT_SIZE_LABEL

    def _make_font(self, size, weight=None, underline=False):
        font = ctk.CTkFont(
            family=self.ui_font_family,
            size=self._scaled_size(size),
            weight=weight,
            underline=underline,
        )
        self._font_registry.append((font, size, False))
        return font

    def _make_video_title_font(self, size, weight=None, underline=False):
        font = ctk.CTkFont(
            family=self.ui_font_family,
            size=self._video_title_size(size),
            weight=weight,
            underline=underline,
        )
        self._font_registry.append((font, size, True))
        return font

    def _apply_registered_font_scale(self):
        for font, base_size, is_video_title in list(self._font_registry):
            try:
                size = self._video_title_size(base_size) if is_video_title else self._scaled_size(base_size)
                font.configure(size=size)
            except Exception:
                continue

    def on_font_size_change(self, selected_label):
        if selected_label not in self.FONT_SIZE_OPTIONS:
            return

        self.font_size_label = selected_label
        self.font_scale = self.FONT_SIZE_OPTIONS[selected_label]
        self.settings["font_size"] = selected_label
        self.settings["font_scale"] = self.font_scale
        self.save_settings()
        self._apply_registered_font_scale()
        self.update_idletasks()


    def _resolve_ui_font_family(self):
        preferred = [
            "Pretendard",
            "SUIT",
            "Noto Sans KR",
            "NanumGothic",
            "Malgun Gothic",
            "Segoe UI",
            "Inter",
        ]

        try:
            available = {name.lower(): name for name in tkfont.families(self)}
        except Exception:
            return "Malgun Gothic"

        for family in preferred:
            found = available.get(family.lower())
            if found:
                return found

        return "TkDefaultFont"

    def _scaled_size(self, size):
        return max(1, int(round(size * self.font_scale)))

    def _video_title_size(self, size):
        return max(1, int(round(size * self.font_scale * 0.7)))

    def _resource_path(self, *parts):
        if getattr(sys, "frozen", False):
            base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, *parts)

    def _apply_window_icon(self):
        icon_path = self._resource_path("assets", "VideoDownloader.ico")
        if not os.path.exists(icon_path):
            return

        try:
            self.iconbitmap(icon_path)
            self.iconbitmap(default=icon_path)
        except Exception as exc:
            print(f"Failed to set window icon: {exc}")

    def _maximize_on_launch(self):
        try:
            if sys.platform == "win32":
                self.state("zoomed")
            else:
                self.attributes("-zoomed", True)
        except Exception:
            try:
                self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
            except Exception as exc:
                print(f"Failed to maximize window: {exc}")

    def _load_release_metadata(self):
        version = "?"
        updated_at = ""
        version_path = self._resource_path("VERSION")

        if os.path.exists(version_path):
            try:
                with open(version_path, "r", encoding="utf-8") as version_file:
                    version_text = version_file.read().strip()
                if version_text:
                    version = version_text
            except Exception:
                pass

            try:
                updated_at = datetime.fromtimestamp(os.path.getmtime(version_path)).strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

        return version, updated_at

    def _release_info_text(self):
        lines = [f"Version v{self.release_version}"]
        if self.release_updated_at:
            lines.append(f"Updated {self.release_updated_at}")
        return "\n".join(lines)


    def resolve_default_download_path(self):
        configured = self.settings.get("download_path", "").strip()
        fallback = os.path.join(os.path.expanduser("~"), "Downloads", "Video Downloader")
        candidates = [
            configured,
            fallback,
            os.path.join(os.path.expanduser("~"), ".new_youtube_downloader", "downloads")
        ]

        for candidate in candidates:
            if not candidate:
                continue
            try:
                os.makedirs(candidate, exist_ok=True)
                self.settings["download_path"] = candidate
                self.save_settings()
                return candidate
            except Exception:
                continue

        return "downloads"

    def show_status(self, message, color="#8E8E93", clear_after_ms=None):
        if hasattr(self, "status_label") and self.status_label.winfo_exists():
            self.status_label.configure(text=message, text_color=color)
            if clear_after_ms:
                self.after(clear_after_ms, lambda: self.status_label.configure(text=""))

    def _prepare_thumbnail_image(self, image, size):
        resampling = getattr(Image, "Resampling", Image)
        image = ImageOps.exif_transpose(image).convert("RGB")
        return ImageOps.fit(image, size, method=resampling.LANCZOS, centering=(0.5, 0.5))

    def _clear_ctk_label_image(self, label):
        if not label or not label.winfo_exists():
            return

        try:
            label.configure(image=None)
        except Exception:
            pass

        tk_label = getattr(label, "_label", None)
        if tk_label and tk_label.winfo_exists():
            try:
                tk_label.configure(image="")
            except Exception:
                pass

        try:
            label.image = None
        except Exception:
            pass

    def _set_thumbnail_placeholder(self, label, text="No Preview"):
        if label and label.winfo_exists():
            self._clear_ctk_label_image(label)
            try:
                label.configure(text=text)
            except (RuntimeError, tk.TclError):
                return
            label.image = None

    def _dispatch_to_ui(self, callback, *args):
        if threading.current_thread() is threading.main_thread():
            callback(*args)
            return
        self._ui_task_queue.put((callback, args))

    def _drain_ui_task_queue(self):
        processed = 0
        max_tasks_per_tick = 12

        try:
            while processed < max_tasks_per_tick:
                callback, args = self._ui_task_queue.get_nowait()
                try:
                    callback(*args)
                except Exception as exc:
                    print(f"UI task error: {exc}")
                processed += 1
        except queue.Empty:
            pass

        try:
            if self.winfo_exists():
                delay = 16 if not self._ui_task_queue.empty() else 50
                self.after(delay, self._drain_ui_task_queue)
        except (RuntimeError, tk.TclError):
            pass

    def _mark_download_activity(self):
        self.active_download_last_event_at = time.monotonic()

    def _reset_active_download(self):
        self.active_download_thread = None
        self.active_download_callback_pending = False
        self.active_download_started_at = 0.0
        self.active_download_last_event_at = 0.0
        self._last_progress_dispatch_at = 0.0
        self._last_progress_value = -1.0

    def _dispatch_progress_update(self, pct, speed, eta, playlist_info=""):
        now = time.monotonic()
        last_pct = getattr(self, "_last_progress_value", -1.0)
        last_at = getattr(self, "_last_progress_dispatch_at", 0.0)

        significant_change = last_pct < 0 or pct >= 100 or pct <= last_pct or (pct - last_pct) >= 1.0
        interval_elapsed = (now - last_at) >= 0.15

        if not significant_change and not interval_elapsed:
            return

        self._last_progress_dispatch_at = now
        self._last_progress_value = pct
        self._dispatch_to_ui(self.update_progress, pct, speed, eta, playlist_info)

    def _monitor_active_download(self):
        try:
            if not self.winfo_exists():
                return

            if self.is_downloading and self.current_download_item:
                worker = getattr(self, "active_download_thread", None)
                item = self.current_download_item
                if worker and not worker.is_alive():
                    if getattr(self, "active_download_callback_pending", False):
                        self.after(500, self._monitor_active_download)
                        return
                    last_event = self.active_download_last_event_at or self.active_download_started_at
                    idle_for = time.monotonic() - last_event if last_event else 0.0
                    if idle_for >= 2.0 and item.get("status") in ("Downloading", "Processing..."):
                        recovered_path = ""
                        last_path = getattr(self, "last_downloaded_file", "")
                        if last_path and os.path.exists(last_path):
                            recovered_path = last_path
                        if not recovered_path:
                            recovered_path = self._resolve_queue_item_path(item)

                        if recovered_path:
                            print(f"Queue watchdog recovered finished item: {item.get('title', 'Unknown')}")
                            self.last_downloaded_file = recovered_path
                            self._finish_ui()
                            return

                        print(f"Queue watchdog advancing after stalled item: {item.get('title', 'Unknown')}")
                        self._handle_download_error_ui(
                            "Download worker exited before the queue advanced. The item was marked as failed so the next queued download can continue."
                        )
                        return

            self.after(500, self._monitor_active_download)
        except (RuntimeError, tk.TclError):
            pass

    def _live_download_caption(self, item):
        status = item.get("status", "Waiting")
        return "Now Downloading" if status in ("Downloading", "Processing...") else "Last Queue Item"

    def _live_download_detail(self, item):
        status = item.get("status", "Waiting")
        if status == "Downloading":
            prefix = item.get("playlist_info", "")
            pct = item.get("progress", 0.0)
            speed = item.get("speed") or "N/A"
            eta = item.get("eta") or "N/A"
            return f"{prefix}{pct:.1f}% | {speed} | ETA {eta}"
        if status == "Processing...":
            return "Processing downloaded file..."
        if status == "Finished":
            return "Finished | Ready to open"
        if status == "Error":
            return "Download failed | Check the message above"
        return status

    def _refresh_live_download_card(self, item=None):
        if not hasattr(self, "live_download_frame") or not self.live_download_frame.winfo_exists():
            return

        active_item = item or getattr(self, "current_download_item", None)
        if not active_item:
            self.live_download_frame.grid_forget()
            return

        if not self.live_download_frame.winfo_ismapped():
            self.live_download_frame.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="ew")

        status = active_item.get("status", "Waiting")
        progress = active_item.get("progress", 0.0) or 0.0
        if status in ("Processing...", "Finished"):
            progress = max(progress, 100.0)

        self.live_download_caption_label.configure(text=self._live_download_caption(active_item))
        self.live_download_title_label.configure(text=active_item.get("title", "Unknown"))
        detail_color = self.colors["danger"] if status == "Error" else self.colors["text_secondary"]
        self.live_download_detail_label.configure(text=self._live_download_detail(active_item), text_color=detail_color)
        self.live_download_progress.configure(progress_color=self._queue_progress_color(status))
        self.live_download_progress.set(max(0.0, min(progress / 100.0, 1.0)))

    def _overwrite_policy_label(self, policy_value):
        mapping = {
            "ask": "중복 시 물어보기",
            "rename": "자동 이름 변경",
            "overwrite": "항상 덮어쓰기",
            "skip": "항상 건너뛰기",
        }
        return mapping.get(policy_value, mapping["ask"])

    def _overwrite_policy_value(self, policy_label):
        mapping = {
            "중복 시 물어보기": "ask",
            "자동 이름 변경": "rename",
            "항상 덮어쓰기": "overwrite",
            "항상 건너뛰기": "skip",
        }
        return mapping.get(policy_label, "ask")

    def _queue_progress_color(self, status):
        if status == "Finished":
            return self.colors["success"]
        if status == "Error":
            return self.colors["danger"]
        return self.colors["accent"]

    def _queue_status_badge_style(self, status):
        if status == "Finished":
            return ("#1F5B39", "#B7F7CF")
        if status == "Downloading":
            return ("#1E4E82", "#CFE6FF")
        if status == "Processing...":
            return ("#6E4E1F", "#FFE3B3")
        if status == "Error":
            return ("#6E2432", "#FFD7DF")
        return ("#374153", "#D8E1F0")

    def _normalize_title_for_filename(self, title):
        normalized = re.sub(r'[<>:"/\\|?*]', "_", (title or "").strip())
        normalized = normalized.rstrip(". ")
        return normalized or "Unknown"
    def _find_existing_files_for_info(self, download_dir, info):
        if not download_dir or not info:
            return []

        titles = []
        if info.get("is_playlist"):
            for entry in info.get("entries") or []:
                if isinstance(entry, dict) and entry.get("title"):
                    titles.append(entry["title"])
        elif info.get("title"):
            titles.append(info["title"])

        existing = []
        seen = set()
        for title in titles:
            safe_title = self._normalize_title_for_filename(title)
            escaped_title = glob.escape(safe_title)
            patterns = [
                os.path.join(download_dir, f"{escaped_title}.*"),
                os.path.join(download_dir, f"{escaped_title}*.*"),
                os.path.join(download_dir, f"*_{escaped_title}.*"),
                os.path.join(download_dir, f"*_{escaped_title}*.*"),
            ]
            for pattern in patterns:
                for path in glob.glob(pattern):
                    norm = os.path.normcase(os.path.abspath(path))
                    if norm not in seen:
                        seen.add(norm)
                        existing.append(path)

        return existing

    def _find_existing_files_for_url(self, download_dir, url):
        if not download_dir or not url:
            return []

        target_dir = os.path.normcase(os.path.abspath(download_dir))
        existing = []
        seen = set()
        for record in reversed(self.history):
            if (record.get("url") or "").strip() != url:
                continue
            record_path = (record.get("path") or "").strip()
            if not record_path:
                continue
            abs_path = os.path.abspath(record_path)
            if not os.path.isfile(abs_path):
                continue
            if os.path.normcase(os.path.dirname(abs_path)) != target_dir:
                continue
            norm = os.path.normcase(abs_path)
            if norm in seen:
                continue
            seen.add(norm)
            existing.append(abs_path)

        return existing

    def _collect_existing_files(self, download_dir, info, url=""):
        existing = []
        existing.extend(self._find_existing_files_for_info(download_dir, info))
        existing.extend(self._find_existing_files_for_url(download_dir, url))

        unique = []
        seen = set()
        for path in existing:
            norm = os.path.normcase(os.path.abspath(path))
            if norm in seen:
                continue
            seen.add(norm)
            unique.append(path)

        return unique

    def _next_duplicate_filename_suffix(self, existing_files):
        used_numbers = {0}
        for path in existing_files:
            stem = os.path.splitext(os.path.basename(path))[0]
            match = re.search(r" \((\d+)\)$", stem)
            if match:
                try:
                    used_numbers.add(int(match.group(1)))
                except ValueError:
                    pass
            else:
                used_numbers.add(0)

        next_number = 1
        while next_number in used_numbers:
            next_number += 1
        return f" ({next_number})"

    def _prompt_overwrite_for_existing(self, existing_files):
        preview = "\n".join(f"- {os.path.basename(p)}" for p in existing_files[:5])
        more = f"\n... 외 {len(existing_files) - 5}개" if len(existing_files) > 5 else ""
        return messagebox.askyesno(
            "파일 덮어쓰기 확인",
            (
                "같은 제목의 파일이 이미 있습니다.\n\n"
                f"{preview}{more}\n\n"
                "기존 파일을 덮어쓸까요?"
            ),
        )
    def _select_all_url(self, event):
        self.after(50, lambda: self.url_entry.select_range(0, "end"))
    def focus_url_entry(self, event=None):
        if hasattr(self, "url_entry") and self.url_entry.winfo_exists():
            self.url_entry.focus_set()
            self.url_entry.select_range(0, "end")
        return "break"

    def handle_enter_key(self, event=None):
        if not hasattr(self, "tabview") or self.tabview.get() != "Downloader":
            return None
        if hasattr(self, "download_btn") and self.download_btn.cget("state") == "normal":
            self.start_download()
            return "break"
        return None

    def _queue_info_text(self, item, status=None):
        status_text = status or item.get("status", "Waiting")
        parts = [item.get("type", "Video"), item.get("res", "Best")]
        queued_at = item.get("queued_at")
        if queued_at:
            parts.append(f"Queued {queued_at}")
        if item.get("speed"):
            parts.append(item["speed"])
        if item.get("eta"):
            parts.append(f"ETA {item['eta']}")
        parts.append(status_text)
        return " | ".join(parts)

    def _build_metric_card(self, parent, column, label, value):
        card = ctk.CTkFrame(
            parent,
            fg_color=self.colors["surface"],
            corner_radius=12,
            border_width=1,
            border_color=self.colors["border"],
        )
        card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0 if column == 2 else 6))
        card.grid_columnconfigure(0, weight=1)

        value_label = ctk.CTkLabel(
            card,
            text=value,
            font=self.font_metric,
            text_color=self.colors["text_primary"],
        )
        value_label.grid(row=0, column=0, padx=10, pady=(8, 0))

        ctk.CTkLabel(
            card,
            text=label,
            font=self.font_small,
            text_color=self.colors["text_secondary"],
        ).grid(row=1, column=0, padx=10, pady=(0, 8))

        return value_label

    def _today_history_count(self):
        today = datetime.now().date()
        count = 0
        for record in self.history:
            date_text = record.get("date", "")
            try:
                recorded_at = datetime.strptime(date_text, "%Y-%m-%d %H:%M:%S").date()
            except Exception:
                continue
            if recorded_at == today:
                count += 1
        return count

    def refresh_dashboard_metrics(self):
        stats = self._queue_stats() if hasattr(self, "download_queue") else {"done": 0, "error": 0}
        attempted = stats.get("done", 0) + stats.get("error", 0)
        success_rate = 100 if attempted == 0 else int(round((stats.get("done", 0) / attempted) * 100))

        if hasattr(self, "metric_total_value") and self.metric_total_value.winfo_exists():
            self.metric_total_value.configure(text=str(len(self.history)))
        if hasattr(self, "metric_today_value") and self.metric_today_value.winfo_exists():
            self.metric_today_value.configure(text=str(self._today_history_count()))
        if hasattr(self, "metric_success_value") and self.metric_success_value.winfo_exists():
            self.metric_success_value.configure(text=f"{success_rate}%")
    def setup_downloader_tab(self):
        tab = self.tabview.tab("Downloader")
        tab.grid_columnconfigure(0, weight=5)
        tab.grid_columnconfigure(1, weight=4)
        tab.grid_rowconfigure(1, weight=1)

        self.header_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, columnspan=2, padx=28, pady=(8, 14), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="Video Downloader",
            font=self.font_h1,
            text_color=self.colors["text_primary"],
        )
        self.title_label.grid(row=0, column=0, pady=(6, 2))

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Fast queue workflow with smart duplicate handling",
            font=self.font_small,
            text_color=self.colors["text_secondary"],
        )
        self.subtitle_label.grid(row=1, column=0, pady=(0, 4))

        self.release_info_label = ctk.CTkLabel(
            self.header_frame,
            text=self._release_info_text(),
            font=self.font_release,
            text_color=self.colors["text_secondary"],
            justify="right",
            anchor="e",
        )
        self.release_info_label.place(relx=1.0, x=-4, y=46, anchor="ne")

        self.font_size_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.font_size_frame.place(relx=1.0, x=-4, y=4, anchor="ne")
        ctk.CTkLabel(
            self.font_size_frame,
            text="Font",
            font=self.font_small,
            text_color=self.colors["text_secondary"],
        ).grid(row=0, column=0, padx=(0, 8), sticky="e")
        self.font_size_menu = ctk.CTkOptionMenu(
            self.font_size_frame,
            values=list(self.FONT_SIZE_OPTIONS.keys()),
            variable=self.font_size_var,
            command=self.on_font_size_change,
            font=self.font_small,
            dropdown_font=self.font_small,
            fg_color=self.colors["surface_2"],
            button_color=self.colors["surface_3"],
            button_hover_color=self.colors["border"],
            corner_radius=10,
            width=112,
            height=38,
        )
        self.font_size_menu.grid(row=0, column=1, sticky="e")

        self.main_column = ctk.CTkFrame(tab, fg_color="transparent")
        self.main_column.grid(row=1, column=0, padx=(28, 14), pady=(0, 18), sticky="nsew")
        self.main_column.grid_columnconfigure(0, weight=1)

        self.queue_panel = ctk.CTkFrame(
            tab,
            fg_color=self.colors["surface"],
            corner_radius=18,
            border_width=1,
            border_color=self.colors["border"],
        )
        self.queue_panel.grid(row=1, column=1, padx=(14, 28), pady=(0, 18), sticky="nsew")
        self.queue_panel.grid_columnconfigure(0, weight=1)
        self.queue_panel.grid_rowconfigure(1, weight=1)

        self.url_var = tk.StringVar()
        self.url_var.trace_add("write", self.on_url_change)

        self.url_entry = ctk.CTkEntry(
            self.main_column,
            textvariable=self.url_var,
            placeholder_text="Paste video URL here",
            height=50,
            corner_radius=24,
            fg_color=self.colors["surface"],
            border_width=1,
            border_color=self.colors["border"],
            text_color=self.colors["text_primary"],
            font=self.font_url_entry,
        )
        self.url_entry.grid(row=0, column=0, pady=(0, 14), sticky="ew")
        self.url_entry.bind("<FocusIn>", self._select_all_url)
        self.url_entry.bind("<Button-1>", self._select_all_url)

        self.info_frame = ctk.CTkFrame(
            self.main_column,
            fg_color=self.colors["surface"],
            corner_radius=16,
            border_width=1,
            border_color=self.colors["border"],
        )
        self.info_frame.grid_columnconfigure(1, weight=1)

        self.thumbnail_label = ctk.CTkLabel(
            self.info_frame,
            text="No Preview",
            width=120,
            height=90,
            corner_radius=10,
            fg_color=self.colors["surface_2"],
            text_color=self.colors["text_secondary"],
            font=self.font_small,
        )
        self.thumbnail_label.grid(row=0, column=0, rowspan=3, padx=12, pady=12)

        self.video_title = ctk.CTkLabel(
            self.info_frame,
            text="Title",
            font=self.font_preview_title,
            text_color=self.colors["text_primary"],
            anchor="w",
            justify="left",
            wraplength=420,
        )
        self.video_title.grid(row=0, column=1, padx=(4, 14), pady=(12, 2), sticky="w")

        self.video_duration = ctk.CTkLabel(
            self.info_frame,
            text="Duration",
            font=self.font_small,
            text_color=self.colors["text_secondary"],
            anchor="w",
        )
        self.video_duration.grid(row=1, column=1, padx=(4, 14), pady=(0, 10), sticky="w")

        self.settings_container = ctk.CTkFrame(
            self.main_column,
            fg_color=self.colors["surface"],
            corner_radius=16,
            border_width=1,
            border_color=self.colors["border"],
        )
        self.settings_container.grid(row=2, column=0, pady=(0, 16), sticky="ew")
        self.settings_container.grid_columnconfigure(0, weight=1)

        self.settings_title = ctk.CTkLabel(
            self.settings_container,
            text="Download Settings",
            font=self.font_h2,
            text_color=self.colors["text_primary"],
        )
        self.settings_title.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))

        self.options_frame = ctk.CTkFrame(self.settings_container, fg_color="transparent")
        self.options_frame.grid(row=1, column=0, pady=(2, 8), padx=16, sticky="ew")
        self.options_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(self.options_frame, text="Type", font=self.font_small, text_color=self.colors["text_secondary"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(self.options_frame, text="Quality", font=self.font_small, text_color=self.colors["text_secondary"]).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(self.options_frame, text="Subtitles", font=self.font_small, text_color=self.colors["text_secondary"]).grid(row=0, column=2, sticky="w")

        self.type_var = tk.StringVar(value="Video")
        self.type_menu = ctk.CTkOptionMenu(
            self.options_frame,
            values=["Video", "Audio"],
            variable=self.type_var,
            command=self.on_type_change,
            font=self.font_body,
            dropdown_font=self.font_body,
            fg_color=self.colors["surface_2"],
            button_color=self.colors["surface_3"],
            button_hover_color=self.colors["border"],
            corner_radius=10,
            height=34,
        )
        self.type_menu.grid(row=1, column=0, padx=(0, 8), pady=(4, 0), sticky="ew")

        self.res_var = tk.StringVar(value="Best")
        self.res_menu = ctk.CTkOptionMenu(
            self.options_frame,
            values=["Best", "1080p", "720p", "480p", "360p"],
            variable=self.res_var,
            font=self.font_body,
            dropdown_font=self.font_body,
            fg_color=self.colors["surface_2"],
            button_color=self.colors["surface_3"],
            button_hover_color=self.colors["border"],
            corner_radius=10,
            height=34,
        )
        self.res_menu.grid(row=1, column=1, padx=8, pady=(4, 0), sticky="ew")

        self.subtitles_var = tk.BooleanVar(value=self.settings.get("subtitles", False))
        self.subtitles_checkbox = ctk.CTkCheckBox(
            self.options_frame,
            text="KO/EN",
            variable=self.subtitles_var,
            font=self.font_body,
            command=self.save_options,
            checkbox_height=24,
            checkbox_width=24,
        )
        self.subtitles_checkbox.grid(row=1, column=2, padx=(8, 0), pady=(7, 0), sticky="w")

        self.auto_dl_var = tk.BooleanVar(value=self.settings.get("auto_download", True))
        self.auto_dl_checkbox = ctk.CTkCheckBox(
            self.options_frame,
            text="Auto download when URL is pasted",
            variable=self.auto_dl_var,
            font=self.font_body,
            command=self.save_options,
        )
        self.auto_dl_checkbox.grid(row=2, column=0, columnspan=3, pady=(10, 0), sticky="w")

        self.overwrite_policy_var = tk.StringVar(
            value=self._overwrite_policy_label(self.settings.get("overwrite_policy", "ask"))
        )
        ctk.CTkLabel(self.options_frame, text="Duplicates", font=self.font_small, text_color=self.colors["text_secondary"]).grid(row=3, column=0, sticky="w", pady=(10, 2))
        self.overwrite_policy_menu = ctk.CTkOptionMenu(
            self.options_frame,
            values=["중복 시 물어보기", "자동 이름 변경", "항상 덮어쓰기", "항상 건너뛰기"],
            variable=self.overwrite_policy_var,
            command=lambda _: self.save_options(),
            font=self.font_body,
            dropdown_font=self.font_body,
            fg_color=self.colors["surface_2"],
            button_color=self.colors["surface_3"],
            button_hover_color=self.colors["border"],
            corner_radius=10,
            height=34,
        )
        self.overwrite_policy_menu.grid(row=4, column=0, columnspan=3, pady=(0, 0), sticky="ew")

        self.path_frame = ctk.CTkFrame(self.settings_container, fg_color="transparent")
        self.path_frame.grid(row=2, column=0, pady=(8, 14), padx=16, sticky="ew")
        self.path_frame.grid_columnconfigure(0, weight=1)

        self.path_label = ctk.CTkLabel(
            self.path_frame,
            text="Save path",
            font=self.font_small,
            text_color=self.colors["text_secondary"],
        )
        self.path_label.grid(row=0, column=0, columnspan=3, sticky="w", padx=(0, 10))

        default_path = self.default_download_path
        self.path_var = tk.StringVar(value=default_path)
        self.path_entry = ctk.CTkEntry(
            self.path_frame,
            textvariable=self.path_var,
            height=36,
            corner_radius=10,
            fg_color=self.colors["surface_2"],
            border_width=1,
            border_color=self.colors["border"],
            state="disabled",
            text_color=self.colors["text_primary"],
            font=self.font_body,
        )
        self.path_entry.grid(row=1, column=0, padx=(0, 10), pady=(5, 0), sticky="ew")

        self.browse_btn = ctk.CTkButton(
            self.path_frame,
            text="Browse",
            width=84,
            height=36,
            corner_radius=10,
            font=self.font_body,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            command=self.browse_path,
        )
        self.browse_btn.grid(row=1, column=1, padx=(0, 10), pady=(5, 0))

        self.open_folder_btn = ctk.CTkButton(
            self.path_frame,
            text="Open Folder",
            width=110,
            height=36,
            corner_radius=10,
            font=self.font_body,
            command=self.open_download_folder,
            fg_color=self.colors["surface_2"],
            hover_color=self.colors["surface_3"],
            text_color=self.colors["text_primary"],
        )
        self.open_folder_btn.grid(row=1, column=2, pady=(5, 0))

        self.download_btn = ctk.CTkButton(
            self.main_column,
            text="Start Download",
            command=self.start_download,
            font=self.font_primary_button,
            height=52,
            width=250,
            corner_radius=26,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            text_color="#EBF4FF",
            text_color_disabled="#EBEBF5",
        )
        self.download_btn.grid(row=3, column=0, pady=(0, 12))

        self.status_frame = ctk.CTkFrame(
            self.main_column,
            fg_color=self.colors["surface"],
            corner_radius=12,
            border_width=1,
            border_color=self.colors["border"],
        )
        self.status_frame.grid(row=4, column=0, pady=(0, 10), sticky="ew")
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Ready",
            text_color=self.colors["text_secondary"],
            font=self.font_small,
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, padx=12, pady=(8, 4), sticky="w")

        self.live_download_frame = ctk.CTkFrame(
            self.status_frame,
            fg_color=self.colors["surface_2"],
            corner_radius=10,
        )
        self.live_download_frame.grid_columnconfigure(0, weight=1)

        self.live_download_caption_label = ctk.CTkLabel(
            self.live_download_frame,
            text="Now Downloading",
            text_color=self.colors["text_secondary"],
            font=self.font_small,
            anchor="w",
        )
        self.live_download_caption_label.grid(row=0, column=0, padx=12, pady=(10, 2), sticky="w")

        self.live_download_title_label = ctk.CTkLabel(
            self.live_download_frame,
            text="",
            font=self.font_live_title,
            text_color=self.colors["text_primary"],
            anchor="w",
            justify="left",
            wraplength=460,
        )
        self.live_download_title_label.grid(row=1, column=0, padx=12, pady=(0, 2), sticky="w")

        self.live_download_detail_label = ctk.CTkLabel(
            self.live_download_frame,
            text="",
            text_color=self.colors["text_secondary"],
            font=self.font_small,
            anchor="w",
        )
        self.live_download_detail_label.grid(row=2, column=0, padx=12, pady=(0, 8), sticky="w")

        self.live_download_progress = ctk.CTkProgressBar(
            self.live_download_frame,
            mode="determinate",
            height=8,
            progress_color=self.colors["accent"],
            fg_color=self.colors["surface_3"],
        )
        self.live_download_progress.grid(row=3, column=0, padx=12, pady=(0, 12), sticky="ew")
        self.live_download_progress.set(0)

        self.queue_header_frame = ctk.CTkFrame(self.queue_panel, fg_color="transparent")
        self.queue_header_frame.grid(row=0, column=0, padx=18, pady=(18, 8), sticky="ew")
        self.queue_header_frame.grid_columnconfigure(0, weight=1)

        self.queue_title_label = ctk.CTkLabel(
            self.queue_header_frame,
            text="Queue (0)",
            font=self.font_h2,
            text_color=self.colors["text_primary"],
            anchor="w",
        )
        self.queue_title_label.grid(row=0, column=0, sticky="w")

        self.queue_summary_label = ctk.CTkLabel(
            self.queue_header_frame,
            text="Queue is empty | Paste a URL to get started",
            font=self.font_small,
            text_color=self.colors["text_secondary"],
            anchor="w",
        )
        self.queue_summary_label.grid(row=1, column=0, sticky="w", pady=(0, 2))

        self.queue_actions_frame = ctk.CTkFrame(self.queue_header_frame, fg_color="transparent")
        self.queue_actions_frame.grid(row=0, column=1, rowspan=2, sticky="e")

        self.retry_errors_btn = ctk.CTkButton(
            self.queue_actions_frame,
            text="Retry Errors",
            width=106,
            height=30,
            corner_radius=10,
            font=self.font_small,
            fg_color=self.colors["surface_2"],
            hover_color=self.colors["surface_3"],
            text_color=self.colors["text_primary"],
            command=self.retry_error_items,
        )
        self.retry_errors_btn.grid(row=0, column=0, padx=(0, 8))

        self.clear_finished_btn = ctk.CTkButton(
            self.queue_actions_frame,
            text="Clear Done",
            width=96,
            height=30,
            corner_radius=10,
            font=self.font_small,
            fg_color=self.colors["surface_2"],
            hover_color=self.colors["surface_3"],
            text_color=self.colors["text_primary"],
            command=self.clear_finished_items,
        )
        self.clear_finished_btn.grid(row=0, column=1)

        self.queue_scroll = ctk.CTkScrollableFrame(
            self.queue_panel,
            corner_radius=16,
            fg_color=self.colors["panel"],
            border_width=1,
            border_color=self.colors["border"],
        )
        self.queue_scroll.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.queue_scroll.grid_columnconfigure(0, weight=1)

        self.on_type_change(self.type_var.get())
        self.refresh_queue_ui()
    def refresh_queue_ui(self):
        for widget in getattr(self, 'queue_scroll', ctk.CTkFrame(self)).winfo_children():
            widget.destroy()

        queue_count = len(getattr(self, 'download_queue', []))
        self.refresh_queue_header()

        if queue_count == 0:
            empty_frame = ctk.CTkFrame(
                self.queue_scroll,
                fg_color=self.colors["surface"],
                corner_radius=14,
                border_width=1,
                border_color=self.colors["border"],
            )
            empty_frame.grid(row=0, column=0, sticky="ew", pady=14, padx=8)
            ctk.CTkLabel(
                empty_frame,
                text="Queue is empty. Add a URL to get started.",
                text_color=self.colors["text_secondary"],
                font=self.font_body,
            ).grid(row=0, column=0, pady=22, padx=16)
            return

        for idx, item in enumerate(reversed(self.download_queue)):
            frame = ctk.CTkFrame(
                self.queue_scroll,
                fg_color=self.colors["surface"],
                corner_radius=14,
                border_width=1,
                border_color=self.colors["border"],
            )
            frame.grid(row=idx, column=0, sticky="ew", pady=6, padx=6)
            frame.grid_columnconfigure(1, weight=1)

            thumb_lbl = ctk.CTkLabel(
                frame,
                text="No Preview",
                width=96,
                height=54,
                corner_radius=10,
                fg_color=self.colors["surface_2"],
                text_color=self.colors["text_secondary"],
                font=self.font_small,
            )
            thumb_lbl.grid(row=0, column=0, rowspan=3, padx=(10, 8), pady=10, sticky="nw")

            thumb_url = item.get("thumbnail")
            item["thumbnail_label"] = thumb_lbl
            if thumb_url:
                cached_img = item.get("thumbnail_image")
                if cached_img:
                    thumb_lbl.configure(image=cached_img, text="")
                    thumb_lbl.image = cached_img
                elif item.get("thumbnail_loading"):
                    self._set_thumbnail_placeholder(thumb_lbl, "Loading...")
                else:
                    item["thumbnail_loading"] = True
                    self._set_thumbnail_placeholder(thumb_lbl, "Loading...")
                    threading.Thread(
                        target=self.load_queue_thumbnail,
                        args=(thumb_url, item),
                        daemon=True,
                    ).start()
            else:
                self._set_thumbnail_placeholder(thumb_lbl, "No Preview")

            title_lbl = ctk.CTkLabel(
                frame,
                text=item["title"],
                font=self.font_item_title,
                text_color=self.colors["text_primary"],
                anchor="w",
                justify="left",
                wraplength=320,
            )
            title_lbl.grid(row=0, column=1, sticky="w", padx=(0, 8), pady=(9, 2))

            badge_bg, badge_fg = self._queue_status_badge_style(item.get("status"))
            status_chip = ctk.CTkLabel(
                frame,
                text=item.get("status", "Waiting"),
                font=self.font_badge,
                fg_color=badge_bg,
                text_color=badge_fg,
                corner_radius=10,
                width=102,
                height=24,
            )
            status_chip.grid(row=0, column=2, padx=(0, 10), pady=(9, 2), sticky="e")
            info_text = self._queue_info_text(item)

            status_lbl = ctk.CTkLabel(
                frame,
                text=info_text,
                text_color=self.colors["text_secondary"],
                font=self.font_small,
                anchor="w",
                wraplength=320,
            )
            status_lbl.grid(row=1, column=1, sticky="w", padx=(0, 10), pady=(0, 8))

            action_btn = ctk.CTkButton(
                frame,
                text="...",
                width=84,
                height=28,
                corner_radius=8,
                font=self.font_small,
                fg_color=self.colors["surface_2"],
                hover_color=self.colors["surface_3"],
                text_color=self.colors["text_primary"],
                command=lambda i=item: self.open_item_folder(i),
            )
            action_btn.grid(row=1, column=2, padx=(0, 10), pady=(0, 8), sticky="e")

            prog_bar = ctk.CTkProgressBar(
                frame,
                mode="determinate",
                height=7,
                progress_color=self._queue_progress_color(item.get("status")),
                fg_color=self.colors["surface_3"],
            )
            prog_bar.grid(row=2, column=1, columnspan=2, sticky="ew", padx=(0, 10), pady=(0, 12))
            prog_bar.set(item['progress'] / 100)

            item['ui_frame'] = frame
            item['ui_status'] = status_lbl
            item['ui_chip'] = status_chip
            item['ui_prog'] = prog_bar
            item['ui_action'] = action_btn
            self._configure_queue_item_action(item)
    def update_queue_item_ui(self, item):
        status = item.get("status", "Waiting")

        if 'ui_status' in item and item['ui_status'].winfo_exists():
            item['ui_status'].configure(text=self._queue_info_text(item, status))

        if 'ui_chip' in item and item['ui_chip'].winfo_exists():
            badge_bg, badge_fg = self._queue_status_badge_style(status)
            item['ui_chip'].configure(text=status, fg_color=badge_bg, text_color=badge_fg)

        if 'ui_prog' in item and item['ui_prog'].winfo_exists():
            item['ui_prog'].configure(progress_color=self._queue_progress_color(status))
            item['ui_prog'].set(item['progress'] / 100)

        self._configure_queue_item_action(item)

    def _resolve_queue_item_path(self, item):
        explicit = (item.get("path") or "").strip()
        if explicit and os.path.exists(explicit):
            return explicit

        info = item.get("info") or {}
        search_dir = item.get("dir", "")
        existing = self._collect_existing_files(search_dir, info, item.get("url", ""))
        if existing:
            return max(existing, key=lambda p: os.path.getmtime(p))

        return ""
    def _configure_queue_item_action(self, item):
        button = item.get("ui_action")
        if not button or not button.winfo_exists():
            return

        status = item.get("status", "Waiting")
        if status == "Finished":
            button.configure(
                text="Open",
                state="normal",
                fg_color=self.colors["success"],
                hover_color="#249B57",
                text_color="#E9FFF1",
                command=lambda i=item: self.open_queue_item(i),
            )
            return

        if status == "Error":
            button.configure(
                text="Retry",
                state="normal",
                fg_color=self.colors["accent"],
                hover_color=self.colors["accent_hover"],
                text_color=self.colors["text_primary"],
                command=lambda i=item: self.retry_single_item(i),
            )
            return

        if status == "Waiting":
            button.configure(
                text="Remove",
                state="normal",
                fg_color=self.colors["surface_2"],
                hover_color=self.colors["surface_3"],
                text_color=self.colors["text_primary"],
                command=lambda i=item: self.remove_queue_item(i),
            )
            return

        button.configure(
            text="Live",
            state="disabled",
            fg_color=self.colors["surface_3"],
            hover_color=self.colors["surface_3"],
            text_color=self.colors["text_secondary"],
            command=lambda: None,
        )

    def open_item_folder(self, item):
        folder = item.get("dir", "")
        if folder and os.path.exists(folder):
            os.startfile(folder)

    def open_queue_item(self, item):
        path = self._resolve_queue_item_path(item)
        if path:
            item["path"] = path
            self.open_file_location(path)
            return

        folder = item.get("dir", "")
        if folder and os.path.exists(folder):
            os.startfile(folder)
            return

        self.show_status("열 수 있는 파일/폴더를 찾지 못했습니다.", self.colors["warning"], 4000)
    def retry_single_item(self, item):
        if item not in self.download_queue:
            return
        if item.get("status") != "Error":
            return

        item["status"] = "Waiting"
        item["progress"] = 0.0
        item["speed"] = ""
        item["eta"] = ""
        self.show_status(f"Retry queued: {item.get('title', 'Unknown')}", self.colors["accent"], 3000)
        self.update_queue_item_ui(item)
        self.refresh_queue_header()
        self._process_queue()

    def remove_queue_item(self, item):
        if item not in self.download_queue:
            return

        if (
            self.is_downloading
            and self.current_download_item is item
            and item.get("status") in ("Downloading", "Processing...")
        ):
            self.show_status("진행 중인 항목은 삭제할 수 없습니다.", self.colors["warning"], 3000)
            return

        title = item.get("title", "Unknown")
        self.download_queue.remove(item)
        self.refresh_queue_ui()
        self.show_status(f"Removed from queue: {title}", self.colors["text_secondary"], 2500)
    def _queue_stats(self):
        stats = {"total": len(self.download_queue), "waiting": 0, "active": 0, "done": 0, "error": 0}
        for item in self.download_queue:
            status = item.get("status")
            if status == "Waiting":
                stats["waiting"] += 1
            elif status in ("Downloading", "Processing..."):
                stats["active"] += 1
            elif status == "Finished":
                stats["done"] += 1
            elif status == "Error":
                stats["error"] += 1
        return stats

    def refresh_queue_header(self):
        stats = self._queue_stats()
        if hasattr(self, "queue_title_label") and self.queue_title_label.winfo_exists():
            self.queue_title_label.configure(text=f"Queue ({stats['total']})")
        if hasattr(self, "queue_summary_label") and self.queue_summary_label.winfo_exists():
            if stats["total"] == 0:
                summary_text = "Queue is empty | Paste a URL to get started"
            else:
                summary_text = (
                    f"Waiting {stats['waiting']} | Active {stats['active']} | "
                    f"Done {stats['done']} | Error {stats['error']}"
                )
            self.queue_summary_label.configure(text=summary_text)
        if hasattr(self, "retry_errors_btn") and self.retry_errors_btn.winfo_exists():
            self.retry_errors_btn.configure(state="normal" if stats["error"] > 0 else "disabled")
        if hasattr(self, "clear_finished_btn") and self.clear_finished_btn.winfo_exists():
            self.clear_finished_btn.configure(state="normal" if stats["done"] > 0 else "disabled")


    def retry_error_items(self):
        retried = 0
        for item in self.download_queue:
            if item.get("status") == "Error":
                item["status"] = "Waiting"
                item["progress"] = 0.0
                item["speed"] = ""
                item["eta"] = ""
                retried += 1
        if retried:
            self.show_status(f"Retrying {retried} failed item(s).", self.colors["accent"], 4000)
            self.refresh_queue_ui()
            self._process_queue()

    def clear_finished_items(self):
        before = len(self.download_queue)
        self.download_queue = [item for item in self.download_queue if item.get("status") != "Finished"]
        removed = before - len(self.download_queue)
        if removed:
            self.show_status(f"Cleared {removed} finished item(s).", self.colors["text_secondary"], 3500)
            self.refresh_queue_ui()

    def load_queue_thumbnail(self, url, item):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as u:
                raw_data = u.read()
            image = self._prepare_thumbnail_image(Image.open(io.BytesIO(raw_data)), (96, 54))
            photo = ctk.CTkImage(light_image=image, dark_image=image, size=(96, 54))

            def apply_thumb():
                item["thumbnail_loading"] = False
                item["thumbnail_image"] = photo
                label = item.get("thumbnail_label")
                if label and label.winfo_exists():
                    label.configure(image=photo, text="")
                    label.image = photo

            self._dispatch_to_ui(apply_thumb)
        except Exception:
            def apply_error():
                item["thumbnail_loading"] = False
                label = item.get("thumbnail_label")
                if label and label.winfo_exists() and not item.get("thumbnail_image"):
                    self._set_thumbnail_placeholder(label, "No Preview")

            self._dispatch_to_ui(apply_error)

    def _process_queue(self):
        if getattr(self, 'is_downloading', False):
            return

        duplicate_policy = self._overwrite_policy_value(self.overwrite_policy_var.get()) if hasattr(self, "overwrite_policy_var") else self.settings.get("overwrite_policy", "ask")

        for item in self.download_queue:
            if item['status'] != 'Waiting':
                continue

            if duplicate_policy != "rename":
                item["filename_suffix"] = ""

            if not item.get("overwrite", False):
                existing_files = self._collect_existing_files(item.get("dir", ""), item.get("info"), item.get("url", ""))
                if existing_files:
                    if duplicate_policy == "overwrite":
                        item["overwrite"] = True
                    elif duplicate_policy == "rename":
                        suffix = self._next_duplicate_filename_suffix(existing_files)
                        item["overwrite"] = False
                        item["filename_suffix"] = suffix
                        self.show_status(f"중복 파일이 있어 새 이름으로 저장합니다: {suffix}", self.colors["text_secondary"], 4000)
                    elif duplicate_policy == "skip":
                        existing_path = max(existing_files, key=lambda p: os.path.getmtime(p))
                        item["status"] = "Finished"
                        item["progress"] = 100.0
                        item["path"] = existing_path
                        self.update_queue_item_ui(item)
                        self.refresh_queue_header()
                        self.show_status("중복 파일이 있어 기존 파일을 유지하고 항목을 건너뛰었습니다.", self.colors["warning"], 5000)
                        continue
                    else:
                        should_overwrite = self._prompt_overwrite_for_existing(existing_files)
                        if should_overwrite:
                            item["overwrite"] = True
                        else:
                            existing_path = max(existing_files, key=lambda p: os.path.getmtime(p))
                            item["status"] = "Finished"
                            item["progress"] = 100.0
                            item["path"] = existing_path
                            self.update_queue_item_ui(item)
                            self.refresh_queue_header()
                            self.show_status("중복 파일을 유지하고 항목을 건너뛰었습니다.", self.colors["warning"], 5000)
                            continue

            self.is_downloading = True
            self.current_download_item = item
            self.last_downloaded_file = ""
            self.active_download_callback_pending = False
            self.active_download_started_at = time.monotonic()
            self._mark_download_activity()
            self._last_progress_dispatch_at = 0.0
            self._last_progress_value = -1.0
            item['status'] = 'Downloading'
            self.show_status(f"Downloading: {item['title']}", self.colors["accent"])
            self.update_queue_item_ui(item)
            self.refresh_queue_ui()
            self._refresh_live_download_card(item)

            self.downloader.download_dir = item['dir']
            self.active_download_thread = self.downloader.start_download(
                item['url'],
                item['type'],
                item['res'],
                item['subs'],
                self.progress_hook,
                self.on_download_finished,
                self.on_download_error,
                item.get("overwrite", False),
                item.get("filename_suffix", "")
            )
            return

    def setup_history_tab(self):
        tab = self.tabview.tab("History")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        self.history_header_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.history_header_frame.grid(row=0, column=0, padx=18, pady=(12, 8), sticky="ew")
        self.history_header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.history_header_frame,
            text="Download History",
            font=self.font_h2,
            text_color=self.colors["text_primary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self.history_summary_label = ctk.CTkLabel(
            self.history_header_frame,
            text="0 items",
            font=self.font_small,
            text_color=self.colors["text_secondary"],
            anchor="w",
        )
        self.history_summary_label.grid(row=1, column=0, sticky="w")

        self.history_tools_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.history_tools_frame.grid(row=1, column=0, padx=18, pady=(0, 10), sticky="ew")
        self.history_tools_frame.grid_columnconfigure(0, weight=1)

        self.history_search_entry = ctk.CTkEntry(
            self.history_tools_frame,
            textvariable=self.history_query_var,
            placeholder_text="Search title or URL",
            height=36,
            corner_radius=10,
            fg_color=self.colors["surface"],
            border_width=1,
            border_color=self.colors["border"],
            text_color=self.colors["text_primary"],
            font=self.font_body,
        )
        self.history_search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.clear_history_btn = ctk.CTkButton(
            self.history_tools_frame,
            text="Clear",
            width=86,
            height=36,
            corner_radius=10,
            font=self.font_body,
            command=self.clear_history,
            fg_color=self.colors["surface_2"],
            hover_color=self.colors["surface_3"],
            text_color=self.colors["text_primary"],
        )
        self.clear_history_btn.grid(row=0, column=1)

        self.history_scroll = ctk.CTkScrollableFrame(
            tab,
            corner_radius=14,
            fg_color=self.colors["panel"],
            border_width=1,
            border_color=self.colors["border"],
        )
        self.history_scroll.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 16))
        self.history_scroll.grid_columnconfigure(0, weight=1)

        if not hasattr(self, "_history_query_trace"):
            self._history_query_trace = self.history_query_var.trace_add("write", lambda *_: self.refresh_history_ui())

        self.refresh_history_ui()

    def refresh_history_ui(self):
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        query = self.history_query_var.get().strip().lower() if hasattr(self, "history_query_var") else ""
        records = list(reversed(self.history))
        if query:
            records = [
                record
                for record in records
                if query in record.get("title", "").lower() or query in record.get("url", "").lower()
            ]

        total_count = len(self.history)
        shown_count = len(records)
        if hasattr(self, "history_summary_label") and self.history_summary_label.winfo_exists():
            if query:
                self.history_summary_label.configure(text=f"{shown_count} / {total_count} items")
            else:
                self.history_summary_label.configure(text=f"{total_count} items")

        if not records:
            empty_text = "No matching history." if query else "No download history yet."
            ctk.CTkLabel(
                self.history_scroll,
                text=empty_text,
                text_color=self.colors["text_secondary"],
                font=self.font_body,
            ).grid(row=0, column=0, pady=22)
    
            return

        for idx, record in enumerate(records):
            frame = ctk.CTkFrame(
                self.history_scroll,
                fg_color=self.colors["surface"],
                corner_radius=12,
                border_width=1,
                border_color=self.colors["border"],
            )
            frame.grid(row=idx, column=0, sticky="ew", pady=6, padx=6)
            frame.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                frame,
                text=record.get("title", "Unknown"),
                font=self.font_item_title,
                text_color=self.colors["text_primary"],
                anchor="w",
                justify="left",
                wraplength=310,
            ).grid(row=0, column=0, sticky="w", padx=(12, 8), pady=(9, 2))

            info_text = f"{record.get('type', 'Unknown')} | {record.get('resolution', 'Unknown')} | {record.get('date', '')}"
            ctk.CTkLabel(
                frame,
                text=info_text,
                text_color=self.colors["text_secondary"],
                font=self.font_small,
                anchor="w",
            ).grid(row=1, column=0, sticky="w", padx=(12, 8), pady=(0, 2))

            url = record.get("url", "")
            if url:
                url_display = url if len(url) <= 70 else f"{url[:67]}..."
                url_lbl = ctk.CTkLabel(
                    frame,
                    text=url_display,
                    text_color="#8BBEFA",
                    font=self.font_link,
                    anchor="w",
                    cursor="hand2",
                )
                url_lbl.grid(row=2, column=0, sticky="w", padx=(12, 8), pady=(0, 3))
                url_lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))

            path_btn = ctk.CTkButton(
                frame,
                text="Open Folder",
                width=100,
                height=28,
                corner_radius=8,
                font=self.font_small,
                fg_color=self.colors["surface_2"],
                hover_color=self.colors["surface_3"],
                text_color=self.colors["text_primary"],
                command=lambda p=record.get("path", ""): self.open_file_location(p),
            )
            path_btn.grid(row=3, column=0, sticky="w", padx=(12, 8), pady=(0, 10))

            thumb_lbl = ctk.CTkLabel(
                frame,
                text="No Preview",
                width=80,
                height=60,
                corner_radius=10,
                fg_color=self.colors["surface_2"],
                text_color=self.colors["text_secondary"],
                font=self.font_small,
            )
            thumb_lbl.grid(row=0, column=1, rowspan=4, padx=(8, 12), pady=10, sticky="e")

            thumb_url = record.get("thumbnail")
            if thumb_url:
                self._set_thumbnail_placeholder(thumb_lbl, "Loading...")
                threading.Thread(target=self.load_history_thumbnail, args=(thumb_url, thumb_lbl), daemon=True).start()
            else:
                self._set_thumbnail_placeholder(thumb_lbl, "No Preview")


    def load_history_thumbnail(self, url, label):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as u:
                raw_data = u.read()
            image = self._prepare_thumbnail_image(Image.open(io.BytesIO(raw_data)), (80, 60))
            photo = ctk.CTkImage(light_image=image, dark_image=image, size=(80, 60))

            def apply_thumb():
                if label.winfo_exists():
                    label.configure(image=photo, text="")
                    label.image = photo

            self._dispatch_to_ui(apply_thumb)
        except Exception:
            self._dispatch_to_ui(self._set_thumbnail_placeholder, label, "No Preview")

    def open_file_location(self, path):
        if not path:
            return

        target_dir = path if os.path.isdir(path) else os.path.dirname(path)
        if target_dir and os.path.exists(target_dir):
            os.startfile(target_dir)

    def clear_history(self):
        self.history = []
        self.save_history()
        self.refresh_history_ui()

    def open_download_folder(self):
        folder = self.path_var.get()
        if os.path.exists(folder):
            os.startfile(folder)
        else:
            try:
                os.makedirs(folder, exist_ok=True)
                os.startfile(folder)
            except Exception as e:
                print(f"Could not open/create folder: {e}")

    def save_options(self):
        self.settings["auto_download"] = self.auto_dl_var.get()
        self.settings["subtitles"] = self.subtitles_var.get()
        if hasattr(self, "overwrite_policy_var"):
            self.settings["overwrite_policy"] = self._overwrite_policy_value(self.overwrite_policy_var.get())
        self.save_settings()

    def on_type_change(self, choice):
        if choice == "Audio":
            self.res_menu.configure(state="disabled")
            self.subtitles_checkbox.configure(state="disabled")
        else:
            self.res_menu.configure(state="normal")
            self.subtitles_checkbox.configure(state="normal")

    def browse_path(self):
        folder = filedialog.askdirectory(initialdir=self.path_var.get())
        if folder:
            try:
                os.makedirs(folder, exist_ok=True)
                self.path_var.set(folder)
                self.downloader.download_dir = folder
                self.settings["download_path"] = folder
                self.save_settings()
                self.show_status(f"Save folder: {folder}", self.colors["success"], 2500)
            except Exception as e:
                self.show_status(f"Cannot use folder: {e}", self.colors["danger"], 5000)

    def auto_start_download_from_url(self, url):
        self.url_var.set(url)
        # Fetch info will be triggered by on_url_change
        # We need to set a flag to auto-start when info is fetched
        self._waiting_to_auto_start = True
    def on_url_change(self, *args):
        url = self.url_var.get().strip()
        if url.startswith("http"):
            self.info_request_token += 1
            request_token = self.info_request_token
            self.current_thumbnail_token += 1
            if hasattr(self, "thumbnail_label") and self.thumbnail_label.winfo_exists():
                self._set_thumbnail_placeholder(self.thumbnail_label, "Loading...")
            self.download_btn.configure(
                state="disabled",
                text="Loading Info...",
                fg_color=self.colors["surface_2"],
                hover_color=self.colors["surface_3"],
            )
            self.current_info = None
            self.show_status("Fetching video info...", self.colors["text_secondary"], 2000)

            if not getattr(self, '_waiting_to_auto_start', False) and self.auto_dl_var.get():
                self._waiting_to_auto_start = True

            self.downloader.fetch_info(
                url,
                lambda info, token=request_token, requested_url=url: self.on_info_fetched(info, token, requested_url),
                lambda err, token=request_token, requested_url=url: self.on_info_error(err, token, requested_url),
            )
        else:
            self.info_request_token += 1
            self.current_thumbnail_token += 1
            self.current_info = None
            if hasattr(self, "info_frame") and self.info_frame.winfo_ismapped():
                self.info_frame.grid_forget()
            if hasattr(self, "thumbnail_label") and self.thumbnail_label.winfo_exists():
                self._set_thumbnail_placeholder(self.thumbnail_label, "No Preview")
            self.download_btn.configure(
                state="disabled",
                text="Download",
                fg_color=self.colors["accent"],
                hover_color=self.colors["accent_hover"],
                text_color_disabled="#EBEBF5",
            )

    def format_duration(self, seconds):
        if seconds is None or seconds == "":
            return "Unknown"
        try:
            total_seconds = max(0, int(float(seconds)))
        except (TypeError, ValueError):
            return "Unknown"
        m, s = divmod(total_seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def on_info_fetched(self, info, request_token=None, requested_url=None):
        self._dispatch_to_ui(self._handle_info_fetched_ui, info, request_token, requested_url)

    def _handle_info_fetched_ui(self, info, request_token=None, requested_url=None):
        current_url = self.url_var.get().strip() if hasattr(self, "url_var") else ""
        if request_token is not None and request_token != self.info_request_token:
            return
        if requested_url and requested_url != current_url:
            return

        self.current_info = info
        self.update_ui_with_info(info, request_token, requested_url)

    def update_ui_with_info(self, info, request_token=None, requested_url=None):
        current_url = self.url_var.get().strip() if hasattr(self, "url_var") else ""
        if request_token is not None and request_token != self.info_request_token:
            return
        if requested_url and requested_url != current_url:
            return

        self.video_title.configure(text=info.get('title', 'Unknown Title'))
        self.video_duration.configure(text=self.format_duration(info.get('duration')))

        # Handle thumbnail async
        thumb_url = info.get('thumbnail')
        self.current_thumbnail_token += 1
        thumbnail_token = self.current_thumbnail_token
        if thumb_url:
            self._set_thumbnail_placeholder(self.thumbnail_label, "Loading...")
            threading.Thread(target=self.load_thumbnail, args=(thumb_url, thumbnail_token), daemon=True).start()
        else:
            self._set_thumbnail_placeholder(self.thumbnail_label, "No Preview")

        self.info_frame.grid(row=1, column=0, pady=(0, 15), sticky="ew")
        self.download_btn.configure(state="normal", text="Download", fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"])

        # Update available resolutions if video
        if not info.get('is_playlist'):
            formats = info.get('formats', [])
            resolutions = set()
            for f in formats:
                if f.get('vcodec') != 'none' and f.get('height'):
                    resolutions.add(f['height'])
            
            if resolutions:
                sorted_res = sorted(list(resolutions), reverse=True)
                res_values = ["Best"] + [f"{r}p" for r in sorted_res]
                self.res_menu.configure(values=res_values)
                self.res_var.set("Best")

        # Auto start download if flag is set
        if getattr(self, '_waiting_to_auto_start', False):
            self._waiting_to_auto_start = False
            self.start_download()

    def load_thumbnail(self, url, token):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as u:
                raw_data = u.read()
            image = self._prepare_thumbnail_image(Image.open(io.BytesIO(raw_data)), (120, 90))
            photo = ctk.CTkImage(light_image=image, dark_image=image, size=(120, 90))

            def apply_thumb():
                if token != self.current_thumbnail_token:
                    return
                self.thumbnail_label.configure(image=photo, text="")
                self.thumbnail_label.image = photo

            self._dispatch_to_ui(apply_thumb)
        except Exception as e:
            def apply_error():
                if token != self.current_thumbnail_token:
                    return
                self._set_thumbnail_placeholder(self.thumbnail_label, "No Preview")

            self._dispatch_to_ui(apply_error)
            print(f"Thumbnail error: {e}")

    def on_info_error(self, err, request_token=None, requested_url=None):
        self._dispatch_to_ui(self._handle_info_error_ui, err, request_token, requested_url)

    def _handle_info_error_ui(self, err, request_token=None, requested_url=None):
        current_url = self.url_var.get().strip() if hasattr(self, "url_var") else ""
        if request_token is not None and request_token != self.info_request_token:
            return
        if requested_url and requested_url != current_url:
            return

        self._waiting_to_auto_start = False
        self.current_thumbnail_token += 1
        self.current_info = None
        short_err = str(err).splitlines()[0][:120] if err else "Invalid URL"
        self.show_status(f"Info error: {short_err}", self.colors["danger"], 8000)

        if hasattr(self, "info_frame") and self.info_frame.winfo_ismapped():
            self.info_frame.grid_forget()
        if hasattr(self, "thumbnail_label") and self.thumbnail_label.winfo_exists():
            self._set_thumbnail_placeholder(self.thumbnail_label, "No Preview")

        self.after(
            0,
            lambda: self.download_btn.configure(
                state="disabled",
                text="Invalid URL",
                fg_color=self.colors["danger"],
                hover_color=self.colors["danger"],
                text_color_disabled="#FFFFFF",
            ),
        )
        self.after(
            2800,
            lambda: self.download_btn.configure(
                text="Download",
                state="disabled",
                fg_color=self.colors["accent"],
                hover_color=self.colors["accent_hover"],
                text_color_disabled="#EBEBF5",
            ),
        )

    def start_download(self):
        url = self.url_var.get().strip()
        if not url or not self.current_info:
            return

        download_dir = self.path_var.get().strip()
        if not download_dir:
            self.show_status("Please choose a save folder first.", self.colors["danger"], 6000)
            return

        try:
            os.makedirs(download_dir, exist_ok=True)
        except Exception as e:
            self.show_status(f"Cannot create folder: {e}", self.colors["danger"], 8000)
            return

        self.settings["download_path"] = download_dir
        self.save_settings()

        for queued_item in self.download_queue:
            if (
                queued_item.get("url") == url
                and queued_item.get("type") == self.type_var.get()
                and queued_item.get("res") == self.res_var.get()
                and queued_item.get("status") in ("Waiting", "Downloading", "Processing...")
            ):
                self.show_status("이미 같은 항목이 대기열에 있습니다.", self.colors["warning"], 4000)
                return

        overwrite = False
        filename_suffix = ""
        existing_files = self._collect_existing_files(download_dir, self.current_info, url)
        duplicate_policy = self._overwrite_policy_value(self.overwrite_policy_var.get()) if hasattr(self, "overwrite_policy_var") else self.settings.get("overwrite_policy", "ask")

        if existing_files:
            if duplicate_policy == "skip":
                self.show_status("중복 파일이 있어 다운로드를 건너뛰었습니다.", self.colors["warning"], 5000)
                return
            if duplicate_policy == "overwrite":
                overwrite = True
            elif duplicate_policy == "rename":
                filename_suffix = self._next_duplicate_filename_suffix(existing_files)
                self.show_status(f"중복 파일이 있어 새 이름으로 저장합니다: {filename_suffix}", self.colors["text_secondary"], 4000)
            else:
                preview = "\n".join(f"- {os.path.basename(p)}" for p in existing_files[:5])
                more = f"\n... 외 {len(existing_files) - 5}개" if len(existing_files) > 5 else ""
                should_overwrite = messagebox.askyesno(
                    "파일 덮어쓰기 확인",
                    (
                        "같은 제목의 파일이 이미 있습니다.\n\n"
                        f"{preview}{more}\n\n"
                        "기존 파일을 덮어쓸까요?"
                    ),
                )
                if not should_overwrite:
                    self.show_status("다운로드 취소: 기존 파일을 유지했습니다.", self.colors["warning"], 5000)
                    return
                overwrite = True

        self.download_btn.configure(state="disabled", text="Added to Queue!")
        self.after(2000, lambda: self.download_btn.configure(state="normal", text="Download", fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"]))

        format_type = self.type_var.get()
        resolution = self.res_var.get()
        download_subs = self.subtitles_var.get() and format_type == "Video"

        queue_item = {
            "title": self.current_info.get('title', 'Unknown Title') if self.current_info else 'Unknown',
            "url": url,
            "type": format_type,
            "res": resolution,
            "subs": download_subs,
            "overwrite": overwrite,
            "filename_suffix": filename_suffix,
            "thumbnail": self.current_info.get("thumbnail") if self.current_info else None,
            "thumbnail_image": None,
            "thumbnail_label": None,
            "thumbnail_loading": False,
            "dir": download_dir,
            "status": "Waiting",
            "progress": 0.0,
            "speed": "",
            "eta": "",
            "info": self.current_info,
            "queued_at": datetime.now().strftime("%H:%M:%S")
        }

        self.download_queue.append(queue_item)
        self.refresh_queue_ui()
        self.show_status(f"Queued: {queue_item['title']}", self.colors["text_secondary"], 2500)
        self._process_queue()

    def progress_hook(self, d):
        self._mark_download_activity()
        if d['status'] == 'downloading':
            try:
                if 'playlist_index' in d:
                    idx = d.get('playlist_index')
                    total = d.get('playlist_count', '?')
                    playlist_info = f"[{idx}/{total}] "
                else:
                    playlist_info = ""

                percent_str = d.get('_percent_str', '0.0%').strip()
                import re
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                percent_str = ansi_escape.sub('', percent_str)
                pct = float(percent_str.replace('%', ''))
                
                speed = d.get('_speed_str', 'N/A')
                eta = d.get('_eta_str', 'N/A')

                self._dispatch_progress_update(pct, speed, eta, playlist_info)
            except Exception as e:
                pass
        elif d['status'] == 'finished':
            self.last_downloaded_file = d.get('filename') or d.get('info_dict', {}).get('_filename', 'Unknown')
            if hasattr(self, 'current_download_item'):
                item = self.current_download_item
                item['status'] = 'Processing...'
                self._dispatch_to_ui(self.update_queue_item_ui, item)
                self._dispatch_to_ui(self._refresh_live_download_card, item)

    def update_progress(self, pct, speed, eta, playlist_info=""):
        self._mark_download_activity()
        if hasattr(self, 'current_download_item'):
            item = self.current_download_item
            item['progress'] = pct
            item['speed'] = speed
            item['eta'] = eta
            item['playlist_info'] = playlist_info
            if pct == 100:
                item['status'] = 'Processing...'
            self.update_queue_item_ui(item)
            self._refresh_live_download_card(item)

    def on_download_finished(self):
        self.active_download_callback_pending = True
        self._mark_download_activity()
        self._dispatch_to_ui(self._finish_ui)

    def _finish_ui(self):
        path = getattr(self, 'last_downloaded_file', '')
        item = getattr(self, 'current_download_item', None)
        self.active_download_callback_pending = False

        try:
            if not item:
                return

            if not path or not os.path.exists(path):
                path = self._resolve_queue_item_path(item)
            if not path:
                path = item.get("dir", "") or "Unknown"

            item['status'] = 'Finished'
            item['progress'] = 100
            item["path"] = path
            self.update_queue_item_ui(item)
            self.refresh_queue_header()

            record = {
                "title": item["title"],
                "url": item["url"],
                "type": item["type"],
                "resolution": item["res"],
                "path": path,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "thumbnail": item["info"].get('thumbnail') if item["info"] else None
            }
            self.history.append(record)
            self.save_history()
            self.refresh_history_ui()
            self.show_status(f"Finished: {item['title']}", self.colors["success"], 5000)
        except Exception as e:
            print(f"Finish UI error: {e}")
            self.show_status(f"Finished, but cleanup failed: {e}", self.colors["warning"], 6000)
        finally:
            self.is_downloading = False
            self.current_download_item = None
            self._reset_active_download()
            self.after(500, self._process_queue)

    def on_download_error(self, err):
        self.active_download_callback_pending = True
        self._mark_download_activity()
        self._dispatch_to_ui(self._handle_download_error_ui, str(err) if err else "Unknown error")

    def _handle_download_error_ui(self, full_err):
        self.active_download_callback_pending = False
        print(full_err)
        short_err = full_err.splitlines()[0][:150]
        item = getattr(self, 'current_download_item', None)
        if item:
            item['status'] = 'Error'
            self.update_queue_item_ui(item)
            self.refresh_queue_header()
            self._refresh_live_download_card(item)
        self.show_status(f"Download failed: {short_err}", self.colors["danger"], 10000)
        try:
            messagebox.showerror("?ㅼ슫濡쒕뱶 ?ㅽ뙣", full_err)
        except Exception:
            pass

        item = getattr(self, 'current_download_item', None)
        if item:
            item['status'] = 'Error'
            self.update_queue_item_ui(item)
            self.refresh_queue_header()

        self.is_downloading = False
        self.current_download_item = None
        self._reset_active_download()
        self.after(500, self._process_queue)

if __name__ == "__main__":
    app = App()
    app.mainloop()


























































