import sys
import os
import winreg
import ctypes


def enable_windows_dpi_awareness():
    """Enable the sharpest available Windows DPI mode before tkinter starts."""
    if sys.platform != "win32":
        return "default"

    # Windows 10 Creators Update+: best behavior when crossing monitors.
    try:
        set_context = ctypes.windll.user32.SetProcessDpiAwarenessContext
        set_context.argtypes = [ctypes.c_void_p]
        set_context.restype = ctypes.c_bool
        if set_context(ctypes.c_void_p(-4)):  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
            return "per-monitor-v2"
    except Exception:
        pass

    # Windows 8.1+: per-monitor DPI awareness.
    try:
        set_awareness = ctypes.windll.shcore.SetProcessDpiAwareness
        set_awareness.argtypes = [ctypes.c_int]
        set_awareness.restype = ctypes.c_long
        result = set_awareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        if result in (0, -2147024891, 0x80070005):  # S_OK or already set
            return "per-monitor"
    except Exception:
        pass

    # Windows Vista+: system DPI awareness fallback.
    try:
        if ctypes.windll.user32.SetProcessDPIAware():
            return "system"
    except Exception:
        pass

    return "default"


def set_windows_app_user_model_id():
    """Give Windows a stable app identity for taskbar icon grouping."""
    if sys.platform != "win32":
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AIA.MediaFetchAIA")
    except Exception as exc:
        print(f"Failed to set Windows AppUserModelID: {exc}")


def get_window_dpi(window):
    """Return effective DPI for the monitor currently hosting this window."""
    if sys.platform != "win32":
        return 96

    hwnd = window.winfo_id()

    try:
        get_dpi_for_window = ctypes.windll.user32.GetDpiForWindow
        get_dpi_for_window.argtypes = [ctypes.c_void_p]
        get_dpi_for_window.restype = ctypes.c_uint
        dpi = get_dpi_for_window(ctypes.c_void_p(hwnd))
        if dpi:
            return int(dpi)
    except Exception:
        pass

    try:
        monitor = ctypes.windll.user32.MonitorFromWindow(ctypes.c_void_p(hwnd), 2)
        x_dpi = ctypes.c_uint()
        y_dpi = ctypes.c_uint()
        ctypes.windll.shcore.GetDpiForMonitor(
            ctypes.c_void_p(monitor),
            0,  # MDT_EFFECTIVE_DPI
            ctypes.byref(x_dpi),
            ctypes.byref(y_dpi),
        )
        dpi = int((x_dpi.value + y_dpi.value) / 2)
        if dpi:
            return dpi
    except Exception:
        pass

    try:
        return int(window.winfo_fpixels("1i"))
    except Exception:
        return 96


def install_tk_dpi_scaling(window):
    """Keep tkinter text scaling aligned with the window's current monitor."""
    state = {"dpi": None, "after_id": None}

    def apply_scaling():
        dpi = get_window_dpi(window)
        if dpi == state["dpi"]:
            return

        state["dpi"] = dpi
        scaling = max(0.75, min(3.0, dpi / 72.0))
        try:
            window.tk.call("tk", "scaling", scaling)
        except Exception as exc:
            print(f"Failed to apply tkinter DPI scaling: {exc}")

    def poll_scaling():
        try:
            if not window.winfo_exists():
                return
            apply_scaling()
            state["after_id"] = window.after(1200, poll_scaling)
        except Exception:
            return

    window.update_idletasks()
    apply_scaling()
    state["after_id"] = window.after(1200, poll_scaling)

def register_url_protocol(protocol_name="yg-download"):
    """
    Registers a custom URL protocol in the Windows Registry under HKEY_CURRENT_USER.
    """
    if sys.platform != "win32":
        return

    try:
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            python_exe = sys.executable
            script_path = os.path.abspath(__file__)
            exe_path = f'"{python_exe}" "{script_path}"'
        
        if getattr(sys, 'frozen', False):
            exe_path_quoted = f'"{exe_path}"'
        else:
            exe_path_quoted = exe_path

        key_path = rf"Software\Classes\{protocol_name}"
        
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, f"URL:{protocol_name} Protocol")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            
            with winreg.CreateKey(key, r"shell\open\command") as command_key:
                command_val = f'{exe_path_quoted} "%1"'
                winreg.SetValue(command_key, "", winreg.REG_SZ, command_val)
                
    except Exception as e:
        print(f"Failed to register URL protocol: {e}")

if __name__ == "__main__":
    enable_windows_dpi_awareness()
    set_windows_app_user_model_id()
    register_url_protocol()
    
    initial_url = None
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        urls = arg.split("yg-download://")
        if len(urls) > 1:
            initial_url = urls[1]
        elif arg.startswith("yg-download:"):
            initial_url = arg.replace("yg-download:", "")

    from gui import App

    app = App(initial_url=initial_url)
    install_tk_dpi_scaling(app)
    app.mainloop()
