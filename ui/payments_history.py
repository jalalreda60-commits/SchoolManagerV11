"""
payments_history.py — SGS v4
Payments history widget.
Top toolbar includes "Ajouter Paiement" button that opens AddPaymentDialog
(student selector → PaymentDialog).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QLineEdit,
    QHeaderView, QAbstractItemView, QFrame, QMessageBox
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from datetime import datetime

from models.database import Payment, Receipt, Student, MonthRecord, SCHOOL_MONTHS
from themes.style import (
    SCHOOL_MONTHS as MONTHS, TABLE_CSS, PRIMARY, PRIMARY_LIGHT,
    SUCCESS, SUCCESS_LIGHT, WARNING, WARNING_LIGHT, INFO, INFO_LIGHT,
    NAN_COLOR, NAN_TEXT, DANGER, DANGER_LIGHT, BORDER, TEXT_MAIN, TEXT_SUB
)

BTN = (f'QPushButton {{ background: {PRIMARY}; color: white; border: none; '
       f'border-radius: 8px; padding: 9px 20px; font-weight: 600; font-size: 13px; }}'
       f'QPushButton:hover {{ background: #4338CA; }}')
BTN_SEC = ('QPushButton { background: #F3F4F6; color: #374151; border: 1px solid #E5E7EB; '
           'border-radius: 8px; padding: 9px 20px; font-weight: 500; }'
           'QPushButton:hover { background: #E5E7EB; }')
BTN_SUC = (f'QPushButton {{ background: {SUCCESS}; color: white; border: none; '
           f'border-radius: 8px; padding: 9px 20px; font-weight: 600; font-size: 13px; }}'
           f'QPushButton:hover {{ background: #059669; }}')


def _mini_card(label, value, accent, light):
    card = QFrame()
    card.setStyleSheet(
        f'QFrame {{ background: {light}; border: 1px solid {accent}33; '
        f'border-radius: 12px; border-left: 4px solid {accent}; }}'
    )
    card.setFixedHeight(78)
    cl = QVBoxLayout(card)
    cl.setContentsMargins(16, 12, 16, 10)
    cl.setSpacing(3)
    val = QLabel(value)
    val.setStyleSheet(f'color: {accent}; font-size: 20px; font-weight: 800; background: transparent;')
    lbl = QLabel(label)
    lbl.setStyleSheet(f'color: {TEXT_SUB}; font-size: 11px; font-weight: 500; background: transparent;')
    cl.addWidget(val)
    cl.addWidget(lbl)
    card._val = val
    return card


class PaymentsHistoryWidget(QWidget):
    def __init__(self, session):
        super().__init__()
        self.session = session
        self.setStyleSheet('background: transparent;')
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # ── Title + Add button ────────────────────────────────────────────────
        title_row = QHBoxLayout()
        title = QLabel('💳  Historique des Paiements')
        title.setStyleSheet(
            f'color: {TEXT_MAIN}; font-size: 16px; font-weight: 800; background: transparent;'
        )
        title_row.addWidget(title)
        title_row.addStretch()

        add_btn = QPushButton('➕  Ajouter Paiement')
        add_btn.setStyleSheet(BTN_SUC)
        add_btn.setFixedHeight(38)
        add_btn.clicked.connect(self._open_add_payment)
        title_row.addWidget(add_btn)
        layout.addLayout(title_row)

        # ── Filters toolbar ───────────────────────────────────────────────────
        tb = QHBoxLayout()
        tb.setSpacing(10)

        search_css = (
            f'QLineEdit {{ background: white; border: 1.5px solid {BORDER}; '
            f'border-radius: 10px; color: {TEXT_MAIN}; padding: 0 14px; '
            f'font-size: 13px; height: 40px; }}'
            f'QLineEdit:focus {{ border-color: {PRIMARY}; }}'
        )
        combo_css = (
            f'QComboBox {{ background: white; border: 1.5px solid {BORDER}; '
            f'border-radius: 10px; color: {TEXT_MAIN}; padding: 0 12px; '
            f'font-size: 13px; min-width: 140px; height: 40px; }}'
            f'QComboBox QAbstractItemView {{ background: white; border: 1.5px solid #C7D2FE; '
            f'border-radius: 10px; color: {TEXT_MAIN}; padding: 4px; outline: none; }}'
            f'QComboBox QAbstractItemView::item {{ padding: 9px 14px; border-radius: 6px; '
            f'margin: 1px 4px; color: {TEXT_MAIN}; }}'
            f'QComboBox QAbstractItemView::item:hover {{ background: #F5F3FF; color: {PRIMARY}; }}'
            f'QComboBox QAbstractItemView::item:selected {{ background: {PRIMARY_LIGHT}; color: {PRIMARY}; }}'
        )

        self.search = QLineEdit()
        self.search.setPlaceholderText('🔍  Rechercher élève ou N° reçu...')
        self.search.setFixedWidth(300)
        self.search.setStyleSheet(search_css)
        self.search.textChanged.connect(self._filter)

        self.type_filter = QComboBox()
        self.type_filter.setStyleSheet(combo_css)
        self.type_filter.addItem('Tous types', '')
        self.type_filter.addItem('📅 Mensualités', 'monthly')
        self.type_filter.addItem('🛡️ Assurances', 'insurance')
        self.type_filter.addItem('🚌 Transport', 'transport')
        self.type_filter.currentIndexChanged.connect(self._filter)

        self.month_filter = QComboBox()
        self.month_filter.setStyleSheet(combo_css)
        self.month_filter.addItem('Tous les mois', '')
        for m in MONTHS:
            self.month_filter.addItem(m, m)
        self.month_filter.currentIndexChanged.connect(self._filter)

        open_btn = QPushButton('🧾  Ouvrir Reçu')
        open_btn.setFixedHeight(40)
        open_btn.setStyleSheet(BTN_SEC)
        open_btn.clicked.connect(self._open_receipt)

        refresh_btn = QPushButton('🔄')
        refresh_btn.setFixedSize(40, 40)
        refresh_btn.setStyleSheet(BTN_SEC)
        refresh_btn.setToolTip('Rafraîchir')
        refresh_btn.clicked.connect(self._load_data)

        tb.addWidget(self.search)
        tb.addWidget(self.type_filter)
        tb.addWidget(self.month_filter)
        tb.addStretch()
        tb.addWidget(open_btn)
        tb.addWidget(refresh_btn)
        layout.addLayout(tb)

        # ── Summary cards ─────────────────────────────────────────────────────
        cr = QHBoxLayout()
        cr.setSpacing(12)
        self.c_total   = _mini_card('Total encaissé',  '0 MAD', SUCCESS,    SUCCESS_LIGHT)
        self.c_monthly = _mini_card('Mensualités',     '0 MAD', PRIMARY,    PRIMARY_LIGHT)
        self.c_ins     = _mini_card('Assurances',      '0 MAD', INFO,       INFO_LIGHT)
        self.c_trans   = _mini_card('Transport',       '0 MAD', '#0369A1',  '#DBEAFE')
        for c in [self.c_total, self.c_monthly, self.c_ins, self.c_trans]:
            cr.addWidget(c)
        layout.addLayout(cr)

        # ── Table ─────────────────────────────────────────────────────────────
        tcard = QFrame()
        tcard.setStyleSheet(
            f'QFrame {{ background: white; border: 1px solid {BORDER}; border-radius: 14px; }}'
        )
        tcl = QVBoxLayout(tcard)
        tcl.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ['N° Reçu', 'Élève', 'Classe', 'Type', 'Période', 'Montant', 'Date', 'Statut']
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(TABLE_CSS)
        tcl.addWidget(self.table)
        layout.addWidget(tcard, 1)

        self.status_lbl = QLabel()
        self.status_lbl.setStyleSheet('color: #9CA3AF; font-size: 12px; background: transparent;')
        layout.addWidget(self.status_lbl)

        self.all_payments = []

    # ── Data ──────────────────────────────────────────────────────────────────

    def _load_data(self):
        self.session.expire_all()
        self.all_payments = (
            self.session.query(Payment)
            .order_by(Payment.payment_date.desc())
            .limit(500)
            .all()
        )
        self._populate_table(self.all_payments)

    def _populate_table(self, payments):
        type_map = {
            'monthly':   '📅 Mensualité',
            'insurance': '🛡️ Assurance',
            'transport': '🚌 Transport',
        }
        type_colors = {
            'monthly':   PRIMARY,
            'insurance': INFO,
            'transport': '#0369A1',
        }

        self.table.setRowCount(len(payments))
        total = monthly_t = ins_t = trans_t = 0

        for row, p in enumerate(payments):
            student = self.session.query(Student).filter_by(id=p.student_id).first()
            name  = f'{student.first_name} {student.last_name}' if student else '—'
            cls   = student.class_name if student else '—'
            color = type_colors.get(p.payment_type, TEXT_SUB)

            items_data = [
                (p.receipt_number or '—',                                '#6B7280', False),
                (name,                                                    TEXT_MAIN, True),
                (cls,                                                     PRIMARY,   False),
                (type_map.get(p.payment_type, p.payment_type or '—'),   color,     False),
                (f'{p.month or "—"} {p.year or ""}',                    TEXT_MAIN, False),
                (f'{p.amount:,.2f} MAD',                                 SUCCESS,   True),
                (p.payment_date.strftime('%d/%m/%Y  %H:%M')
                 if p.payment_date else '—',                             TEXT_SUB,  False),
                ('✅  Payé',                                              SUCCESS,   False),
            ]
            for col, (text, fg, bold) in enumerate(items_data):
                item = QTableWidgetItem(str(text))
                item.setForeground(QColor(fg))
                if bold:
                    f = item.font(); f.setBold(True); item.setFont(f)
                self.table.setItem(row, col, item)
            self.table.setRowHeight(row, 42)

            a = p.amount or 0
            total += a
            if p.payment_type == 'monthly':
                monthly_t += a
            elif p.payment_type == 'insurance':
                ins_t += a
            elif p.payment_type == 'transport':
                trans_t += a

        self.c_total._val.setText(f'{total:,.0f} MAD')
        self.c_monthly._val.setText(f'{monthly_t:,.0f} MAD')
        self.c_ins._val.setText(f'{ins_t:,.0f} MAD')
        self.c_trans._val.setText(f'{trans_t:,.0f} MAD')
        self.status_lbl.setText(
            f'{len(payments)} paiements  •  Total: {total:,.2f} MAD'
        )

    def _filter(self):
        search   = self.search.text().lower()
        pay_type = self.type_filter.currentData()
        month    = self.month_filter.currentData()
        filtered = []
        for p in self.all_payments:
            student = self.session.query(Student).filter_by(id=p.student_id).first()
            name = (
                f'{(student.first_name or "")} {(student.last_name or "")}'.lower()
                if student else ''
            )
            rec = (p.receipt_number or '').lower()
            if search and search not in name and search not in rec:
                continue
            if pay_type and p.payment_type != pay_type:
                continue
            if month and p.month != month:
                continue
            filtered.append(p)
        self._populate_table(filtered)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _open_add_payment(self):
        """Open student selector → PaymentDialog."""
        from ui.payment_dialog import AddPaymentDialog
        dlg = AddPaymentDialog(self, self.session)
        dlg.exec()
        # Refresh after dialog closes
        self._load_data()

    def _open_receipt(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'Sélection', 'Sélectionnez un paiement.')
            return
        rec_num = self.table.item(row, 0).text()
        receipt = self.session.query(Receipt).filter_by(receipt_number=rec_num).first()
        if receipt and receipt.pdf_path and os.path.exists(receipt.pdf_path):
            import subprocess
            import platform
            if platform.system() == 'Linux':
                subprocess.Popen(['xdg-open', receipt.pdf_path])
            elif platform.system() == 'Darwin':
                subprocess.Popen(['open', receipt.pdf_path])
            else:
                try:
                    os.startfile(receipt.pdf_path)
                except Exception:
                    pass
        else:
            QMessageBox.warning(self, 'Introuvable', 'Le PDF de ce reçu est introuvable.')
