"""Pause the owned MT5 visualization through its native menu, without global keys.

Menu labels and enabled states are read at runtime; no screen coordinates or
hardcoded command IDs are used. Unknown layouts fail explicitly.
"""
import os
from pathlib import Path
import psutil


class VisualPause:
    def __init__(self, terminal_pid, terminal_path):
        self.pid = terminal_pid
        self.agent = os.path.normcase(str(Path(terminal_path).with_name('metatester64.exe')))
        self.sent = False
        self.window = None
        self.state = 'waiting_window'

    def poll(self):
        if os.name != 'nt':
            self.state = 'unsupported'
            return self.state
        import ctypes as c
        from ctypes import wintypes as w
        u = c.WinDLL('user32', use_last_error=True)
        u.GetMenu.argtypes=[w.HWND];u.GetMenu.restype=w.HMENU
        u.GetSubMenu.argtypes=[w.HMENU,c.c_int];u.GetSubMenu.restype=w.HMENU
        u.GetMenuItemCount.argtypes=[w.HMENU]
        u.GetMenuItemID.argtypes=[w.HMENU,c.c_int];u.GetMenuItemID.restype=w.UINT
        u.GetMenuStringW.argtypes=[w.HMENU,w.UINT,w.LPWSTR,c.c_int,w.UINT]
        u.GetMenuState.argtypes=[w.HMENU,w.UINT,w.UINT];u.GetMenuState.restype=w.UINT
        u.GetWindowThreadProcessId.argtypes=[w.HWND,c.POINTER(w.DWORD)]
        u.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,c.c_int]
        u.IsWindow.argtypes=[w.HWND]
        u.IsWindowVisible.argtypes=[w.HWND]
        u.ShowWindowAsync.argtypes=[w.HWND,c.c_int]
        u.SetForegroundWindow.argtypes=[w.HWND]
        u.SendMessageTimeoutW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM,w.UINT,w.UINT,c.POINTER(c.c_size_t)]
        def send(hwnd,message,wp,lp=0):
            result=c.c_size_t()
            return bool(u.SendMessageTimeoutW(hwnd,message,wp,lp,2,300,c.byref(result)))

        if self.window is None:
            try:
                children=psutil.Process(self.pid).children(recursive=True)
                pids={p.pid for p in children if os.path.normcase(p.exe()) == self.agent}
            except (psutil.Error,OSError):
                return self.state
            matches=[]
            cbtype=c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
            @cbtype
            def visit(hwnd,_):
                pid=w.DWORD();u.GetWindowThreadProcessId(hwnd,c.byref(pid))
                if pid.value in pids and u.IsWindowVisible(hwnd):
                    title=c.create_unicode_buffer(512);u.GetWindowTextW(hwnd,title,512)
                    if title.value.startswith('Strategy Tester Visualization :'):
                        matches.append(hwnd)
                return True
            u.EnumWindows.argtypes=[cbtype,w.LPARAM]
            u.EnumWindows(visit,0)
            if len(matches)!=1:return self.state
            self.window=matches[0]
        if not u.IsWindow(self.window):
            self.state='window_closed'
            return self.state
        entries={}
        def walk(menu):
            for pos in range(max(0,u.GetMenuItemCount(menu))):
                sub=u.GetSubMenu(menu,pos)
                if sub:
                    if not send(self.window,0x117,sub,pos):continue # WM_INITMENUPOPUP updates command states
                    walk(sub)
                else:
                    label=c.create_unicode_buffer(256)
                    u.GetMenuStringW(menu,pos,label,256,0x400)
                    name=label.value.replace('&','').split('\t')[0].strip().lower()
                    entries[name]=(u.GetMenuItemID(menu,pos),u.GetMenuState(menu,pos,0x400))
        menu=u.GetMenu(self.window)
        if not menu:return self.state
        walk(menu)
        pause=next((entries[n] for n in ('pausar','pause') if n in entries),None)
        start=next((entries[n] for n in ('iniciar','start') if n in entries),None)
        stop=next((entries[n] for n in ('parar','stop') if n in entries),None)
        enabled=lambda entry:entry is not None and entry[1]!=0xffffffff and not entry[1]&3
        if enabled(start) and enabled(stop):
            self.state='paused'
            u.ShowWindowAsync(self.window,5)
            u.SetForegroundWindow(self.window)
        elif enabled(pause) and not self.sent:
            # Never toggle twice: a second toggle would resume the simulation.
            self.sent=True
            self.state='pause_requested' if send(self.window,0x111,pause[0]) else 'pause_unconfirmed'
        return self.state
