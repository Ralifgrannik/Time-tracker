import sys
import time
import datetime
import os
import json
import random
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QFrame
)
from PyQt6.QtCore import QTimer, Qt, QPoint, QPointF
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QIcon
from PyQt6.QtCharts import QChart, QChartView, QBarSeries, QBarSet, QValueAxis, QBarCategoryAxis

# --- OpenAI Professional Palette ---
COLOR_BG = "#1a1a1e"
COLOR_CARD = "rgba(45, 45, 50, 210)" 
COLOR_ACCENT = "#10a37f" 
COLOR_TEXT_MAIN = "#ececec"
COLOR_TEXT_DIM = "#949494"
COLOR_BORDER = "#3e3e42"
COLOR_DANGER = "#ef4444"

STATS_FILE = "study_stats.json"
import os
import sys

# Функция для поиска ресурсов внутри собранного .exe
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# В классе StudyTimerWindow измените загрузку иконки:
# if os.path.exists(resource_path("icon.ico")):
#     self.setWindowIcon(QIcon(resource_path("icon.ico")))
class NeuralBackground(QWidget):
    """Виджет с анимированной нейронной сетью"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points = []
        self.num_points = 45
        for _ in range(self.num_points):
            self.points.append({
                "pos": QPointF(random.random() * 900, random.random() * 650),
                "vel": QPointF((random.random() - 0.5) * 0.5, (random.random() - 0.5) * 0.5)
            })
        
        # Таймер для анимации (60 FPS)
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(16)

    def update_animation(self):
        for p in self.points:
            p["pos"] += p["vel"]
            
            # Отскок от границ
            if p["pos"].x() < 0 or p["pos"].x() > self.width(): p["vel"].setX(-p["vel"].x())
            if p["pos"].y() < 0 or p["pos"].y() > self.height(): p["vel"].setY(-p["vel"].y())
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.fillRect(self.rect(), QColor(COLOR_BG))
        
        # Линии связей
        pen = QPen(QColor(255, 255, 255, 15))
        painter.setPen(pen)
        for i in range(self.num_points):
            p1 = self.points[i]["pos"]
            for j in range(i + 1, self.num_points):
                p2 = self.points[j]["pos"]
                dist = (p1.x() - p2.x())**2 + (p1.y() - p2.y())**2
                if dist < 12000:
                    painter.drawLine(p1, p2)
        
        # Сами нейроны
        painter.setBrush(QColor(255, 255, 255, 30))
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self.points:
            painter.drawEllipse(p["pos"], 1.5, 1.5)

class StyledCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_CARD};
                border: 1px solid {COLOR_BORDER};
                border-radius: 16px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)

class StudyTimerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.stats = load_stats()
        self.daily_seconds = self.calculate_daily()
        
        self.setWindowTitle("Focus")
        self.setFixedSize(850, 600)
        
        # Иконка приложения
        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))
        
        # Фон
        self.bg = NeuralBackground(self)
        self.setCentralWidget(self.bg)
        
        # Контент
        self.content_widget = QWidget(self.bg)
        self.content_widget.setFixedSize(850, 600)
        main_layout = QVBoxLayout(self.content_widget)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(25)

        # --- ВЕРХНИЙ РЯД ---
        top_row = QHBoxLayout()
        top_row.setSpacing(20)

        # Таймер
        self.timer_card = StyledCard()
        timer_layout = QVBoxLayout(self.timer_card)
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setFont(QFont("Consolas", 62, QFont.Weight.Bold))
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet(f"color: {COLOR_TEXT_MAIN};")
        
        self.toggle_btn = QPushButton("Начать сессию")
        self.toggle_btn.setFixedSize(220, 48)
        self.toggle_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.set_start_style()
        self.toggle_btn.clicked.connect(self.toggle)

        timer_layout.addWidget(self.timer_label)
        timer_layout.addWidget(self.toggle_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Статистика
        info_layout = QVBoxLayout()
        info_layout.setSpacing(15)

        total_card = StyledCard()
        l1 = QVBoxLayout(total_card)
        lbl1 = QLabel("ВСЕГО ВРЕМЕНИ")
        lbl1.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 10px; font-weight: bold;")
        self.total_time_val = QLabel(format_time(self.stats["total_seconds"]))
        self.total_time_val.setStyleSheet(f"color: {COLOR_TEXT_MAIN}; font-size: 24px; font-weight: bold;")
        l1.addWidget(lbl1); l1.addWidget(self.total_time_val)

        # НОВАЯ КАРТОЧКА: ФОКУС СЕГОДНЯ (Вместо цели)
        today_card = StyledCard()
        l2 = QVBoxLayout(today_card)
        lbl2 = QLabel("ФОКУС СЕГОДНЯ")
        lbl2.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 10px; font-weight: bold;")
        self.today_time_val = QLabel(format_time(self.daily_seconds))
        self.today_time_val.setStyleSheet(f"color: {COLOR_TEXT_MAIN}; font-size: 24px; font-weight: bold;")
        l2.addWidget(lbl2); l2.addWidget(self.today_time_val)

        info_layout.addWidget(total_card)
        info_layout.addWidget(today_card)

        top_row.addWidget(self.timer_card, stretch=3)
        top_row.addLayout(info_layout, stretch=2)
        main_layout.addLayout(top_row)

        # --- ГРАФИК ---
        self.chart_card = StyledCard()
        chart_layout = QVBoxLayout(self.chart_card)
        self.chart_view = QChartView(self.create_chart())
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.chart_view.setStyleSheet("background: transparent;")
        chart_layout.addWidget(self.chart_view)
        main_layout.addWidget(self.chart_card)

        # --- ФУТЕР ---
        footer = QHBoxLayout()
        self.reset_btn = QPushButton("Сбросить статистику")
        self.reset_btn.setStyleSheet(f"QPushButton {{ color: {COLOR_TEXT_DIM}; background: transparent; border: 1px solid {COLOR_BORDER}; border-radius: 8px; padding: 5px 15px; font-size: 11px; }} QPushButton:hover {{ color: {COLOR_DANGER}; border-color: {COLOR_DANGER}; }}")
        self.reset_btn.clicked.connect(self.reset_stats)
        footer.addStretch(); footer.addWidget(self.reset_btn)
        main_layout.addLayout(footer)

        self.main_timer = QTimer(self)
        self.main_timer.timeout.connect(self.update_timer)
        self.main_timer.start(1000)
        self.running = False
        self.elapsed = 0

    def set_start_style(self):
        self.toggle_btn.setText("Начать сессию")
        self.toggle_btn.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT}; color: white; border-radius: 8px; border: none; }} QPushButton:hover {{ background-color: #0d8a6a; }}")

    def set_stop_style(self):
        self.toggle_btn.setText("Завершить")
        self.toggle_btn.setStyleSheet(f"QPushButton {{ background-color: #353538; color: {COLOR_DANGER}; border-radius: 8px; border: 1px solid {COLOR_BORDER}; }} QPushButton:hover {{ background-color: #3d1a1a; }}")

    def toggle(self):
        if not self.running:
            self.running = True
            self.start_time = time.time() - self.elapsed
            self.set_stop_style()
        else:
            self.running = False
            self.elapsed = int(time.time() - self.start_time)
            self.save_session()
            self.elapsed = 0
            self.timer_label.setText("00:00:00")
            self.set_start_style()
            self.update_ui()

    def save_session(self):
        if self.elapsed < 1: return
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.stats["history"].append({"date": date_str, "duration_sec": self.elapsed})
        self.stats["total_seconds"] += self.elapsed
        self.daily_seconds += self.elapsed
        save_stats(self.stats)

    def update_timer(self):
        if self.running:
            curr = int(time.time() - self.start_time)
            display_time = format_time(curr)
            self.timer_label.setText(display_time)

    def update_ui(self):
        self.total_time_val.setText(format_time(self.stats["total_seconds"]))
        self.today_time_val.setText(format_time(self.daily_seconds))
        self.chart_view.setChart(self.create_chart())

    def create_chart(self):
        days = { (datetime.date.today() - datetime.timedelta(days=i)).strftime("%d.%m"): 0 for i in range(7) }
        for s in self.stats["history"]:
            try:
                d = datetime.datetime.strptime(s["date"], "%Y-%m-%d %H:%M").strftime("%d.%m")
                if d in days: days[d] += s["duration_sec"]
            except: continue

        series = QBarSeries()
        bar_set = QBarSet("Мин")
        bar_set.setColor(QColor(COLOR_ACCENT))
        categories = list(reversed(list(days.keys())))
        for k in categories: bar_set.append(days[k] // 60)

        series.append(bar_set)
        chart = QChart()
        chart.addSeries(series)
        chart.setBackgroundBrush(QBrush(QColor("transparent")))
        chart.legend().hide()
        chart.layout().setContentsMargins(0, 0, 0, 0)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsColor(QColor(COLOR_TEXT_DIM))
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setLabelsColor(QColor(COLOR_TEXT_DIM))
        axis_y.setGridLineColor(QColor("#333333"))
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)
        return chart

    def calculate_daily(self):
        today = datetime.date.today()
        return sum(s["duration_sec"] for s in self.stats["history"] 
                   if datetime.datetime.strptime(s["date"], "%Y-%m-%d %H:%M").date() == today)

    def reset_stats(self):
        if QMessageBox.question(self, "Сброс", "Удалить весь прогресс?") == QMessageBox.StandardButton.Yes:
            self.stats = {"total_seconds": 0, "sessions": 0, "daily_goal": 7200, "history": []}
            save_stats(self.stats)
            self.daily_seconds = 0
            self.update_ui()

def load_stats():
    default_stats = {"total_seconds": 0, "sessions": 0, "daily_goal": 7200, "history": []}
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_stats.update(data)
                return default_stats
        except: pass
    return default_stats

def save_stats(data):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def format_time(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StudyTimerWindow()
    window.show()
    sys.exit(app.exec())    