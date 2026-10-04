"""Windows용 원형 집중 타이머. 표준 라이브러리만 사용한다."""

import math
import threading
import time
import tkinter as tk
import winsound
from ctypes import windll

# 창 밖은 이 색으로 뚫어서 투명하게 만든다.
TRANS = "#010102"
FACE = "#171c19"
EDGE = "#2a3330"
CIRCUIT = "#314038"
TICK = "#FF2EF2"
TICK_CORE = "#FFD4FF"
DIGIT = "#F4FFFB"
FLASH = "#FF3AF0"
FLASH_DIGIT = "#2A001F"
MIN_MINUTES = 1
MAX_MINUTES = 60
SIZE = 340


def enable_sharp_text():
    """글자가 흐리지 않도록 Windows 배율에 맞춘다."""
    try:
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def play_chime():
    """타이머가 끝나면 짧은 소리를 낸다. 화면은 멈추지 않는다."""

    def _play():
        try:
            winsound.Beep(784, 140)
            winsound.Beep(988, 160)
            winsound.Beep(1175, 260)
        except RuntimeError:
            winsound.MessageBeep()

    threading.Thread(target=_play, daemon=True).start()


# 7세그먼트에서 켜질 획. a 위, b 오른쪽 위, c 오른쪽 아래, d 아래, e 왼쪽 아래, f 왼쪽 위, g 가운데.
SEGMENTS = {
    "0": "abcdef",
    "1": "bc",
    "2": "abdeg",
    "3": "abcdg",
    "4": "bcfg",
    "5": "acdfg",
    "6": "acdefg",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
}


