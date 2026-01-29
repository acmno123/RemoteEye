import customtkinter as ctk
import socket, threading, mss, zlib, pyautogui, os, time, datetime
from PIL import Image, ImageTk

# ... (顏色設定維持不變) ...
COLORS = {"primary": "#6c5ce7", "secondary": "#00bcd4", "bg_dark": "#0a0a0c", "card_bg": "#1c1c1e", "success": "#32d74b", "danger": "#ff453a", "warning": "#ff9f0a"}

class RemoteEyeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.sock = None
        self.image_id = None
        self.is_connected = False
        self.start_time = time.time()
        self.remote_res = (1920, 1080)
        self.bytes_received = 0
        self.last_check_time = time.time()
        
        self.title("RemoteEye Global Ultra v1.7")
        self.geometry("1100x750")
        self.configure(fg_color=COLORS["bg_dark"])
        self.setup_sidebar()
        self.show_dashboard()
        self.update_loop()

    # --- 核心更新：修復畫面傳輸 ---
    def receive_view(self):
        self.add_log("🎬 正在啟動畫面串流...")
        while self.is_connected:
            try:
                # 1. 接收 4 字節的大小標籤
                sz_data = self.sock.recv(4)
                if not sz_data:
                    self.add_log("❗ 受控端已停止傳送資料。")
                    break
                
                sz = int.from_bytes(sz_data, 'big')
                if sz <= 0: continue
                
                self.bytes_received += sz
                
                # 2. 完整接收數據封包
                data = b""
                while len(data) < sz:
                    packet = self.sock.recv(min(sz - len(data), 65536))
                    if not packet: break
                    data += packet
                
                # 3. 解壓縮與渲染
                if len(data) == sz:
                    # 使用 zlib 解壓縮並轉換圖片
                    raw_data = zlib.decompress(data)
                    raw_img = Image.frombytes("RGB", self.remote_res, raw_data)
                    
                    # 確保 Canvas 寬度大於 0
                    cw = max(1, self.canvas.winfo_width())
                    ch = max(1, self.canvas.winfo_height())
                    
                    img = raw_img.resize((cw, ch), Image.Resampling.LANCZOS)
                    self.tk_img = ImageTk.PhotoImage(img)
                    
                    # 4. 在主執行緒更新畫布
                    self.after(0, self.draw)
                
            except Exception as e:
                self.add_log(f"❌ 畫面更新異常: {e}")
                self.is_connected = False
                break

    def draw(self):
        if hasattr(self, 'canvas') and self.canvas.winfo_exists():
            if self.image_id is None:
                # 第一次繪製
                self.image_id = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
            else:
                # 更新現有圖片內容
                self.canvas.itemconfig(self.image_id, image=self.tk_img)
            # 強制更新 Canvas 繪圖
            self.canvas.update_idletasks()

    # --- 受控端修正：畫面抓取優化 ---
    def agent_stream(self, conn):
        self.add_log("📽️ 開始抓取桌面影像...")
        with mss.mss() as sct:
            # 強制鎖定第一個螢幕 (Primary Monitor)
            monitor = sct.monitors[1]
            # 先傳送一次解析度給控制端
            res_str = f"{monitor['width']},{monitor['height']}"
            conn.sendall(len(res_str).to_bytes(4, 'big') + res_str.encode())
            
            while True:
                try:
                    # 截取螢幕
                    sct_img = sct.grab(monitor)
                    # 轉為 PIL Image (BGRX 轉 RGB)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    # 進行壓縮 (等級 3 取得速度平衡)
                    pixel_data = img.tobytes()
                    compressed_data = zlib.compress(pixel_data, 3)
                    
                    # 傳送封包大小 + 內容
                    conn.sendall(len(compressed_data).to_bytes(4, 'big') + compressed_data)
                    
                    # 控制 FPS 在 25 左右，避免頻寬爆炸
                    time.sleep(0.04)
                except (ConnectionResetError, BrokenPipeError):
                    self.add_log("❗ 控制端已中斷連線。")
                    break
                except Exception as e:
                    self.add_log(f"❌ 畫面抓取失敗: {e}")
                    break

    # --- 其餘介面與穩定度邏輯 (同 V1.6) ---
    def safe_ui_update(self, widget, func, *args, **kwargs):
        try:
            if widget and widget.winfo_exists(): func(*args, **kwargs)
        except: pass

    def update_loop(self):
        if hasattr(self, 'uptime_label') and self.uptime_label.winfo_exists():
            self.uptime_label.configure(text=self.get_uptime())
        if hasattr(self, 'traffic_label') and self.traffic_label.winfo_exists():
            now = time.time()
            diff = now - self.last_check_time
            kb_ps = (self.bytes_received / 1024) / diff if diff > 0 else 0
            self.traffic_label.configure(text=f"{kb_ps:.1f} KB/s")
            self.bytes_received = 0
            self.last_check_time = now
        if hasattr(self, 'conn_label') and self.conn_label.winfo_exists():
            status = "ACTIVE" if self.is_connected else "IDLE"
            self.conn_label.configure(text=status, text_color=COLORS["success"] if self.is_connected else COLORS["danger"])
        self.after(1000, self.update_loop)

    def get_uptime(self):
        elapsed = int(time.time() - self.start_time)
        hrs, rem = divmod(elapsed, 3600)
        mins, secs = divmod(rem, 60)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"

    def add_log(self, msg):
        if hasattr(self, 'log_box') and self.log_box.winfo_exists():
            try:
                now = datetime.datetime.now().strftime("%H:%M:%S")
                self.after(0, lambda: self._do_log(msg, now))
            except: pass

    def _do_log(self, msg, timestamp):
        if self.log_box.winfo_exists():
            self.log_box.insert("end", f"[{timestamp}] {msg}\n")
            self.log_box.see("end")

    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#0d0d0f", border_width=1, border_color="#222")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        ctk.CTkLabel(self.sidebar, text="RemoteEye", font=("Space Grotesk", 32, "bold"), text_color=COLORS["primary"]).pack(pady=40)
        btns = [("📊 儀表板", self.show_dashboard), ("🎮 控制模式", self.init_controller_ui), ("🛡️ 受控模式", self.init_agent_ui)]
        for text, cmd in btns:
            ctk.CTkButton(self.sidebar, text=text, fg_color="transparent", hover_color=COLORS["card_bg"], anchor="w", height=50, corner_radius=12, command=cmd).pack(fill="x", padx=15, pady=8)

    def clear_view(self):
        if hasattr(self, 'main_view'):
            for child in self.main_view.winfo_children(): child.destroy()
            self.main_view.destroy()
        self.main_view = ctk.CTkFrame(self, fg_color="transparent")
        self.main_view.pack(side="right", expand=True, fill="both", padx=30, pady=30)

    def show_dashboard(self):
        self.clear_view()
        ctk.CTkLabel(self.main_view, text="系統監控中心", font=("Microsoft JhengHei", 32, "bold")).pack(anchor="w", pady=(0, 25))
        stat_frame = ctk.CTkFrame(self.main_view, fg_color="transparent")
        stat_frame.pack(fill="x")
        self.uptime_label = self.create_card(stat_frame, "運行時間", "00:00:00", COLORS["secondary"], 0)
        self.conn_label = self.create_card(stat_frame, "連線狀態", "IDLE", COLORS["danger"], 1)
        self.traffic_label = self.create_card(stat_frame, "即時流量", "0.0 KB/s", COLORS["warning"], 2)
        self.log_box = ctk.CTkTextbox(self.main_view, fg_color="#141416", border_width=1, border_color="#333", font=("Consolas", 12))
        self.log_box.pack(expand=True, fill="both", pady=(20, 0))
        self.add_log("系統 Ready。")

    def create_card(self, master, title, val, color, col):
        card = ctk.CTkFrame(master, fg_color=COLORS["card_bg"], width=240, height=140, corner_radius=20, border_width=1, border_color="#333")
        card.grid(row=0, column=col, padx=10)
        card.grid_propagate(False)
        ctk.CTkLabel(card, text=title, text_color="#aaa").pack(pady=(25, 5))
        lbl = ctk.CTkLabel(card, text=val, font=("Consolas", 32, "bold"), text_color=color)
        lbl.pack(); return lbl

    def init_controller_ui(self):
        self.clear_view()
        self.image_id = None # 重置圖片 ID
        top = ctk.CTkFrame(self.main_view, fg_color=COLORS["card_bg"], height=70, corner_radius=15)
        top.pack(fill="x", pady=(0, 20))
        self.ip_entry = ctk.CTkEntry(top, placeholder_text="輸入受控端 IP", width=250, height=45)
        self.ip_entry.pack(side="left", padx=15, pady=12)
        ctk.CTkButton(top, text="建立連線", fg_color=COLORS["primary"], width=120, height=45, command=self.connect_to_agent).pack(side="left", padx=5)
        self.canvas = ctk.CTkCanvas(self.main_view, bg="#000", highlightthickness=0)
        self.canvas.pack(expand=True, fill="both")
        self.canvas.bind("<Button-1>", self.on_click)

    def connect_to_agent(self):
        ip = self.ip_entry.get().strip()
        if not ip: return
        self.add_log(f"🛰️ 嘗試連線至: {ip}...")
        threading.Thread(target=self._secure_connect_worker, args=(ip,), daemon=True).start()

    def _secure_connect_worker(self, ip):
        try:
            self.sock = socket.create_connection((ip, 65432), timeout=5)
            self.sock.settimeout(None)
            # 接收解析度
            l_data = self.sock.recv(4)
            if not l_data: raise ConnectionError("對端無回應")
            l = int.from_bytes(l_data, 'big')
            self.remote_res = tuple(map(int, self.sock.recv(l).decode().split(',')))
            self.is_connected = True
            self.add_log(f"🟢 連線成功，解析度: {self.remote_res}")
            self.receive_view()
        except Exception as e:
            self.add_log(f"❌ 連線失敗: {e}")

    def init_agent_ui(self):
        self.clear_view()
        ip = socket.gethostbyname(socket.gethostname())
        card = ctk.CTkFrame(self.main_view, fg_color=COLORS["card_bg"], corner_radius=30, border_width=1, border_color=COLORS["primary"])
        card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.7, relheight=0.5)
        ctk.CTkLabel(card, text="🛡️ 受控模式", font=("Arial", 24, "bold"), text_color=COLORS["primary"]).pack(pady=20)
        ctk.CTkLabel(card, text=ip, font=("Consolas", 48, "bold"), text_color=COLORS["secondary"]).pack(pady=10)
        self.agent_status_lbl = ctk.CTkLabel(card, text="● 等待連線...", text_color=COLORS["warning"])
        self.agent_status_lbl.pack()
        threading.Thread(target=self.run_agent_server, daemon=True).start()

    def run_agent_server(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', 65432)); s.listen(5)
            self.add_log("🛡️ 服務監聽中...")
            while True:
                conn, addr = s.accept()
                self.after(0, lambda: self.agent_status_lbl.configure(text=f"🟢 連線自: {addr[0]}", text_color=COLORS["success"]))
                self.add_log(f"接收連線: {addr[0]}")
                threading.Thread(target=self.agent_stream, args=(conn,), daemon=True).start()
                self.agent_receive(conn)
        except Exception as e: self.add_log(f"❌ 服務錯誤: {e}")

    def agent_receive(self, conn):
        while True:
            try:
                h = conn.recv(1024).decode()
                if h.startswith("click"):
                    _, x, y = h.split(","); pyautogui.click(int(x), int(y))
            except: break

    def on_click(self, e):
        if not self.is_connected or not hasattr(self, 'canvas'): return
        rx = int(e.x * (self.remote_res[0] / self.canvas.winfo_width()))
        ry = int(e.y * (self.remote_res[1] / self.canvas.winfo_height()))
        try: self.sock.sendall(f"click,{rx},{ry}".encode())
        except: pass

if __name__ == "__main__":
    RemoteEyeApp().mainloop()
