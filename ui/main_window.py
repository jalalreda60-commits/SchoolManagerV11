import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QSizePolicy)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QIcon

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(BASE_DIR, 'assets', 'school_logo.png')
ICON_PATH = os.path.join(BASE_DIR, 'assets', 'school_logo.ico')


class NavButton(QPushButton):
    def __init__(self, icon_text, label, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setObjectName('nav_btn')
        self.setText(f'  {icon_text}   {label}')
        self.setFixedHeight(42)
        self.setCursor(Qt.PointingHandCursor)


class MainWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setWindowTitle('Le Schéma SGS v3')
        self.setMinimumSize(1340, 820)
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))

        from models.database import get_session
        self.session = get_session()
        self._pages = {}
        self._init_ui()
        self._navigate(0)

    def closeEvent(self, e):
        self.session.close()
        super().closeEvent(e)

    def _init_ui(self):
        from themes.style import LIGHT_THEME
        self.setStyleSheet(LIGHT_THEME)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(240)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(0, 0, 0, 0)
        sb.setSpacing(0)

        # Logo
        logo_zone = QWidget()
        logo_zone.setFixedHeight(72)
        logo_zone.setStyleSheet('background:transparent; border-bottom:1px solid #EAEDF3;')
        lz = QHBoxLayout(logo_zone); lz.setContentsMargins(16, 0, 16, 0); lz.setSpacing(12)
        logo_lbl = QLabel()
        if os.path.exists(LOGO_PATH):
            pix = QPixmap(LOGO_PATH).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        logo_lbl.setFixedSize(42, 42)
        txt_col = QVBoxLayout(); txt_col.setSpacing(1)
        name_lbl = QLabel('Le Schéma')
        name_lbl.setStyleSheet('color:#1A1D2E; font-size:14px; font-weight:700; background:transparent;')
        sub_lbl = QLabel('Gestion Scolaire v3')
        sub_lbl.setStyleSheet('color:#9CA3AF; font-size:10px; background:transparent;')
        txt_col.addWidget(name_lbl); txt_col.addWidget(sub_lbl)
        lz.addWidget(logo_lbl); lz.addLayout(txt_col); lz.addStretch()
        sb.addWidget(logo_zone)
        sb.addSpacing(10)

        def section_sep(text):
            lbl = QLabel(f'  {text}')
            lbl.setStyleSheet('color:#9CA3AF; font-size:10px; font-weight:700; letter-spacing:1px; padding:6px 18px 2px 18px; background:transparent;')
            return lbl

        # Navigation items — index maps to _get_page(idx)
        NAV_MAIN = [
            ('🏠', 'Tableau de Bord',   0),
            ('🎓', 'Élèves',            1),
            ('💳', 'Paiements',         2),
            ('🛡️', 'Assurances',         3),   # ← MODULE 2
            ('👥', 'Personnel',         4),
            ('💸', 'Dépenses',          5),
        ]
        NAV_ADMIN = [
            ('🚌', 'Transport',         6),
            ('📅', 'Emploi du Temps',   7),
            ('📊', 'Rapports',          8),
            ('📥', 'Import Excel',      9),
            ('⚙️',  'Paramètres',        10),
        ]

        sb.addWidget(section_sep('MENU PRINCIPAL'))
        self.nav_btns = []
        for icon, label, idx in NAV_MAIN:
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda _, i=idx: self._navigate(i))
            sb.addWidget(btn)
            self.nav_btns.append((idx, btn))

        sb.addSpacing(6)
        sb.addWidget(section_sep('ADMINISTRATION'))
        for icon, label, idx in NAV_ADMIN:
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda _, i=idx: self._navigate(i))
            sb.addWidget(btn)
            self.nav_btns.append((idx, btn))

        sb.addStretch()

        # User card
        user_card = QFrame()
        user_card.setStyleSheet('QFrame { background:#F7F8FC; border-top:1px solid #EAEDF3; }')
        user_card.setFixedHeight(72)
        uc = QHBoxLayout(user_card); uc.setContentsMargins(16, 12, 16, 12); uc.setSpacing(10)
        role_icons = {'admin': '👑', 'comptable': '💼', 'secretaire': '📋'}
        avatar = QLabel(role_icons.get(self.user.role, '👤'))
        avatar.setFixedSize(36, 36); avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet('background:#EEF2FF; border-radius:18px; font-size:17px;')
        info_col = QVBoxLayout(); info_col.setSpacing(1)
        uname = QLabel(self.user.full_name or self.user.username)
        uname.setStyleSheet('color:#1A1D2E; font-weight:600; font-size:12px; background:transparent;')
        urole = QLabel(self.user.role.capitalize())
        urole.setStyleSheet('color:#9CA3AF; font-size:10px; background:transparent;')
        info_col.addWidget(uname); info_col.addWidget(urole)
        logout = QPushButton('↩')
        logout.setFixedSize(30, 30); logout.setToolTip('Déconnexion'); logout.setCursor(Qt.PointingHandCursor)
        logout.setStyleSheet('QPushButton { background:transparent; color:#9CA3AF; border:none; font-size:16px; border-radius:6px; } QPushButton:hover { background:#FEE2E2; color:#EF4444; }')
        logout.clicked.connect(self._logout)
        uc.addWidget(avatar); uc.addLayout(info_col); uc.addStretch(); uc.addWidget(logout)
        sb.addWidget(user_card)

        # ── Content area ──────────────────────────────────────────────
        content = QWidget(); content.setStyleSheet('background:#F7F8FC;')
        cl = QVBoxLayout(content); cl.setContentsMargins(0, 0, 0, 0); cl.setSpacing(0)

        # Topbar
        topbar = QFrame(); topbar.setObjectName('topbar'); topbar.setFixedHeight(58)
        tb = QHBoxLayout(topbar); tb.setContentsMargins(28, 0, 28, 0)
        self.page_title = QLabel('Tableau de Bord')
        self.page_title.setStyleSheet('color:#1A1D2E; font-size:18px; font-weight:700; background:transparent;')
        from datetime import datetime
        date_lbl = QLabel(datetime.now().strftime('%A %d %B %Y'))
        date_lbl.setStyleSheet('color:#9CA3AF; font-size:12px; background:transparent;')
        refresh_btn = QPushButton('↺  Actualiser')
        refresh_btn.setFixedHeight(34); refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet('QPushButton { background:#F3F4F6; color:#374151; border:1px solid #E5E7EB; border-radius:8px; padding:0 16px; font-size:12px; font-weight:500; } QPushButton:hover { background:#E5E7EB; }')
        refresh_btn.clicked.connect(self._refresh_current)
        tb.addWidget(self.page_title); tb.addStretch()
        tb.addWidget(date_lbl); tb.addSpacing(16); tb.addWidget(refresh_btn)

        self.stack = QStackedWidget(); self.stack.setStyleSheet('background:transparent;')
        cl.addWidget(topbar); cl.addWidget(self.stack, 1)
        root.addWidget(sidebar); root.addWidget(content, 1)

    # ── Page factory ─────────────────────────────────────────────────
    def _get_page(self, idx):
        if idx in self._pages:
            return self._pages[idx]

        titles = [
            'Tableau de Bord', 'Gestion des Élèves', 'Historique Paiements',
            'Gestion des Assurances',                              # 3 ← new
            'Personnel & Enseignants', 'Dépenses', 'Transport',
            'Emploi du Temps', 'Rapports & Exports', 'Import Excel', 'Paramètres'
        ]

        if   idx == 0:
            from ui.dashboard             import DashboardWidget;             w = DashboardWidget(self.session)
        elif idx == 1:
            from ui.students              import StudentsWidget;              w = StudentsWidget(self.session)
        elif idx == 2:
            from ui.payments_history      import PaymentsHistoryWidget;       w = PaymentsHistoryWidget(self.session)
        elif idx == 3:                                                         # ← MODULE 2
            from ui.insurance_dialog      import InsuranceManagementWidget;   w = InsuranceManagementWidget(self.session)
        elif idx == 4:
            from ui.employees             import EmployeesWidget;             w = EmployeesWidget(self.session)
        elif idx == 5:
            from ui.expenses              import ExpensesWidget;              w = ExpensesWidget(self.session)
        elif idx == 6:
            from ui.transport             import TransportWidget;             w = TransportWidget(self.session)
        elif idx == 7:
            from ui.timetable             import TimetableWidget;             w = TimetableWidget(self.session)
        elif idx == 8:
            from ui.reports               import ReportsWidget;               w = ReportsWidget(self.session)
        elif idx == 9:
            from ui.import_center         import ImportCenter;                w = ImportCenter(self.session)
        elif idx == 10:
            from ui.settings_widget       import SettingsWidget;              w = SettingsWidget(self.session)
        else:
            from PySide6.QtWidgets import QLabel
            w = QLabel(f'Page {idx}')

        self.stack.addWidget(w)
        self._pages[idx] = w
        return w

    def _navigate(self, idx):
        titles = [
            'Tableau de Bord', 'Gestion des Élèves', 'Historique Paiements',
            'Gestion des Assurances',
            'Personnel & Enseignants', 'Dépenses', 'Transport',
            'Emploi du Temps', 'Rapports & Exports', 'Import Excel', 'Paramètres'
        ]
        for i, btn in self.nav_btns:
            btn.setChecked(i == idx)
        if idx < len(titles):
            self.page_title.setText(titles[idx])
        self.stack.setCurrentWidget(self._get_page(idx))

    def _refresh_current(self):
        idx = next((i for i, btn in self.nav_btns if btn.isChecked()), 0)
        if idx in self._pages:
            w = self._pages[idx]
            if   hasattr(w, 'refresh'):         w.refresh()
            elif hasattr(w, '_load_data'):      w._load_data()
            elif hasattr(w, '_load_students'):  w._load_students()

    def _logout(self):
        self.session.close()
        self.close()
        from ui.login_window import LoginWindow
        self._login = LoginWindow(self._relogin)
        self._login.show()

    def _relogin(self, user):
        self._login.close()
        from models.database import get_session
        self.session = get_session()
        self.user    = user
        self._pages.clear()
        while self.stack.count():
            self.stack.removeWidget(self.stack.widget(0))
        self._navigate(0)
        self.show()