class FocusTimer:
    def __init__(self, root):
        self.root = root
        self.cx = SIZE / 2
        self.cy = SIZE / 2
        self.radius = SIZE / 2 - 6
        self.minutes = 25
        self.total = self.minutes * 60
        self.remaining = float(self.total)
        self.running = False
        self.finished = False
        self.topmost = True
        self.bg_mode = "clear"
        self.after_id = None
        self.flash_after_id = None
        self.flash_on = False
        self.deadline = 0.0
        self._press = None
        self._moved = False
        self._zone = "center"
        self._build()
        self.draw()

    def _build(self):
        self.canvas = tk.Canvas(
            self.root,
            width=SIZE,
            height=SIZE,
            bg=TRANS,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.on_right_click)

        self.menu = tk.Menu(
            self.root,
            tearoff=0,
            bg="#1b211e",
            fg=DIGIT,
            activebackground="#A01878",
            activeforeground="#ffffff",
            font=("Malgun Gothic", 10),
            bd=0,
        )
        self.menu.add_command(label="항상 위", command=self.toggle_topmost)
        self.menu.add_separator()
        self.menu.add_command(label="배경 투명", command=self.toggle_clear)
        self.menu.add_command(label="배경 반투명", command=self.toggle_dim)
        self.menu.add_separator()
        self._refresh_menu()
        self.menu.add_command(label="시작 / 일시정지", command=self.toggle_run)
        self.menu.add_command(label="초기화", command=self.reset)
        self.menu.add_separator()
        self.menu.add_command(label="종료", command=self.root.destroy)

    def on_press(self, event):
        self._press = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y())
        self._moved = False
        distance = math.hypot(event.x - self.cx, event.y - self.cy)
        # 숫자 쪽은 창 이동, 그 바깥 원형 눈금은 시간 조절이다.
        self._zone = "center" if distance < self.radius * 0.46 else "dial"

    def on_drag(self, event):
        if self._press is None:
            return
        if abs(event.x_root - self._press[0]) + abs(event.y_root - self._press[1]) > 4:
            self._moved = True
        if not self._moved:
            return
        if self._zone == "dial":
            self.set_minutes(self.minutes_at(event.x, event.y))
            return
        dx = event.x_root - self._press[0]
        dy = event.y_root - self._press[1]
        self.root.geometry(f"+{self._press[2] + dx}+{self._press[3] + dy}")

    def on_release(self, event):
        if self._zone == "dial":
            self.set_minutes(self.minutes_at(event.x, event.y))
        elif not self._moved:
            self.toggle_run()
        self._press = None

    def on_right_click(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def minutes_at(self, x, y):
        """12시 방향에서 시계 방향으로 돌린 각도를 1~60분으로 바꾼다."""
        angle = math.atan2(x - self.cx, -(y - self.cy))
        if angle < 0:
            angle += 2 * math.pi
        minutes = int(round(angle / (2 * math.pi) * MAX_MINUTES))
        if minutes <= 0 or minutes > MAX_MINUTES:
            minutes = MAX_MINUTES
        return max(MIN_MINUTES, minutes)

    def set_minutes(self, minutes):
        self._cancel_flash()
        self.minutes = minutes
        self.total = minutes * 60
        self.remaining = float(self.total)
        self.finished = False
        if self.running:
            self.deadline = time.monotonic() + self.remaining
        self.draw()

    def _mark(self, name, on):
        return f"✓  {name}" if on else f"    {name}"

    def _refresh_menu(self):
        """체크 글자를 라벨에 넣어서, 마우스를 올리지 않아도 선택된 항목이 보이게 한다."""
        self.menu.entryconfigure(0, label=self._mark("항상 위", self.topmost))
        self.menu.entryconfigure(2, label=self._mark("배경 투명", self.bg_mode == "clear"))
        self.menu.entryconfigure(3, label=self._mark("배경 반투명", self.bg_mode == "dim"))

    def toggle_topmost(self):
        self.topmost = not self.topmost
        self.root.attributes("-topmost", self.topmost)
        self._refresh_menu()

    def toggle_clear(self):
        self.bg_mode = "solid" if self.bg_mode == "clear" else "clear"
        self.apply_background()

    def toggle_dim(self):
        self.bg_mode = "solid" if self.bg_mode == "dim" else "dim"
        self.apply_background()

    def apply_background(self):
        """투명은 숫자와 눈금만 남긴다. 체크를 해제하면 어두운 원으로 돌아간다."""
        self.root.attributes("-transparentcolor", TRANS)
        hwnd = windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
        alpha = 145 if self.bg_mode == "dim" else 255
        windll.user32.SetLayeredWindowAttributes(hwnd, 0x00020101, alpha, 0x1 | 0x2)
        self._refresh_menu()
        self.draw()

    def toggle_run(self):
        if self.running:
            self.pause()
        else:
            self.start()

    def start(self):
        if self.running:
            return
        self._cancel_flash()
        if self.remaining <= 0:
            self.remaining = float(self.total)
            self.finished = False
        self.running = True
        self.deadline = time.monotonic() + self.remaining
        self.draw()
        self.tick()

    def pause(self):
        if not self.running:
            return
        self.running = False
        self._cancel_tick()
        self.remaining = max(0.0, self.deadline - time.monotonic())
        self.draw()

    def reset(self):
        self.running = False
        self.finished = False
        self._cancel_tick()
        self._cancel_flash()
        self.remaining = float(self.total)
        self.draw()

    def tick(self):
        self.remaining = max(0.0, self.deadline - time.monotonic())
        if self.remaining <= 0:
            self.remaining = 0
            self.running = False
            self.finished = True
            self.after_id = None
            play_chime()
            self._start_flash()
            return
        self.draw()
        self.after_id = self.root.after(100, self.tick)

    def _cancel_tick(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def _start_flash(self):
        self._cancel_flash()
        self._pulse()

    def _pulse(self):
        if not self.finished:
            return
        self.flash_on = not self.flash_on
        self.draw()
        self.flash_after_id = self.root.after(240, self._pulse)

    def _cancel_flash(self):
        if self.flash_after_id is not None:
            self.root.after_cancel(self.flash_after_id)
            self.flash_after_id = None
        self.flash_on = False

    def _time_text(self):
        whole = max(0, math.ceil(self.remaining - 1e-9))
        minutes, seconds = divmod(whole, 60)
        return f"{minutes:02d}:{seconds:02d}"

    def draw(self):
        canvas = self.canvas
        canvas.delete("all")
        radius = self.radius
        # 배경 투명일 때는 검은 원을 그리지 않는다. 캔버스 바탕색이 창에서 빠진다.
        if self.bg_mode != "clear":
            canvas.create_oval(
                self.cx - radius,
                self.cy - radius,
                self.cx + radius,
                self.cy + radius,
                fill=FACE,
                outline=EDGE,
                width=2,
            )
            self._draw_circuits(radius * 0.62)
        self._draw_ticks(radius)
        if self.finished and self.flash_on:
            glow = radius * 0.72
            canvas.create_oval(
                self.cx - glow,
                self.cy - glow,
                self.cx + glow,
                self.cy + glow,
                fill=FLASH,
                outline=TICK_CORE,
                width=3,
            )
        self._draw_time()

    def _draw_circuits(self, radius):
        canvas = self.canvas
        cx, cy = self.cx, self.cy
        canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, outline=CIRCUIT, width=1)
        canvas.create_oval(
            cx - radius * 0.48,
            cy - radius * 0.48,
            cx + radius * 0.48,
            cy + radius * 0.48,
            outline=CIRCUIT,
            width=1,
        )
        for degrees in (30, 100, 160, 210, 250, 310, 345):
            theta = math.radians(degrees)
            pad_x = cx + math.cos(theta) * radius * 0.78
            pad_y = cy + math.sin(theta) * radius * 0.78
            canvas.create_oval(pad_x - 3, pad_y - 3, pad_x + 3, pad_y + 3, outline=CIRCUIT, width=1)
        canvas.create_line(cx - radius, cy - 8, cx - 18, cy - 8, cx - 18, cy - radius * 0.55, fill=CIRCUIT, width=1)
        canvas.create_line(cx + 16, cy + 10, cx + radius * 0.7, cy + 10, cx + radius * 0.7, cy + radius * 0.45, fill=CIRCUIT)
        canvas.create_line(cx - 8, cy - radius * 0.2, cx - 8, cy - radius, fill=CIRCUIT)
        canvas.create_line(cx - radius * 0.2, cy + radius * 0.35, cx + radius * 0.45, cy + radius * 0.35, fill=CIRCUIT)

    def _draw_ticks(self, radius):
        lit = 0
        if self.remaining > 0:
            lit = min(MAX_MINUTES, max(0, math.ceil(self.remaining / 60 - 1e-9)))
        inner = radius * 0.60
        outer = radius * 0.96
        for index in range(lit):
            theta = math.radians(index * (360 / MAX_MINUTES))
            outward_x = math.sin(theta)
            outward_y = -math.cos(theta)
            side_x = math.cos(theta)
            side_y = math.sin(theta)
            inner_half = 1.6
            outer_half = 4.4
            points = [
                self.cx + outward_x * inner + side_x * inner_half,
                self.cy + outward_y * inner + side_y * inner_half,
                self.cx + outward_x * outer + side_x * outer_half,
                self.cy + outward_y * outer + side_y * outer_half,
                self.cx + outward_x * outer - side_x * outer_half,
                self.cy + outward_y * outer - side_y * outer_half,
                self.cx + outward_x * inner - side_x * inner_half,
                self.cy + outward_y * inner - side_y * inner_half,
            ]
            self.canvas.create_polygon(points, fill=TICK, outline=TICK_CORE, width=1)

    def _draw_time(self):
        text = self._time_text()
        digit_w, digit_h, gap = 28, 48, 7
        colon_w = 16
        widths = [colon_w if char == ":" else digit_w for char in text]
        total = sum(widths) + gap * (len(text) - 1)
        x = self.cx - total / 2
        top = self.cy - digit_h / 2
        if self.finished and self.flash_on:
            color = FLASH_DIGIT
        elif self.bg_mode == "clear":
            color = TICK
        else:
            color = DIGIT
        for char, width in zip(text, widths):
            if char == ":":
                dot_x = x + width / 2
                for dot_y in (top + digit_h * 0.32, top + digit_h * 0.68):
                    self.canvas.create_oval(dot_x - 3, dot_y - 3, dot_x + 3, dot_y + 3, fill=color, outline=color)
            else:
                self._draw_digit(char, x, top, digit_w, digit_h, color)
            x += width + gap

    def _draw_digit(self, char, x, y, width, height, color):
        thickness = 5
        for segment in SEGMENTS[char]:
            if segment in "adg":
                y0 = {"a": y + 1, "g": y + height / 2 - thickness / 2, "d": y + height - thickness - 1}[segment]
                inset = 4
                self.canvas.create_line(
                    x + inset,
                    y0 + thickness / 2,
                    x + width - inset,
                    y0 + thickness / 2,
                    fill=color,
                    width=thickness,
                    capstyle="round",
                )
            else:
                x0 = x + width - thickness if segment in "bc" else x + 1
                if segment in "bf":
                    y0, y1 = y + 6, y + height / 2 - 3
                else:
                    y0, y1 = y + height / 2 + 3, y + height - 6
                self.canvas.create_line(
                    x0 + thickness / 2,
                    y0,
                    x0 + thickness / 2,
                    y1,
                    fill=color,
                    width=thickness,
                    capstyle="round",
                )


def main():
    enable_sharp_text()
    root = tk.Tk()
    root.withdraw()
    root.title("집중 타이머")
    root.overrideredirect(True)
    root.configure(bg=TRANS)
    root.attributes("-transparentcolor", TRANS)
    root.attributes("-topmost", True)
    width = height = SIZE
    x = (root.winfo_screenwidth() - width) // 2
    y = (root.winfo_screenheight() - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")
    timer = FocusTimer(root)
    root.deiconify()
    root.after(50, timer.apply_background)
    root.mainloop()


if __name__ == "__main__":
    main()
