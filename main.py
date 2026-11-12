# -*- coding: utf-8 -*-
# ================= 一机一码授权验证 =================
import uuid
import hashlib
import tkinter as tk
from tkinter import simpledialog, messagebox
import os
import sys

# 你的专属密钥，千万别忘了，也别发给别人！
SECRET_KEY = "ZXS_Master_Key_2024"

def check_license():
    auth_file = os.path.join(os.environ.get("APPDATA", ""), "zxs_auth.dat")
    if os.path.exists(auth_file):
        return True
        
    mac = uuid.getnode()
    machine_code = hashlib.md5(str(mac).encode()).hexdigest()[:8].upper()
    
    # 隐藏主窗口，仅弹窗
    root = tk.Tk()
    root.withdraw()
    
    msg = f"软件未授权！\n\n本机机器码：{machine_code}\n\n请将上方机器码发给管理员获取授权码："
    user_key = simpledialog.askstring("软件激活", msg)
    
    if not user_key:
        messagebox.showwarning("提示", "未输入授权码，软件将退出。")
        sys.exit()
        
    expected_key = hashlib.md5((machine_code + SECRET_KEY).encode()).hexdigest()[:12].upper()
    
    if user_key.strip().upper() == expected_key:
        with open(auth_file, "w") as f:
            f.write("Authorized")
        messagebox.showinfo("成功", "授权成功！欢迎使用珠心算训练器。")
        root.destroy()
        return True
    else:
        messagebox.showerror("错误", "授权码不正确！")
        sys.exit()

# 在启动 App 之前强制检查授权
if not check_license():
    sys.exit()
# ====================================================

# 下面保留你原来所有的代码，比如：
# import sqlite3
# import random
# ...
"""
珠心算训练器 v8.0 (纯净终极版)
混合位数 | 竖式对齐 | 语音防卡死 | 今日成绩展示 | 免密登录 | 随时退出
"""
import os
import sqlite3
import random
import datetime
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# ---------------- 语音模块 (独立线程，绝对防卡死) ----------------
_D = "零一二三四五六七八九"

def _sec4(n):
    s = str(n).zfill(4)
    units = ["千", "百", "十", ""]
    out = ""
    zero = False
    for i, ch in enumerate(s):
        d = int(ch)
        if d == 0:
            if out: zero = True
            continue
        if zero:
            out += "零"
            zero = False
        out += _D[d] + units[i]
    return out

def num_to_cn(n):
    if isinstance(n, float):
        integer_part = int(n)
        res = num_to_cn(integer_part)
        dec = round(n - integer_part, 3)
        if dec > 0:
            res += "点"
            for _ in range(3):
                dec *= 10
                digit = int(dec)
                res += _D[digit]
                dec -= digit
        return res
    n = int(n)
    if n == 0: return "零"
    if n < 10000:
        s = _sec4(n)
        if s.startswith("一十"): s = s[1:]
        return s
    hi, lo = divmod(n, 10000)
    s = num_to_cn(hi) + "万"
    if lo:
        if lo < 1000: s += "零"
        s += num_to_cn(lo)
    return s

class TTS:
    def __init__(self, root):
        self.root = root
        self.ok = False
        self.err_msg = ""
        try:
            import pyttsx3
            test = pyttsx3.init()
            test.stop()
            self.ok = True
        except Exception as e:
            self.err_msg = f"语音引擎不可用，请检查是否被拦截。\n({e})"
            self.ok = False

    def speak(self, text, rate=160, callback=None):
        if not self.ok:
            if callback: self.root.after(0, callback)
            return

        def _run():
            try:
                import pythoncom
                pythoncom.CoInitialize()
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty("rate", rate) 
                for v in engine.getProperty("voices"):
                    name = (getattr(v, "name", "") or "").lower()
                    vid = (getattr(v, "id", "") or "").lower()
                    if "chinese" in name or "huihui" in name or "zh" in vid:
                        engine.setProperty("voice", v.id)
                        break
                engine.say(text)
                engine.runAndWait()
                engine.stop()
                pythoncom.CoUninitialize()
            except Exception:
                pass
            finally:
                if callback:
                    try: self.root.after(0, callback)
                    except: pass

        threading.Thread(target=_run, daemon=True).start()

