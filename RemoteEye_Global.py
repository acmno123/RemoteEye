import customtkinter as ctk
import socket, threading, mss, zlib, pyautogui, os, time
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox

# --- 多國語言字典設定 (移除密碼文字) ---
LANG_MAP = {
    "zh_TW": {
        "title": "RemoteEye Global v1.0.6", "main_label": "請選擇運行模式", "btn_ctrl": "協助他人\n(控制端)",
        "btn_agent": "接受協助\n(受控端)", "ip_label": "您的本機連線資訊:", "status_wait": "狀態: 等待中...",
        "back_menu": "返回主選單", "ip_placeholder": "輸入目標 IP 地址", "connect": "立即連線",
        "send_file": "傳送檔案", "lang_select": "介面語言", "file_success": "檔案接收成功！"
    },
    "en": {
        "title": "RemoteEye Global v1.0.6", "main_label": "Select Operation Mode", "btn_ctrl": "Support Others\n(Controller)",
        "btn_agent": "Get Support\n(Agent)", "ip_label": "Local Connection Info:", "status_wait": "Status: Idle...",
        "back_menu": "Main Menu", "ip_placeholder": "Enter Target IP", "connect": "Connect Now",
        "send_file": "Send File", "lang_select": "Language", "file_success": "File Received!"
    }
}

pyautogui.FAILSAFE = False
ctk.set_appearance_mode("dark")

class RemoteEyeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.current_lang = "zh_TW"
        self.sock = None
        self.image_id = None
        self.tk_img = None
        self.remote_res = (1920, 1080)
        self.refresh_ui()

    def refresh_ui(self):
        for widget in self.winfo_children(): widget.destroy()
        L = LANG_MAP[self.current_lang]
        self.title(L["title"])
        self.geometry("600x550")
        
        # Logo 標題區
        ctk.CTkLabel(self, text="RemoteEye", font=("Arial", 40, "bold"), text_color="#3b82f6").pack(pady=(30, 5))
        ctk.CTkLabel(self, text="Global Edition v1.0.6", font=("Arial", 12), text_color="gray").pack(pady=(0, 20))
        ctk.CTkLabel(self, text=L["main_label"], font=("Arial", 16)).pack(pady=5)
        
        # 模式選擇按鈕區
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text=L["btn_ctrl"], height=140, width=240, font=("Arial", 18, "bold"), corner_radius=20, command=self.init_controller_ui).grid(row=0, column=0, padx=15)
        ctk.CTkButton(btn_frame, text=L["btn_agent"], height=140, width=240, font=("Arial", 18, "bold"), corner_radius=20, fg_color="#10b981", hover_color="#059669", command=self.init_agent_ui).grid(row=0, column=1, padx=15)

        # 底部語言切換
        lang_frame = ctk.CTkFrame(self, height=50)
        lang_frame.pack(side="bottom", fill="x", padx=50, pady=30)
        ctk.CTkLabel(lang_frame, text=L["lang_select"]).pack(side="left", padx=20)
        self.lang_menu = ctk.CTkOptionMenu(lang_frame, values=list(LANG_MAP.keys()), command=self.change_language)
        self.lang_menu.set(self.current_lang)
        self.lang_menu.pack(side="right", padx=20)

    def change_language(self, new_lang):
        self.current_lang = new_lang
        self.refresh_ui()

    # --- 受控端 (Agent) ---
    def init_agent_ui(self):
        for widget in self.winfo_children(): widget.destroy()
        L = LANG_MAP[self.current_lang]
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        
        ctk.CTkLabel(self, text=L["ip_label"], font=("Arial", 18)).pack(pady=(30,10))
        
        # IP 顯示大圖示區
        info_card = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=15)
        info_card.pack(pady=10, padx=50, fill="x")
        ctk.CTkLabel(info_card, text=f"IP: {ip}\nHOST: {hostname}", font=("Consolas", 24, "bold"), text_color="#60a5fa", pady=20).pack()
        
        self.status_label = ctk.CTkLabel(self, text=L["status_wait"], font=("Arial", 14), text_color="#94a3b8")
        self.status_label.pack(pady=20)
        
        ctk.CTkButton(self, text=L["back_menu"], fg_color="#475569", hover_color="#334155", width=200, command=self.refresh_ui).pack(pady=20)
        threading.Thread(target=self.run_agent_server, daemon=True).start()

    def run_agent_server(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('0.0.0.0', 65432))
        s.listen(1)
        while True:
            conn, addr = s.accept()
            try:
                self.after(0, lambda: self.status_label.configure(text=f"CONNECTED: {addr[0]}", text_color="#10b981"))
                with mss.mss() as sct:
                    m = sct.monitors[1]
                    res = f"{m['width']},{m['height']}".encode()
                    conn.sendall(len(res).to_bytes(4, 'big') + res)
                    threading.Thread(target=self.agent_stream, args=(conn,), daemon=True).start()
                    self.agent_receive(conn)
            except: pass

    def agent_stream(self, conn):
        with mss.mss() as sct:
            while True:
                st = time.time()
                try:
                    img = Image.frombytes("RGB", sct.monitors[1]['size'], sct.grab(sct.monitors[1]).bgra, "raw", "BGRX")
                    data = zlib.compress(img.tobytes(), 3)
                    conn.sendall(len(data).to_bytes(4, 'big') + data)
                    time.sleep(max(0, 0.04 - (time.time() - st)))
                except: break

    def agent_receive(self, conn):
        while True:
            try:
                h = conn.recv(1024).decode()
                if h.startswith("click"):
                    _, x, y = h.split(","); pyautogui.click(int(x), int(y))
                elif h.startswith("file:"):
                    _, name, size = h.split(":"); size = int(size)
                    path = os.path.join(os.path.expanduser("~"), "Desktop", name)
                    with open(path, "wb") as f:
                        r = 0
                        while r < size:
                            chunk = conn.recv(min(size-r, 4096))
                            f.write(chunk); r += len(chunk)
                    self.after(0, lambda: self.status_label.configure(text=f"✓ {name} RECEIVED"))
            except: break

    # --- 控制端 (Controller) ---
    def init_controller_ui(self):
        for widget in self.winfo_children(): widget.destroy()
        self.geometry("1100x850")
        L = LANG_MAP[self.current_lang]
        
        nav = ctk.CTkFrame(self, height=60)
        nav.pack(fill="x", padx=10, pady=10)
        
        self.ip_entry = ctk.CTkEntry(nav, placeholder_text=L["ip_placeholder"], width=250, height=35)
        self.ip_entry.pack(side="left", padx=15)
        
        ctk.CTkButton(nav, text=L["connect"], width=120, height=35, font=("Arial", 13, "bold"), command=self.connect_to_agent).pack(side="left", padx=5)
        ctk.CTkButton(nav, text=L["send_file"], width=120, height=35, fg_color="#10b981", hover_color="#059669", command=self.send_file).pack(side="left", padx=5)
        ctk.CTkButton(nav, text=L["back_menu"], width=100, height=35, fg_color="#475569", command=self.refresh_ui).pack(side="right", padx=15)
        
        self.canvas = ctk.CTkCanvas(self, bg="#0f172a", highlightthickness=0)
        self.canvas.pack(expand=True, fill="both", padx=15, pady=(0, 15))
        self.canvas.bind("<Button-1>", self.on_click)

    def connect_to_agent(self):
        ip = self.ip_entry.get().strip()
        if not ip: return
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.settimeout(5)
            self.sock.connect((ip, 65432))
            l = int.from_bytes(self.sock.recv(4), 'big')
            res = self.sock.recv(l).decode().split(',')
            self.remote_res = (int(res[0]), int(res[1]))
            threading.Thread(target=self.receive_view, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"連線失敗: {e}")

    def receive_view(self):
        self.sock.settimeout(None)
        while True:
            try:
                sz_data = self.sock.recv(4)
                if not sz_data: break
                sz = int.from_bytes(sz_data, 'big')
                data = b""
                while len(data) < sz: data += self.sock.recv(sz - len(data))
                img = Image.frombytes("RGB", self.remote_res, zlib.decompress(data)).resize(
                    (max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())), Image.Resampling.LANCZOS)
                self.tk_img = ImageTk.PhotoImage(img)
                self.after(0, self.draw)
            except: break

    def draw(self):
        if self.image_id is None: self.image_id = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        else: self.canvas.itemconfig(self.image_id, image=self.tk_img)

    def send_file(self):
        p = filedialog.askopenfilename()
        if p and self.sock:
            n, s = os.path.basename(p), os.path.getsize(p)
            self.sock.sendall(f"file:{n}:{s}".encode())
            time.sleep(0.5)
            with open(p, "rb") as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk: break
                    self.sock.sendall(chunk)

    def on_click(self, e):
        if not self.sock: return
        rx = int(e.x * (self.remote_res[0] / self.canvas.winfo_width()))
        ry = int(e.y * (self.remote_res[1] / self.canvas.winfo_height()))
        try: self.sock.sendall(f"click,{rx},{ry}".encode())
        except: pass

if __name__ == "__main__":
    RemoteEyeApp().mainloop()
