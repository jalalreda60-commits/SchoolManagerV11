"""
dashboard.py — SGS v4
Full KPI dashboard:
  - Students: Total / Paid / Unpaid / Outstanding Debt
  - Revenue: Expected / Collected / Gap
  - Insurance: Collected / Students Without Insurance  (EXCLUDED from Monthly Profit)
  - Expenses: Expected / Paid / Remaining
  - Salaries: Total Employees / Paid / Pending / Amount
  - Monthly Profit: Revenue + Transport − Expenses − Salaries  (insurance excluded)
  - Analytics charts: Monthly Profit / Revenue vs Expenses / Student Payment Rate
  - NAN card REMOVED from dashboard (still exists in DB/reports)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QScrollArea, QSizePolicy, QPushButton)
from PySide6.QtCore import Qt
from datetime import datetime

try:
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    HAS_MPL = True
except Exception:
    HAS_MPL = False

from models.database import (Student, Payment, MonthRecord, Employee,
    Salary, Setting, ExpenseCategory, ExpensePayment, SCHOOL_MONTHS)
from themes.style import (PRIMARY, PRIMARY_LIGHT, SUCCESS, SUCCESS_LIGHT, DANGER,
    DANGER_LIGHT, WARNING, WARNING_LIGHT, INFO, INFO_LIGHT, PURPLE, PURPLE_LIGHT,
    PINK, PINK_LIGHT, TEAL, TEAL_LIGHT, NAN_COLOR, NAN_TEXT,
    BG_CARD, BORDER, TEXT_MAIN, TEXT_SUB,
    REINSCRIPTION_LABELS, REINSCRIPTION_COLORS, SCHOOL_MONTHS as MONTHS, CLASSES)


# ── KPI card ──────────────────────────────────────────────────────────────────
def stat_card(icon, label, value, accent, accent_light, subtitle=None):
    card = QFrame()
    card.setObjectName('stat_card')
    card.setMinimumHeight(112)
    card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    card.setStyleSheet(f'''
        QFrame#stat_card {{ background: {BG_CARD}; border: 1px solid {BORDER};
            border-radius: 14px; border-left: 4px solid {accent}; }}
        QFrame#stat_card:hover {{ border-color: {accent}; background: {accent_light}; }}
    ''')
    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 14, 18, 12)
    layout.setSpacing(6)

    top = QHBoxLayout()
    pill = QLabel(icon)
    pill.setFixedSize(36, 36)
    pill.setAlignment(Qt.AlignCenter)
    pill.setStyleSheet(f'background: {accent_light}; border-radius: 10px; font-size: 17px;')
    top.addWidget(pill)
    top.addStretch()
    val_lbl = QLabel(str(value))
    val_lbl.setStyleSheet(
        f'font-size: 22px; font-weight: 800; color: {accent}; background: transparent;'
    )
    top.addWidget(val_lbl)

    lbl = QLabel(label)
    lbl.setStyleSheet(
        f'font-size: 11px; font-weight: 600; color: {TEXT_SUB}; '
        f'letter-spacing: 0.3px; background: transparent;'
    )
    layout.addLayout(top)
    layout.addWidget(lbl)

    if subtitle:
        sub = QLabel(subtitle)
        sub.setStyleSheet(f'font-size: 10px; color: #9CA3AF; background: transparent;')
        layout.addWidget(sub)

    card._val = val_lbl
    card._sub = None
    if subtitle:
        card._sub = sub
    return card


def section_title(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f'color: {TEXT_MAIN}; font-size: 13px; font-weight: 700; '
        f'background: transparent; padding: 4px 0;'
    )
    return lbl


def divider():
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet(f'color: {BORDER}; background: {BORDER}; max-height: 1px;')
    return line


class DashboardWidget(QWidget):
    def __init__(self, session):
        super().__init__()
        self.session = session
        self.setStyleSheet('background: transparent;')
        self._setup_ui()
        self._load_data()

    # ── UI skeleton ───────────────────────────────────────────────────────────
    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet('QScrollArea { border: none; background: transparent; }')

        container = QWidget()
        container.setStyleSheet('background: transparent;')
        self.vl = QVBoxLayout(container)
        self.vl.setContentsMargins(28, 24, 28, 32)
        self.vl.setSpacing(20)

        # Greeting
        now = datetime.now()
        greeting = ('Bonjour' if now.hour < 12
                    else ('Bon après-midi' if now.hour < 18 else 'Bonsoir'))
        g = QLabel(f'{greeting} ☀️')
        g.setStyleSheet('color: #1A1D2E; font-size: 22px; font-weight: 800; background: transparent;')
        d = QLabel(now.strftime('%A %d %B %Y'))
        d.setStyleSheet('color: #9CA3AF; font-size: 12px; background: transparent;')
        gr = QVBoxLayout(); gr.setSpacing(2)
        gr.addWidget(g); gr.addWidget(d)
        gh = QHBoxLayout(); gh.addLayout(gr); gh.addStretch()
        self.vl.addLayout(gh)

        # ── Student KPIs ──────────────────────────────────────────────────────
        self.vl.addWidget(section_title('👤  Élèves'))
        self.sg = QGridLayout(); self.sg.setSpacing(12)
        self.vl.addLayout(self.sg)

        # ── Revenue KPIs ──────────────────────────────────────────────────────
        self.vl.addWidget(divider())
        self.vl.addWidget(section_title('💰  Revenus'))
        self.rg = QGridLayout(); self.rg.setSpacing(12)
        self.vl.addLayout(self.rg)

        # ── Insurance KPIs ────────────────────────────────────────────────────
        self.vl.addWidget(divider())
        self.vl.addWidget(section_title('🛡️  Assurances (suivi séparé, hors bénéfice mensuel)'))
        self.ig = QGridLayout(); self.ig.setSpacing(12)
        self.vl.addLayout(self.ig)

        # ── Expense KPIs ──────────────────────────────────────────────────────
        self.vl.addWidget(divider())
        self.vl.addWidget(section_title('💸  Dépenses'))
        self.eg = QGridLayout(); self.eg.setSpacing(12)
        self.vl.addLayout(self.eg)

        # ── Salary KPIs ───────────────────────────────────────────────────────
        self.vl.addWidget(divider())
        self.vl.addWidget(section_title('👔  Salaires'))
        self.salg = QGridLayout(); self.salg.setSpacing(12)
        self.vl.addLayout(self.salg)

        # ── Monthly Profit ────────────────────────────────────────────────────
        self.vl.addWidget(divider())
        self.vl.addWidget(section_title('📈  Bénéfice mensuel'))
        self.profit_row = QHBoxLayout(); self.profit_row.setSpacing(12)
        self.vl.addLayout(self.profit_row)

        # ── Re-inscription bar ────────────────────────────────────────────────
        self.vl.addWidget(divider())
        self.vl.addWidget(section_title('🔄  Statut Ré-inscription'))
        reinsc_frame = QFrame()
        reinsc_frame.setStyleSheet(
            f'QFrame {{ background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 14px; }}'
        )
        rfl = QVBoxLayout(reinsc_frame)
        rfl.setContentsMargins(20, 16, 20, 16)
        rfl.setSpacing(12)
        self.reinsc_row = QHBoxLayout()
        self.reinsc_row.setSpacing(12)
        rfl.addLayout(self.reinsc_row)
        self.vl.addWidget(reinsc_frame)

        # ── Analytics charts ──────────────────────────────────────────────────
        if HAS_MPL:
            self.vl.addWidget(divider())
            self.vl.addWidget(section_title('📊  Analytiques'))

            # Row 1: Monthly Profit chart + Revenue vs Expenses
            charts_row1 = QHBoxLayout(); charts_row1.setSpacing(16)
            self.profit_chart_frame, self.profit_chart_layout = self._chart_card(
                '📈  Bénéfice mensuel (Revenue + Transport − Dépenses − Salaires)')
            self.revexp_frame, self.revexp_layout = self._chart_card(
                '💰 vs 💸  Revenus vs Dépenses')
            charts_row1.addWidget(self.profit_chart_frame, 1)
            charts_row1.addWidget(self.revexp_frame, 1)
            self.vl.addLayout(charts_row1)

            # Row 2: Student payment rate + Class breakdown
            charts_row2 = QHBoxLayout(); charts_row2.setSpacing(16)
            self.pay_rate_frame, self.pay_rate_layout = self._chart_card(
                '✅  Taux de paiement élèves par mois')
            self.cls_frame, self.cls_layout = self._chart_card(
                '🎓  Répartition par classe')
            charts_row2.addWidget(self.pay_rate_frame, 3)
            charts_row2.addWidget(self.cls_frame, 2)
            self.vl.addLayout(charts_row2)

        # ── Notifications ─────────────────────────────────────────────────────
        self.vl.addWidget(divider())
        self.notif_frame = QFrame()
        self.notif_frame.setStyleSheet(
            f'QFrame {{ background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 14px; }}'
        )
        nfl = QVBoxLayout(self.notif_frame)
        nfl.setContentsMargins(20, 16, 20, 16)
        nfl.setSpacing(8)
        nt = QLabel('🔔  Alertes & Notifications')
        nt.setStyleSheet(
            f'color: {TEXT_MAIN}; font-size: 14px; font-weight: 700; background: transparent;'
        )
        nfl.addWidget(nt)
        self.notif_inner = QVBoxLayout(); self.notif_inner.setSpacing(6)
        nfl.addLayout(self.notif_inner)
        self.vl.addWidget(self.notif_frame)
        self.vl.addStretch()

        scroll.setWidget(container)
        ol = QVBoxLayout(self)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.addWidget(scroll)

    def _chart_card(self, title):
        frame = QFrame()
        frame.setStyleSheet(
            f'QFrame {{ background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 14px; }}'
        )
        frame.setMinimumHeight(280)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        t = QLabel(title)
        t.setStyleSheet(
            f'color: {TEXT_MAIN}; font-size: 12px; font-weight: 700; background: transparent;'
        )
        layout.addWidget(t)
        ph = QLabel('Chargement...')
        ph.setAlignment(Qt.AlignCenter)
        ph.setStyleSheet('color: #D1D5DB; font-size: 13px; background: transparent;')
        layout.addWidget(ph)
        frame._ph = ph
        return frame, layout

    def _clear_chart(self, frame, layout):
        if hasattr(frame, '_ph') and frame._ph:
            frame._ph.setParent(None)
            frame._ph = None
        # remove old canvas
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), FigureCanvas):
                item.widget().setParent(None)

    def _clear_grid(self, grid):
        for i in reversed(range(grid.count())):
            item = grid.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

    # ── Data loading ──────────────────────────────────────────────────────────
    def _load_data(self):
        self.session.expire_all()
        try:
            now = datetime.now()
            cy = now.year
            cm = now.month

            school_year = self._get_setting('school_year', '2024-25')
            students = self.session.query(Student).filter_by(active=True).all()

            # ── Current-month data ────────────────────────────────────────────
            cur_month_name = MONTHS[cm - 9] if cm >= 9 else MONTHS[cm + 3]
            try:
                cur_month_name = MONTHS[
                    [9,10,11,12,1,2,3,4,5,6].index(cm)
                ]
            except ValueError:
                cur_month_name = None

            # Student KPIs
            n_total = len(students)
            records_this_month = {}
            if cur_month_name:
                for r in self.session.query(MonthRecord).filter_by(
                    month_name=cur_month_name, school_year=school_year
                ).all():
                    records_this_month[r.student_id] = r

            n_paid   = sum(1 for s in students
                           if records_this_month.get(s.id) and
                           records_this_month[s.id].status == 'paid')
            n_unpaid = sum(1 for s in students
                           if records_this_month.get(s.id) and
                           records_this_month[s.id].status == 'unpaid')
            # Outstanding debt = sum of (monthly_fee + transport_fee) for all unpaid months
            all_unpaid_records = self.session.query(MonthRecord).filter_by(
                status='unpaid', school_year=school_year
            ).all()
            outstanding = 0.0
            for rec in all_unpaid_records:
                s = next((x for x in students if x.id == rec.student_id), None)
                if s:
                    outstanding += (s.monthly_fee or 0) + (
                        s.transport_fee if s.has_transport else 0)

            # ── Revenue KPIs — monthly + transport ONLY, insurance EXCLUDED ──
            all_payments     = self.session.query(Payment).all()
            monthly_payments = [p for p in all_payments
                                if p.payment_type in ('monthly', 'transport')]
            # Insurance filtered by current school_year only
            insurance_payments = [p for p in all_payments
                                  if p.payment_type == 'insurance'
                                  and (p.school_year or '') == school_year]

            # Expected = (monthly_fee + transport) × active (non-NAN) months per student
            expected_revenue = 0.0
            for s in students:
                nan_count = self.session.query(MonthRecord).filter_by(
                    student_id=s.id, school_year=school_year, status='nan'
                ).count()
                active_months = len(MONTHS) - nan_count
                fee_pm = (s.monthly_fee or 0) + (
                    s.transport_fee if s.has_transport else 0)
                expected_revenue += fee_pm * active_months

            # Collected = monthly + transport payments only (insurance never included)
            collected_revenue = sum(p.amount or 0 for p in monthly_payments)
            revenue_gap = max(0.0, expected_revenue - collected_revenue)

            # ── Insurance KPIs — tracked separately, excluded from profit ────
            insurance_collected = sum(p.amount or 0 for p in insurance_payments)
            n_no_insurance = sum(1 for s in students if not s.insurance_paid)

            # ── Expense KPIs — uses ExpenseCategory + ExpensePayment (v4) ────
            from models.database import ExpenseCategory, ExpensePayment
            active_cats = self.session.query(ExpenseCategory).filter_by(active=True).all()
            # Expected = sum of all active category monthly amounts
            expected_expenses = sum(c.monthly_amount or 0 for c in active_cats)
            # Paid this month = ExpensePayments for current school month
            cur_month_str = cur_month_name or ''
            expense_payments_this_month = self.session.query(ExpensePayment).filter_by(
                month=cur_month_str, year=cy
            ).all() if cur_month_str else []
            paid_expenses = sum(p.amount or 0 for p in expense_payments_this_month)
            remaining_expenses = max(0.0, expected_expenses - paid_expenses)

            # ── Salary KPIs ───────────────────────────────────────────────────
            salaries_this_year = [
                s for s in self.session.query(Salary).all()
                if s.year == cy
            ]
            n_employees = self.session.query(Employee).filter_by(active=True).count()
            salaries_paid_count = sum(1 for s in salaries_this_year if s.paid)
            salaries_pending = max(0, n_employees - salaries_paid_count)
            total_salary_paid = sum(
                (s.net_salary or s.total or 0) for s in salaries_this_year if s.paid
            )

            # ── Monthly Profit — Module 6 formula ────────────────────────────
            # profit = (monthly_revenue + transport_revenue)
            #          - expense_payments  (ExpensePayment this month)
            #          - salary_payments   (Salary.net_salary paid this month)
            # Insurance is EXCLUDED from this calculation
            rev_this_month = sum(
                p.amount or 0 for p in monthly_payments
                if p.payment_date and p.payment_date.month == cm
                and p.payment_date.year == cy
            )
            exp_this_month = paid_expenses   # already scoped to current month
            sal_this_month = sum(
                (s.net_salary or s.total or 0) for s in salaries_this_year
                if s.paid and s.paid_date and s.paid_date.month == cm
            )
            monthly_profit = rev_this_month - exp_this_month - sal_this_month

            # ── Re-inscription ────────────────────────────────────────────────
            n_yes  = sum(1 for s in students if getattr(s, 'reinscription_status', 'pending') == 'yes')
            n_no   = sum(1 for s in students if getattr(s, 'reinscription_status', 'pending') == 'no')
            n_pend = sum(1 for s in students if getattr(s, 'reinscription_status', 'pending') == 'pending')

        except Exception as ex:
            import traceback; traceback.print_exc()
            print(f'Dashboard load error: {ex}')
            (n_total, n_paid, n_unpaid, outstanding, expected_revenue,
             collected_revenue, revenue_gap, insurance_collected, n_no_insurance,
             expected_expenses, paid_expenses, remaining_expenses, n_employees,
             salaries_paid_count, salaries_pending, total_salary_paid,
             monthly_profit, n_yes, n_no, n_pend, rev_this_month, exp_this_month) = (0,) * 22
            sal_this_month = 0
            all_payments, monthly_payments, insurance_payments = [], [], []

        # ── Render KPI cards ──────────────────────────────────────────────────

        # Students
        self._clear_grid(self.sg)
        student_cards = [
            ('👥', 'Total élèves',          n_total,                          PRIMARY,  PRIMARY_LIGHT),
            ('✅', 'Payés ce mois',          n_paid,                           SUCCESS,  SUCCESS_LIGHT),
            ('⏳', 'Non payés ce mois',      n_unpaid,                         DANGER,   DANGER_LIGHT),
            ('💳', 'Créances totales',       f'{outstanding:,.0f} MAD',        WARNING,  WARNING_LIGHT),
        ]
        for i, args in enumerate(student_cards):
            self.sg.addWidget(stat_card(*args), 0, i)

        # Revenue
        self._clear_grid(self.rg)
        rev_cards = [
            ('📊', 'Revenus attendus',      f'{expected_revenue:,.0f} MAD',   PURPLE,   PURPLE_LIGHT),
            ('💰', 'Revenus encaissés',     f'{collected_revenue:,.0f} MAD',  SUCCESS,  SUCCESS_LIGHT),
            ('📉', 'Écart de revenus',      f'{revenue_gap:,.0f} MAD',        DANGER,   DANGER_LIGHT),
        ]
        for i, args in enumerate(rev_cards):
            self.rg.addWidget(stat_card(*args), 0, i)

        # Insurance (tracked separately)
        self._clear_grid(self.ig)
        ins_cards = [
            ('🛡️', 'Assurances encaissées', f'{insurance_collected:,.0f} MAD', TEAL,  TEAL_LIGHT),
            ('❌',  'Sans assurance',        n_no_insurance,                   WARNING, WARNING_LIGHT),
        ]
        for i, args in enumerate(ins_cards):
            self.ig.addWidget(stat_card(*args), 0, i)

        # Expenses
        self._clear_grid(self.eg)
        exp_cards = [
            ('📋', 'Dépenses prévues',      f'{expected_expenses:,.0f} MAD',  INFO,     INFO_LIGHT),
            ('💸', 'Dépenses payées',       f'{paid_expenses:,.0f} MAD',      DANGER,   DANGER_LIGHT),
            ('🔖', 'Restant à payer',       f'{remaining_expenses:,.0f} MAD', WARNING,  WARNING_LIGHT),
        ]
        for i, args in enumerate(exp_cards):
            self.eg.addWidget(stat_card(*args), 0, i)

        # Salaries
        self._clear_grid(self.salg)
        sal_cards = [
            ('👔', 'Total employés',        n_employees,                      PRIMARY,  PRIMARY_LIGHT),
            ('✅', 'Salaires versés',        salaries_paid_count,              SUCCESS,  SUCCESS_LIGHT),
            ('⏳', 'Salaires en attente',    max(0, salaries_pending),         DANGER,   DANGER_LIGHT),
            ('💰', 'Montant total versé',    f'{total_salary_paid:,.0f} MAD',  PURPLE,   PURPLE_LIGHT),
        ]
        for i, args in enumerate(sal_cards):
            self.salg.addWidget(stat_card(*args), 0, i)

        # Monthly Profit (formula card)
        for i in reversed(range(self.profit_row.count())):
            w = self.profit_row.itemAt(i).widget()
            if w: w.setParent(None)

        profit_color = SUCCESS if monthly_profit >= 0 else DANGER
        profit_light = SUCCESS_LIGHT if monthly_profit >= 0 else DANGER_LIGHT
        formula_lbl = (f'Revenus ({rev_this_month:,.0f}) − '
                       f'Dépenses ({exp_this_month:,.0f}) − '
                       f'Salaires ({sal_this_month:,.0f})')
        profit_card = stat_card(
            '📈', 'Bénéfice mois en cours',
            f'{monthly_profit:,.0f} MAD',
            profit_color, profit_light,
            subtitle=formula_lbl
        )
        self.profit_row.addWidget(profit_card)

        # Re-inscription
        for i in reversed(range(self.reinsc_row.count())):
            w = self.reinsc_row.itemAt(i).widget()
            if w: w.setParent(None)
        for val, count, color, light in [
            ('yes', n_yes, SUCCESS, SUCCESS_LIGHT),
            ('no',  n_no,  DANGER,  DANGER_LIGHT),
            ('pending', n_pend, WARNING, WARNING_LIGHT),
        ]:
            card = QFrame()
            card.setStyleSheet(
                f'QFrame {{ background: {light}; border: 1px solid {color}33; '
                f'border-radius: 12px; border-left: 4px solid {color}; }}'
            )
            card.setFixedHeight(70)
            ccl = QVBoxLayout(card)
            ccl.setContentsMargins(16, 10, 16, 10)
            ccl.setSpacing(3)
            vl = QLabel(str(count))
            vl.setStyleSheet(
                f'color: {color}; font-size: 20px; font-weight: 800; background: transparent;'
            )
            ll = QLabel(REINSCRIPTION_LABELS.get(val, val))
            ll.setStyleSheet(
                f'color: {TEXT_SUB}; font-size: 11px; font-weight: 500; background: transparent;'
            )
            ccl.addWidget(vl); ccl.addWidget(ll)
            self.reinsc_row.addWidget(card)
        self.reinsc_row.addStretch()

        # Charts
        if HAS_MPL:
            self._draw_monthly_profit(monthly_payments, cy)
            self._draw_rev_vs_exp(monthly_payments, cy)
            self._draw_payment_rate(school_year)
            self._draw_classes()

        # Notifications
        self._draw_notifications(n_no_insurance, n_unpaid, n_pend, outstanding)

    # ── Charts ────────────────────────────────────────────────────────────────

    def _monthly_values_for_year(self, payments, year, types=None):
        """Sum payment amounts per calendar month (1-12) for a given year."""
        result = [0.0] * 12
        for p in payments:
            if p.payment_date and p.payment_date.year == year:
                if types is None or p.payment_type in types:
                    result[p.payment_date.month - 1] += p.amount or 0
        return result

    def _expense_monthly_for_year(self, year):
        """Sum ExpensePayment amounts by calendar month for a given year."""
        result = [0.0] * 12
        for ep in self.session.query(ExpensePayment).filter_by(year=year).all():
            # Map school month name to calendar month index
            month_map = {
                'Septembre': 8, 'Octobre': 9, 'Novembre': 10, 'Décembre': 11,
                'Janvier': 0, 'Février': 1, 'Mars': 2, 'Avril': 3,
                'Mai': 4, 'Juin': 5, 'Juillet': 6, 'Août': 7
            }
            idx = month_map.get(ep.month)
            if idx is not None:
                result[idx] += ep.amount or 0
        return result

    def _salary_monthly_for_year(self, year):
        result = [0.0] * 12
        for s in self.session.query(Salary).filter_by(paid=True).all():
            if s.year == year and s.paid_date:
                result[s.paid_date.month - 1] += s.total or 0
        return result

    def _draw_monthly_profit(self, monthly_payments, year):
        """Bar chart: Profit = Revenue + Transport − Expenses − Salaries per month."""
        self._clear_chart(self.profit_chart_frame, self.profit_chart_layout)
        rev  = self._monthly_values_for_year(monthly_payments, year,
                                              types=['monthly', 'transport'])
        exp  = self._expense_monthly_for_year(year)
        sal  = self._salary_monthly_for_year(year)
        profit = [rev[i] - exp[i] - sal[i] for i in range(12)]
        labels = ['Sep','Oct','Nov','Déc','Jan','Fév','Mar','Avr','Mai','Jun','Jul','Aoû']
        colors = [SUCCESS[1:] if v >= 0 else DANGER[1:] for v in profit]
        colors_hex = [f'#{c}' for c in colors]

        fig = Figure(figsize=(7, 3), facecolor='white')
        ax = fig.add_subplot(111)
        ax.set_facecolor('white')
        bars = ax.bar(range(12), profit, color=colors_hex, width=0.6, zorder=3)
        ax.axhline(0, color='#E5E7EB', linewidth=1, zorder=2)
        ax.set_xticks(range(12))
        ax.set_xticklabels(labels, fontsize=8, color='#9CA3AF')
        ax.yaxis.set_tick_params(labelcolor='#9CA3AF', labelsize=8)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.yaxis.grid(True, color='#F3F4F8', linewidth=1, zorder=0)
        ax.set_axisbelow(True)
        fig.tight_layout(pad=1.5)
        canvas = FigureCanvas(fig)
        canvas.setStyleSheet('background: white;')
        self.profit_chart_layout.addWidget(canvas)

    def _draw_rev_vs_exp(self, monthly_payments, year):
        """Line chart: Revenue vs Expenses per month."""
        self._clear_chart(self.revexp_frame, self.revexp_layout)
        rev = self._monthly_values_for_year(monthly_payments, year,
                                            types=['monthly', 'transport'])
        exp = self._expense_monthly_for_year(year)
        labels = ['Sep','Oct','Nov','Déc','Jan','Fév','Mar','Avr','Mai','Jun','Jul','Aoû']

        fig = Figure(figsize=(7, 3), facecolor='white')
        ax = fig.add_subplot(111)
        ax.set_facecolor('white')
        xs = range(12)
        ax.fill_between(xs, rev, alpha=0.10, color='#10B981')
        ax.fill_between(xs, exp, alpha=0.10, color='#EF4444')
        ax.plot(xs, rev, color='#10B981', linewidth=2.5, marker='o',
                markersize=4, markerfacecolor='white', markeredgewidth=2, label='Revenus')
        ax.plot(xs, exp, color='#EF4444', linewidth=2.5, marker='o',
                markersize=4, markerfacecolor='white', markeredgewidth=2, label='Dépenses')
        ax.set_xticks(range(12))
        ax.set_xticklabels(labels, fontsize=8, color='#9CA3AF')
        ax.yaxis.set_tick_params(labelcolor='#9CA3AF', labelsize=8)
        ax.legend(fontsize=8, frameon=False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.yaxis.grid(True, color='#F3F4F8', linewidth=1)
        ax.set_axisbelow(True)
        fig.tight_layout(pad=1.5)
        canvas = FigureCanvas(fig)
        canvas.setStyleSheet('background: white;')
        self.revexp_layout.addWidget(canvas)

    def _draw_payment_rate(self, school_year):
        """Grouped bar chart: % Paid vs % Unpaid per school month."""
        self._clear_chart(self.pay_rate_frame, self.pay_rate_layout)
        paid_pct, unpaid_pct = [], []
        for month in MONTHS:
            records = self.session.query(MonthRecord).filter_by(
                month_name=month, school_year=school_year
            ).all()
            active = [r for r in records if r.status != 'nan']
            total = len(active)
            if total:
                p = sum(1 for r in active if r.status == 'paid')
                paid_pct.append(100 * p / total)
                unpaid_pct.append(100 * (total - p) / total)
            else:
                paid_pct.append(0.0)
                unpaid_pct.append(0.0)

        short = ['Sep','Oct','Nov','Déc','Jan','Fév','Mar','Avr','Mai','Jun']
        xs = range(len(MONTHS))
        w = 0.38

        fig = Figure(figsize=(8, 3), facecolor='white')
        ax = fig.add_subplot(111)
        ax.set_facecolor('white')
        ax.bar([x - w/2 for x in xs], paid_pct,   width=w,
               color='#10B981', alpha=0.85, label='% Payés',    zorder=3)
        ax.bar([x + w/2 for x in xs], unpaid_pct, width=w,
               color='#EF4444', alpha=0.85, label='% Impayés',  zorder=3)
        ax.set_xticks(list(xs))
        ax.set_xticklabels(short, fontsize=8, color='#9CA3AF')
        ax.yaxis.set_tick_params(labelcolor='#9CA3AF', labelsize=8)
        ax.set_ylim(0, 110)
        ax.legend(fontsize=8, frameon=False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.yaxis.grid(True, color='#F3F4F8', linewidth=1, zorder=0)
        ax.set_axisbelow(True)
        fig.tight_layout(pad=1.5)
        canvas = FigureCanvas(fig)
        canvas.setStyleSheet('background: white;')
        self.pay_rate_layout.addWidget(canvas)

    def _draw_classes(self):
        self._clear_chart(self.cls_frame, self.cls_layout)
        counts, labels = [], []
        for cls in CLASSES:
            c = self.session.query(Student).filter_by(class_name=cls, active=True).count()
            if c > 0:
                counts.append(c)
                labels.append(cls)
        if not counts:
            counts, labels = [1], ['Aucun']
        fig = Figure(figsize=(4, 3), facecolor='white')
        ax = fig.add_subplot(111)
        palette = ['#4F46E5','#10B981','#F59E0B','#EF4444','#8B5CF6','#14B8A6',
                   '#EC4899','#3B82F6','#6D28D9','#059669','#D97706','#DC2626',
                   '#7C3AED','#0D9488','#BE185D','#1D4ED8']
        ax.pie(counts, labels=labels, autopct='%1.0f%%',
               colors=palette[:len(counts)],
               textprops={'fontsize': 8, 'color': '#374151'},
               pctdistance=0.82,
               wedgeprops={'linewidth': 2, 'edgecolor': 'white'})
        fig.tight_layout(pad=0.5)
        canvas = FigureCanvas(fig)
        canvas.setStyleSheet('background: white;')
        self.cls_layout.addWidget(canvas)

    # ── Notifications ─────────────────────────────────────────────────────────
    def _draw_notifications(self, no_ins, unpaid_this_month, reinsc_pend, outstanding):
        for i in reversed(range(self.notif_inner.count())):
            w = self.notif_inner.itemAt(i).widget()
            if w: w.setParent(None)

        notifs = []
        if no_ins:
            notifs.append(('⚠️',  f'{no_ins} élèves sans assurance payée',        WARNING,  WARNING_LIGHT))
        if unpaid_this_month:
            notifs.append(('💳',  f'{unpaid_this_month} élèves non payés ce mois', DANGER,   DANGER_LIGHT))
        if outstanding > 0:
            notifs.append(('📋',  f'Créances totales: {outstanding:,.0f} MAD',     DANGER,   DANGER_LIGHT))
        if reinsc_pend:
            notifs.append(('🔄',  f'{reinsc_pend} ré-inscriptions en attente',     WARNING,  WARNING_LIGHT))
        if not notifs:
            notifs.append(('✅',  'Tout est en ordre — bonne journée !',           SUCCESS,  SUCCESS_LIGHT))

        for icon, msg, color, light in notifs:
            row = QFrame()
            row.setStyleSheet(
                f'QFrame {{ background: {light}; border-radius: 10px; '
                f'border-left: 3px solid {color}; }}'
            )
            rl = QHBoxLayout(row)
            rl.setContentsMargins(14, 8, 14, 8)
            rl.setSpacing(10)
            il = QLabel(icon)
            il.setStyleSheet('font-size: 15px; background: transparent;')
            ml = QLabel(msg)
            ml.setStyleSheet(
                f'color: {TEXT_MAIN}; font-size: 12px; font-weight: 500; background: transparent;'
            )
            rl.addWidget(il); rl.addWidget(ml); rl.addStretch()
            self.notif_inner.addWidget(row)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get_setting(self, key, default=''):
        s = self.session.query(Setting).filter_by(key=key).first()
        return s.value if s else default

    def refresh(self):
        self._load_data()