# ---------------- 数据库模块 ----------------
app_data_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ZhuXinSuanV8")
os.makedirs(app_data_dir, exist_ok=True)
DB_FILE = os.path.join(app_data_dir, "v8.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS students
                 (id INTEGER PRIMARY KEY, grade TEXT, class_name TEXT, name TEXT, pin TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS records
                 (id INTEGER PRIMARY KEY, student_id INTEGER, date TEXT,
                  task_type TEXT, mode TEXT, total INTEGER, correct INTEGER, score_rate REAL)''')
    c.execute("SELECT COUNT(*) FROM students")
    if c.fetchone()[0] == 0:
        students = []
        grades = ["一年级", "二年级", "三年级", "四年级", "五年级", "六年级"]
        classes = ["1班", "2班", "3班", "4班", "5班", "6班"]
        for g in grades:
            for c_name in classes:
                for i in range(1, 3):
                    students.append((g, c_name, f"测试生{i}", ""))
        c.executemany("INSERT INTO students (grade, class_name, name, pin) VALUES (?,?,?,?)", students)
        conn.commit()
    conn.close()

def get_students():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, grade, class_name, name FROM students")
    res = c.fetchall()
    conn.close()
    return res

def create_student(grade, class_name, name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO students (grade, class_name, name, pin) VALUES (?,?,?,?)", (grade, class_name, name, ""))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id

def get_student_stats(student_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(DISTINCT date) FROM records WHERE student_id=?", (student_id,))
    days = c.fetchone()[0]
    c.execute("SELECT AVG(score_rate) FROM records WHERE student_id=?", (student_id,))
    avg_rate = c.fetchone()[0]
    avg_rate = f"{avg_rate:.1f}%" if avg_rate else "暂无"
    conn.close()
    return days, avg_rate

def get_today_records(student_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    today = datetime.date.today().strftime("%Y-%m-%d")
    c.execute("SELECT mode, task_type, correct, total, score_rate FROM records WHERE student_id=? AND date=? ORDER BY id DESC", 
              (student_id, today))
    res = c.fetchall()
    conn.close()
    return res

def save_record(student_id, task_type, mode, total, correct):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    today = datetime.date.today().strftime("%Y-%m-%d")
    rate = (correct / total) * 100 if total > 0 else 0
    c.execute("INSERT INTO records (student_id, date, task_type, mode, total, correct, score_rate) VALUES (?,?,?,?,?,?,?)",
              (student_id, today, task_type, mode, total, correct, rate))
    conn.commit()
    conn.close()

# ---------------- 出题与竖式 ----------------
def format_vertical(seq):
    """完美处理混合位数和小数点对齐的竖式"""
    nums = [str(n[0]) for n in seq]
    max_int_len = max(len(n.split(".")[0]) for n in nums)
    max_dec_len = max((len(n.split(".")[1]) if "." in n else 0) for n in nums)

    lines = []
    for i, (num, sign) in enumerate(seq):
        s = str(num)
        parts = s.split(".")
        int_part = parts[0]
        dec_part = parts[1] if len(parts) > 1 else ""
        dec_str = dec_part.ljust(max_dec_len, "0") if max_dec_len > 0 else ""
        int_str = int_part.rjust(max_int_len)
        full_num = f"{int_str}.{dec_str}" if max_dec_len > 0 else int_str
        
        if i == 0:
            lines.append(full_num.rjust(max_int_len + 2 + max_dec_len + (1 if max_dec_len > 0 else 0)))
        else:
            lines.append(f"{sign} {full_num}".rjust(max_int_len + 2 + max_dec_len + (1 if max_dec_len > 0 else 0)))

    total_len = max_int_len + 2 + (max_dec_len + 1 if max_dec_len > 0 else 0)
    lines.append("-" * total_len)
    return "\n".join(lines)

def get_random_num(max_int_digits, max_dec_digits):
    """生成不超过指定整数位数和小数位数的随机数字"""
    int_d = random.randint(1, max_int_digits)
    lo = 10 ** (int_d - 1) if int_d > 1 else 1
    hi = 10 ** int_d - 1
    int_part = random.randint(lo, hi)

    if max_dec_digits <= 0:
        return int_part

    dec_d = random.randint(0, max_dec_digits)
    if dec_d == 0:
        return int_part
    
    dec_part = random.randint(1, 10**dec_d - 1)
    return float(f"{int_part}.{dec_part:0{dec_d}d}")

def gen_question(task_type, digits, items, dec_places):
    if task_type == "整数满五加":
        a, b = random.choice([(1, 4), (2, 3), (3, 2), (4, 1)])
        return [(a, "+"), (b, "+")], a + b
    elif task_type == "整数破五减":
        a, b = random.choice([(5, 1), (5, 2), (5, 3), (5, 4), (6, 2), (6, 3), (6, 4), (7, 3), (7, 4), (8, 4)])
        return [(a, "-"), (b, "-")], a - b
    elif task_type == "整数进位加":
        a = random.randint(2, 9)
        b = random.randint(10 - a, 9)
        return [(a, "+"), (b, "+")], a + b
    elif task_type == "整数退位减":
        a = random.randint(11, 18)
        b = random.randint(a - 9, 9)
        return [(a, "-"), (b, "-")], a - b
    elif task_type == "整数加减混合":
        first = get_random_num(digits, 0)
        seq = [(first, "+")]
        total = first
        for _ in range(items - 1):
            v = get_random_num(digits, 0)
            if random.random() < 0.5 and total - v >= 0:
                seq.append((v, "-"))
                total -= v
            else:
                seq.append((v, "+"))
                total += v
        return seq, total
    elif task_type == "整数乘法":
        a = get_random_num(digits, 0)
        b = random.randint(2, 9)
        return [(a, "×"), (b, "×")], a * b
    elif task_type == "整数除法":
        b = random.randint(2, 9)
        ans = get_random_num(digits, 0)
        a = b * ans
        return [(a, "÷"), (b, "÷")], ans
    elif task_type == "小数加法":
        a = get_random_num(digits, dec_places)
        b = get_random_num(digits, dec_places)
        return [(a, "+"), (b, "+")], round(a + b, dec_places)
    elif task_type == "小数减法":
        a = get_random_num(digits, dec_places)
        b = get_random_num(digits, dec_places)
        if a < b: a, b = b, a 
        return [(a, "-"), (b, "-")], round(a - b, dec_places)
    elif task_type == "小数加减混合":
        first = get_random_num(digits, dec_places)
        seq = [(first, "+")]
        total = first
        for _ in range(items - 1):
            v = get_random_num(digits, dec_places)
            if random.random() < 0.5 and round(total - v, dec_places) >= 0:
                seq.append((v, "-"))
                total = round(total - v, dec_places)
            else:
                seq.append((v, "+"))
                total = round(total + v, dec_places)
        return seq, total
    elif task_type == "小数乘法":
        a = get_random_num(digits, dec_places)
        b = random.randint(2, 9)
        return [(a, "×"), (b, "×")], round(a * b, dec_places)
    elif task_type == "小数除法":
        b = random.randint(2, 9)
        ans = get_random_num(digits, dec_places)
        a = round(b * ans, dec_places)
        return [(a, "÷"), (b, "÷")], ans
    return [(1, "+"), (2, "+")], 3

# ---------------- 珠像图模块 ----------------
BG = "#f7f2e7"
FONT = "Microsoft YaHei"
FRAME_COLOR = "#7a4f2a"
BEAD_INACTIVE = "#e6a8a8" 
BEAD_ACTIVE = "#800000"    

class AbacusCanvas(tk.Canvas):
    def __init__(self, master, **kw):
        super().__init__(master, bg=BG, highlightthickness=0, **kw)
        self.digits = []
        self.bind("<Configure>", lambda e: self._redraw())

    def show(self, digits):
        self.digits = list(digits)
        self._redraw()

    def _redraw(self):
        self.delete("all")
        if not self.digits: return
        W, H = self.winfo_width(), self.winfo_height()
        if W < 60 or H < 80: return
        n = len(self.digits)
        pad_x, pad_y = 24, 15
        rod_w = max(40, min(100, (W - 2 * pad_x) / n))
        total_w = rod_w * n
        x0 = (W - total_w) / 2
        top, bottom = pad_y, H - pad_y
        avail_h = bottom - top
        beam_h = 10
        up_h = (avail_h - beam_h) * 0.3
        dn_h = (avail_h - beam_h) * 0.7
        max_r_up = up_h / 3.2
        max_r_dn = dn_h / 12.8
        r = max(6.0, min(rod_w * 0.28, max_r_up, max_r_dn))
        gap = max(2.0, r * 0.15)
        beam_y = top + up_h

        self.create_rectangle(x0, top, x0 + total_w, bottom, outline=FRAME_COLOR, width=3)
        for i in range(1, n):
            x = x0 + i * rod_w
            self.create_line(x, top, x, bottom, fill="#e0d2bd", width=1)

        for i, d in enumerate(self.digits):
            cx = x0 + i * rod_w + rod_w / 2
            self._draw_rod(cx, top, bottom, beam_y, beam_h, r, gap, d)

        self.create_rectangle(x0, beam_y, x0 + total_w, beam_y + beam_h, fill=FRAME_COLOR, outline="")

    def _draw_rod(self, cx, top, bottom, beam_y, beam_h, r, gap, d):
        up_down = 1 if d >= 5 else 0
        low_up = d % 5
        step = 2 * r + gap
        if up_down: 
            self._bead(cx, beam_y - r - gap/2, r, True)
        else: 
            self._bead(cx, top + r + gap/2, r, False)
        y = bottom - r - gap/2
        for _ in range(4 - low_up):
            self._bead(cx, y, r, False)
            y -= step
        y = beam_y + beam_h + r + gap/2
        for _ in range(low_up):
            self._bead(cx, y, r, True)
            y += step

    def _bead(self, cx, cy, r, active):
        color = BEAD_ACTIVE if active else BEAD_INACTIVE
        w = r * 1.1
        h = r * 1.5
        self.create_oval(cx - w, cy - h, cx + w, cy + h, fill=color, outline=FRAME_COLOR, width=1)
        self.create_oval(cx - w * 0.4, cy - h * 0.5, cx + w * 0.2, cy - h * 0.1, fill="white", outline="")

# ---------------- 主应用 ----------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("珠心算训练器 v8.0")
        self.geometry("960x780")
        self.configure(bg=BG)
        try: self.tk.call("tk", "scaling", 1.15)
        except: pass
        self.tts = TTS(self)
        init_db()
        self.current_student = None
        self.frame = None
        self.show_login()

    def switch(self, cls, **kw):
        if self.frame is not None: 
            try: self.frame.destroy() 
            except: pass
        self.frame = cls(self, self, **kw)
        self.frame.pack(fill="both", expand=True)

    def show_login(self):
        self.current_student = None
        self.switch(LoginFrame)

    def show_dashboard(self, student_info):
        self.current_student = student_info
        self.switch(DashboardFrame)

    def show_train(self, task_type, mode, count, digits, items, dec_places, interval, speech_rate, limit_secs):
        self.switch(TrainFrame, task_type=task_type, mode=mode, count=count, digits=digits, items=items, dec_places=dec_places, interval=interval, speech_rate=speech_rate, limit_secs=limit_secs)


class LoginFrame(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self.students = get_students()

        tk.Label(self, text="珠心算训练器", font=(FONT, 32, "bold"), bg=BG, fg="#8b5a2b").pack(pady=(80, 10))
        tk.Label(self, text="专注 · 快速 · 准确", font=(FONT, 14), bg=BG, fg="#9e9e9e").pack(pady=(0, 40))

        box = tk.Frame(self, bg=BG)
        box.pack()

        tk.Label(box, text="年级：", font=(FONT, 14), bg=BG).grid(row=0, column=0, pady=10, sticky="e")
        self.grades = ["一年级", "二年级", "三年级", "四年级", "五年级", "六年级"]
        self.cb_grade = ttk.Combobox(box, values=self.grades, font=(FONT, 14), state="readonly", width=15)
        self.cb_grade.grid(row=0, column=1, pady=10)
        self.cb_grade.bind("<<ComboboxSelected>>", self.update_classes)

        tk.Label(box, text="班级：", font=(FONT, 14), bg=BG).grid(row=1, column=0, pady=10, sticky="e")
        self.classes = ["1班", "2班", "3班", "4班", "5班", "6班"]
        self.cb_class = ttk.Combobox(box, values=self.classes, font=(FONT, 14), state="readonly", width=15)
        self.cb_class.grid(row=1, column=1, pady=10)
        self.cb_class.bind("<<ComboboxSelected>>", self.update_names)

        tk.Label(box, text="姓名：", font=(FONT, 14), bg=BG).grid(row=2, column=0, pady=10, sticky="e")
        self.cb_name = ttk.Combobox(box, font=(FONT, 14), width=15)
        self.cb_name.grid(row=2, column=1, pady=10)
        tk.Label(box, text="(可直接输入新名字注册)", font=(FONT, 10), bg=BG, fg="#9e9e9e").grid(row=2, column=2, sticky="w")

        tk.Button(self, text="进入训练", font=(FONT, 16, "bold"), bg="#8b5a2b", fg="white",
                  activebackground="#6d4522", activeforeground="white", relief="flat", padx=40, pady=10, 
                  cursor="hand2", command=self.do_login).pack(pady=50)
                  
        self.cb_grade.current(0)
        self.update_classes(None)

    def update_classes(self, event):
        self.cb_class['values'] = self.classes
        if self.classes: 
            self.cb_class.current(0)
            self.update_names(None)

    def update_names(self, event):
        g, c = self.cb_grade.get(), self.cb_class.get()
        names = [s[3] for s in self.students if s[1] == g and s[2] == c]
        self.cb_name['values'] = names
        if names: 
            self.cb_name.current(0)
        else:
            self.cb_name.set('')

    def do_login(self):
        g, c = self.cb_grade.get(), self.cb_class.get()
        name = self.cb_name.get().strip() 
        if not all([g, c, name]):
            messagebox.showwarning("提示", "请选择年级、班级并填写姓名")
            return
        s_info = next((s for s in self.students if s[1]==g and s[2]==c and s[3]==name), None)
        if s_info:
            self.app.show_dashboard(s_info)
        else:
            new_id = create_student(g, c, name)
            new_info = (new_id, g, c, name)
            self.students.append(new_info)
            messagebox.showinfo("欢迎", f"已为新学员【{name}】创建账号！")
            self.app.show_dashboard(new_info)


class DashboardFrame(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        s = app.current_student
        self.sid, self.grade, self.cls, self.name = s

        top = tk.Frame(self, bg="#8b5a2b")
        top.pack(fill="x")
        tk.Label(top, text=f"{self.grade} {self.cls} {self.name} 同学", font=(FONT, 14, "bold"), bg="#8b5a2b", fg="white").pack(side="left", padx=20, pady=15)
        tk.Button(top, text="退出", font=(FONT, 12), bg="#6d4522", fg="white", relief="flat", command=app.show_login).pack(side="right", padx=20)

        data_frame = tk.Frame(self, bg=BG)
        data_frame.pack(fill="x", padx=30, pady=10)

        stats = tk.Frame(data_frame, bg="white", bd=1, relief="solid")
        stats.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        days, rate = get_student_stats(self.sid)
        tk.Label(stats, text="累计打卡", font=(FONT, 12), bg="white", fg="#616161").grid(row=0, column=0, padx=20, pady=(10,0))
        tk.Label(stats, text=f"{days} 天", font=(FONT, 20, "bold"), bg="white", fg="#2e7d32").grid(row=1, column=0, padx=20, pady=(0,10))
        tk.Label(stats, text="平均正确率", font=(FONT, 12), bg="white", fg="#616161").grid(row=0, column=1, padx=20, pady=(10,0))
        tk.Label(stats, text=f"{rate}", font=(FONT, 20, "bold"), bg="white", fg="#c62828").grid(row=1, column=1, padx=20, pady=(0,10))

        log_frame = tk.Frame(data_frame, bg="white", bd=1, relief="solid")
        log_frame.pack(side="left", fill="both", expand=True)
        
        tk.Label(log_frame, text="📅 今日答题记录", font=(FONT, 12, "bold"), bg="white", fg="#8b5a2b", anchor="w").pack(fill="x", padx=10, pady=(5,0))

        tree_frame = tk.Frame(log_frame, bg="white")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        cols = ("mode", "task", "score", "rate")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=4)
        self.tree.heading("mode", text="模式")
        self.tree.heading("task", text="题型")
        self.tree.heading("score", text="得分")
        self.tree.heading("rate", text="正确率")

        self.tree.column("mode", width=60, anchor="center")
        self.tree.column("task", width=120, anchor="center")
        self.tree.column("score", width=60, anchor="center")
        self.tree.column("rate", width=60, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.load_today_records()

        p_frame = tk.Frame(self, bg=BG)
        p_frame.pack(pady=10)
        
        row1 = tk.Frame(p_frame, bg=BG)
        row1.pack(pady=5)
        tk.Label(row1, text="题型：", font=(FONT, 12, "bold"), bg=BG).pack(side="left", padx=5)
        self.v_task = tk.StringVar(value="整数加减混合")
        tasks = ["整数满五加", "整数破五减", "整数进位加", "整数退位减", "整数加减混合", "整数乘法", "整数除法",
                 "小数加法", "小数减法", "小数加减混合", "小数乘法", "小数除法"]
        ttk.Combobox(row1, textvariable=self.v_task, values=tasks, state="readonly", width=14, font=(FONT, 12)).pack(side="left", padx=10)

        tk.Label(row1, text="模式：", font=(FONT, 12, "bold"), bg=BG).pack(side="left", padx=15)
        self.v_mode = tk.StringVar(value="看心算")
        ttk.Combobox(row1, textvariable=self.v_mode, values=["看心算", "听心算", "珠像图", "闪电算"], state="readonly", width=10, font=(FONT, 12)).pack(side="left", padx=10)

        tk.Label(row1, text="语速：", font=(FONT, 12, "bold"), bg=BG).pack(side="left", padx=15)
        self.v_speed = tk.StringVar(value="正常")
        ttk.Combobox(row1, textvariable=self.v_speed, values=["慢速", "正常", "快速"], state="readonly", width=8, font=(FONT, 12)).pack(side="left", padx=10)

        row2 = tk.Frame(p_frame, bg=BG)
        row2.pack(pady=5)
        self.v_digits = tk.IntVar(value=2)
        self.v_items = tk.IntVar(value=5)
        self.v_dec = tk.IntVar(value=2)
        self.v_count = tk.IntVar(value=10)
        self.v_interval = tk.DoubleVar(value=0.8)

        params = [
            ("最大整数位数", ttk.Spinbox(row2, from_=1, to=6, width=4, textvariable=self.v_digits, font=(FONT, 12))),
            ("笔数", ttk.Spinbox(row2, from_=2, to=15, width=4, textvariable=self.v_items, font=(FONT, 12))),
            ("最大小数位数", ttk.Spinbox(row2, from_=0, to=3, width=4, textvariable=self.v_dec, font=(FONT, 12))),
            ("题量", ttk.Spinbox(row2, from_=1, to=100, width=4, textvariable=self.v_count, font=(FONT, 12))),
            ("间隔(秒)", ttk.Spinbox(row2, from_=0.3, to=5.0, increment=0.1, width=4, textvariable=self.v_interval, font=(FONT, 12)))
        ]
        for label, widget in params:
            tk.Label(row2, text=label, font=(FONT, 12), bg=BG).pack(side="left", padx=(10, 2))
            widget.pack(side="left", padx=(0, 5))

        row3 = tk.Frame(p_frame, bg=BG)
        row3.pack(pady=5)
        tk.Label(row3, text="限时模式：", font=(FONT, 12, "bold"), bg=BG).pack(side="left", padx=5)
        self.v_limit_mode = tk.StringVar(value="不限时")
        cb_limit = ttk.Combobox(row3, textvariable=self.v_limit_mode, values=["不限时", "限时"], state="readonly", width=8, font=(FONT, 12))
        cb_limit.pack(side="left", padx=5)
        
        tk.Label(row3, text="限时(分钟)：", font=(FONT, 12), bg=BG).pack(side="left", padx=(15, 2))
        self.v_limit_mins = tk.IntVar(value=5)
        sb_limit = ttk.Spinbox(row3, from_=1, to=60, width=4, textvariable=self.v_limit_mins, font=(FONT, 12))
        sb_limit.pack(side="left", padx=5)

        def on_limit_change(event=None):
            if self.v_limit_mode.get() == "不限时":
                sb_limit.config(state="disabled")
            else:
                sb_limit.config(state="normal")
        cb_limit.bind("<<ComboboxSelected>>", on_limit_change)
        on_limit_change()

        tk.Button(self, text="开始训练", font=(FONT, 16, "bold"),
                  bg="#8b5a2b", fg="white", activebackground="#6d4522",
                  activeforeground="white", relief="flat", padx=44, pady=10,
                  cursor="hand2", command=self.start).pack(pady=20)

    def load_today_records(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        records = get_today_records(self.sid)
        if not records:
            self.tree.insert("", "end", values=("今日暂无", "答题记录", "-", "-"))
        else:
            for r in records:
                mode, task, correct, total, rate = r
                self.tree.insert("", "end", values=(mode, task, f"{correct}/{total}", f"{rate:.0f}%"))

    def start(self):
        mode = self.v_mode.get()
        task = self.v_task.get()
        if mode == "听心算" and not self.app.tts.ok:
            msg = self.app.tts.err_msg if self.app.tts.err_msg else "当前系统语音引擎不可用"
            messagebox.showwarning("听心算无法启动", f"{msg}\n\n请检查电脑音量或安装 Windows 中文语音包。")
            return
        
        speed_level = self.v_speed.get()
        speech_rate = 130 if speed_level == "慢速" else (170 if speed_level == "正常" else 220)
        
        limit_mode = self.v_limit_mode.get()
        limit_secs = self.v_limit_mins.get() * 60 if limit_mode == "限时" else 0
        
        self.app.show_train(task, mode, self.v_count.get(), self.v_digits.get(), self.v_items.get(), self.v_dec.get(), self.v_interval.get(), speech_rate, limit_secs)


class TrainFrame(tk.Frame):
    def __init__(self, master, app, task_type, mode, count, digits, items, dec_places, interval, speech_rate, limit_secs):
        super().__init__(master, bg=BG)
        self.app = app
        self.sid = app.current_student[0]
        self.task_type = task_type
        self.mode = mode
        self.total = count
        self.interval = interval
        self.speech_rate = speech_rate
        self.limit_secs = limit_secs
        self.idx = 0
        self.correct = 0
        self.job = None
        self.tick_job = None
        self.t0 = time.time()
        self.finished = False
        
        self.bind_all("<Escape>", lambda e: self.force_finish())
        
        self.questions = [gen_question(task_type, digits, items, dec_places) for _ in range(count)]

        top = tk.Frame(self, bg=BG, height=50)
        top.pack(fill="x", padx=24, pady=10)
        
        tk.Button(top, text="结束并返回 (Esc)", font=(FONT, 12, "bold"), bg="#c62828", fg="white", 
                  relief="flat", padx=10, pady=5, cursor="hand2", command=self.force_finish).pack(side="right")
        
        self.lb_time = tk.Label(top, text="00:00", font=(FONT, 12, "bold"), bg=BG, fg="#616161")
        self.lb_time.pack(side="right", padx=15)

        tk.Label(top, text=f"{mode} | {task_type}", font=(FONT, 12, "bold"), bg=BG, fg="#8b5a2b").pack(side="left")
        self.lb_prog = tk.Label(top, text="", font=(FONT, 12), bg=BG, fg="#616161")
        self.lb_prog.pack(side="left", padx=20)

        stage = tk.Frame(self, bg=BG)
        stage.pack(fill="both", expand=True, pady=(6, 0))
        
        self.lb_display = tk.Label(stage, text="准备", font=(FONT, 45, "bold"), bg=BG, fg="#2e7d32", justify="right")
        self.lb_display.pack(pady=30)

        if self.mode == "珠像图":
            self.abacus = AbacusCanvas(stage, width=720, height=320)
            self.abacus.pack(pady=4)

        self.lb_hint = tk.Label(self, text="", font=(FONT, 13), bg=BG, fg="#9e9e9e")
        self.lb_hint.pack()

        inp = tk.Frame(self, bg=BG)
        inp.pack(pady=16)
        self.ent = tk.Entry(inp, font=(FONT, 26), width=10, justify="center", relief="solid", bd=1)
        self.ent.pack(side="left", padx=10)
        self.ent.bind("<Return>", self.submit)
        tk.Button(inp, text="提交 (Enter)", font=(FONT, 13), bg="#8b5a2b", fg="white", 
                  activebackground="#6d4522", activeforeground="white", relief="flat", padx=16, pady=6,
                  cursor="hand2", command=self.submit).pack(side="left")

        self.lb_fb = tk.Label(self, text="", font=(FONT, 18, "bold"), bg=BG)
        self.lb_fb.pack(pady=10)

        self.tick()
        self.after(600, self.next_question)

    def destroy(self):
        self.unbind_all("<Escape>")
        for j in (self.job, self.tick_job):
            if j:
                try: self.after_cancel(j)
                except: pass
        self.job = None
        self.tick_job = None
        super().destroy()

    def tick(self):
        if self.finished or not self.winfo_exists(): return
        
        elapsed = time.time() - self.t0
        
        if self.limit_secs > 0:
            remain = self.limit_secs - int(elapsed)
            if remain <= 0:
                self.lb_time.config(text="00:00", fg="#c62828")
                self.finish()
                return
            color = "#c62828" if remain <= 60 else "#616161"
            self.lb_time.config(text=f"剩 {remain // 60:02d}:{remain % 60:02d}", fg=color)
        else:
            sec = int(elapsed)
            self.lb_time.config(text=f"已用 {sec // 60:02d}:{sec % 60:02d}", fg="#616161")
            
        self.tick_job = self.after(500, self.tick)

    def next_question(self):
        if self.finished: return
        if self.idx >= self.total:
            self.finish() 
            return
        
        self.ent.config(state="normal")
        self.ent.delete(0, "end")
        self.ent.focus_set()
        self.lb_prog.config(text=f"第 {self.idx + 1} / {self.total} 题    得分 {self.correct}")
        self.lb_fb.config(text="")
        self.lb_hint.config(text="")
        
        self.seq, self.answer = self.questions[self.idx]
        self.seq_pos = 0

        if self.mode in ("看心算", "闪电算"):
            self.display_static()
        elif self.mode == "听心算":
            self.lb_display.config(text="🔊", font=(FONT, 70, "bold"), fg="#1e88e5")
            self.job = self.after(500, self.play_next_audio)
        elif self.mode == "珠像图":
            self.lb_display.config(text="")
            self.job = self.after(500, self.play_next_abacus)

    def display_static(self):
        if "加" in self.task_type or "减" in self.task_type:
            text = format_vertical(self.seq)
            self.lb_display.config(text=text, font=("Consolas", 36, "bold"), justify="right", fg="#2e7d32")
        else:
            a, sign = self.seq[0]
            b, _ = self.seq[1]
            self.lb_display.config(text=f"{a} {sign} {b} = ?", font=(FONT, 45, "bold"), justify="center", fg="#2e7d32")

        if self.mode == "闪电算":
            self.job = self.after(600, self.hide_and_wait)
        else:
            self.job = None
            self.lb_hint.config(text="请输入答案后按回车")
            self.ent.focus_set()

    def hide_and_wait(self):
        if self.finished: return
        self.lb_display.config(text="❓ 请作答", font=(FONT, 45, "bold"), fg="#c62828")
        self.lb_hint.config(text="闪电算：请回忆珠像作答")
        self.ent.focus_set()
        self.job = None

    def play_next_audio(self):
        if self.finished: return
        if self.seq_pos < len(self.seq):
            v, sign = self.seq[self.seq_pos]
            first = (self.seq_pos == 0)
            voice_map = {"+": "加", "-": "减", "×": "乘以", "÷": "除以"}
            spoken = ("" if first else voice_map.get(sign, "")) + num_to_cn(v)
            
            self.seq_pos += 1
            self.app.tts.speak(spoken, rate=self.speech_rate, callback=self.audio_done)
        else:
            self.lb_display.config(text="❓", font=(FONT, 70, "bold"), fg="#c62828")
            self.lb_hint.config(text="请输入答案后按回车")
            self.ent.focus_set()
            self.job = None

    def audio_done(self):
        try:
            if self.finished or not self.winfo_exists(): return
            self.job = self.after(400, self.play_next_audio)
        except:
            pass

    def play_next_abacus(self):
        if self.finished: return
        if self.seq_pos < len(self.seq):
            v, sign = self.seq[self.seq_pos]
            first = (self.seq_pos == 0)
            sym_map = {"+": "+", "-": "-", "×": "×", "÷": "÷"}
            sym = "" if first else sym_map.get(sign, "")
            
            self.lb_display.config(text=sym, font=(FONT, 60, "bold"), fg="#c62828", justify="center")
            int_str = str(int(v))
            self.abacus.show([int(c) for c in int_str])
            
            self.seq_pos += 1
            self.job = self.after(1200, self.play_next_abacus)
        else:
            self.lb_display.config(text="")
            self.abacus.show([])
            self.lb_hint.config(text="请输入答案后按回车")
            self.ent.focus_set()
            self.job = None

    def submit(self, event=None):
        if self.finished: return
        if self.job: 
            try: self.after_cancel(self.job)
            except: pass
            self.job = None
        
        txt = self.ent.get().strip()
        if not txt: return
        try: 
            ans = float(txt) if "." in txt else int(txt)
        except ValueError: return

        self.idx += 1
        self.ent.config(state="disabled")
        self.ent.delete(0, "end")
        self.focus_set()

        if isinstance(self.answer, float):
            is_correct = abs(ans - self.answer) < 0.01
        else:
            is_correct = (ans == self.answer)

        if is_correct:
            self.correct += 1
            self.lb_fb.config(text=f"✔ 正确！ (答案: {self.answer})", fg="#2e7d32")
        else:
            self.lb_fb.config(text=f"✘ 错误，正确答案是 {self.answer}", fg="#c62828")
            
        self.lb_prog.config(text=f"第 {min(self.idx + 1, self.total)} / {self.total} 题    得分 {self.correct}")
        self.job = self.after(1500, self.next_question)

    def force_finish(self):
        if self.finished: return
        self.finished = True
        
        for j in (self.job, self.tick_job):
            if j:
                try: self.after_cancel(j)
                except: pass
        self.job = None
        self.tick_job = None
        
        if self.idx > 0:
            save_record(self.sid, self.task_type, self.mode, self.idx, self.correct)
        
        self.app.show_dashboard(self.app.current_student)

    def finish(self):
        if self.finished: return
        self.finished = True
        
        for j in (self.job, self.tick_job):
            if j:
                try: self.after_cancel(j)
                except: pass
        self.job = None
        self.tick_job = None

        if self.idx > 0:
            save_record(self.sid, self.task_type, self.mode, self.idx, self.correct)
            
        self.app.show_dashboard(self.app.current_student)

if __name__ == "__main__":
    App().mainloop()