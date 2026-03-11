import sys
import os
import winreg
from gui import App

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
    register_url_protocol()
    
    initial_url = None
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        urls = arg.split("yg-download://")
        if len(urls) > 1:
            initial_url = urls[1]
        elif arg.startswith("yg-download:"):
            initial_url = arg.replace("yg-download:", "")

    app = App(initial_url=initial_url)
    app.mainloop()
