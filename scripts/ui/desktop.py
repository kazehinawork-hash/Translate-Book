"""Translate Book — PyQt6 Desktop App with Liquid Glass UI."""
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'common'))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QScrollArea, QFrame,
    QSplitter, QTextEdit, QProgressBar, QLineEdit, QComboBox,
    QDialog, QFormLayout, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette

from styles.theme import *


class GlassFrame(QFrame):
    """Glass morphism frame."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "book-card")
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255,255,255,0.06),
                    stop:1 rgba(255,255,255,0.02));
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: {RADIUS_LG}px;
                padding: 20px;
            }}
        """)


class GlassButton(QPushButton):
    """Glass morphism button."""
    def __init__(self, text, variant="primary", parent=None):
        super().__init__(text, parent)
        styles = {
            "primary": f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(102,126,234,0.4), stop:1 rgba(118,75,162,0.4));
                    border: 1px solid rgba(255,255,255,0.15);
                    border-radius: {RADIUS_SM}px;
                    padding: 10px 20px; font-size: 13px; font-weight: bold; color: white;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(102,126,234,0.6), stop:1 rgba(118,75,162,0.6));
                }}
            """,
            "success": f"""
                QPushButton {{
                    background: rgba(74,222,128,0.25);
                    border: 1px solid rgba(74,222,128,0.3);
                    border-radius: {RADIUS_SM}px;
                    padding: 10px 20px; font-size: 13px; font-weight: bold; color: white;
                }}
                QPushButton:hover {{ background: rgba(74,222,128,0.4); }}
            """,
            "danger": f"""
                QPushButton {{
                    background: rgba(248,113,113,0.25);
                    border: 1px solid rgba(248,113,113,0.3);
                    border-radius: {RADIUS_SM}px;
                    padding: 10px 20px; font-size: 13px; font-weight: bold; color: white;
                }}
                QPushButton:hover {{ background: rgba(248,113,113,0.4); }}
            """,
        }
        self.setStyleSheet(styles.get(variant, styles["primary"]))


class Sidebar(QFrame):
    """Left navigation sidebar."""
    nav_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(4)

        # Logo
        logo = QLabel("📚 Translate Book")
        logo.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {TEXT_PRIMARY}; padding: 8px 8px 20px 8px;")
        layout.addWidget(logo)

        # Nav buttons
        self.buttons = []
        nav_items = [
            ("📖  Sách", 0),
            ("🎧  Audio", 1),
            ("⚙️  API Settings", 2),
        ]

        for text, idx in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=idx: self._on_nav(i))
            self.buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # Status
        self.status_label = QLabel("API: —")
        self.status_label.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; padding: 8px;")
        layout.addWidget(self.status_label)

        self.buttons[0].setChecked(True)

    def _on_nav(self, idx):
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == idx)
        self.nav_changed.emit(idx)

    def update_api_status(self, provider: str, ok: bool):
        color = SUCCESS if ok else ERROR
        self.status_label.setText(f"API: {provider} {'✓' if ok else '✗'}")
        self.status_label.setStyleSheet(f"font-size: 11px; color: {color}; padding: 8px;")


class BookCard(GlassFrame):
    """Card hiển thị 1 cuốn sách."""
    translate_clicked = pyqtSignal(str)

    def __init__(self, slug: str, status: dict, parent=None):
        super().__init__(parent)
        self.slug = slug
        self.status = status
        source = status.get("source", "output")

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Source badge
        if source == "input":
            badge = QLabel("📁 INPUT")
            badge.setStyleSheet(f"font-size: 10px; color: {INFO}; background: {INFO_BG}; padding: 2px 8px; border-radius: 4px; max-width: 60px;")
            layout.addWidget(badge)

        # Title
        title = QLabel(slug)
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {TEXT_PRIMARY};")
        title.setWordWrap(True)
        layout.addWidget(title)

        # Status
        if status.get("has_vi_md"):
            status_text = "✓ Hoan thanh"
            status_color = SUCCESS
        elif source == "input":
            status_text = "Chua dich — dat vao input/"
            status_color = INFO
        elif status.get("progress_count", 0) > 0:
            pct = status["progress_count"] / max(status.get("total_chunks", 1), 1) * 100
            status_text = f"Dang dich {status['progress_count']}/{status.get('total_chunks', '?')} chunks ({pct:.0f}%)"
            status_color = WARNING
        else:
            status_text = "Chua bat dau"
            status_color = TEXT_DIM

        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"font-size: 13px; color: {status_color};")
        layout.addWidget(status_label)

        # Progress bar (chi hien khi co progress)
        if status.get("total_chunks", 0) > 0:
            progress = QProgressBar()
            progress.setMaximum(status["total_chunks"])
            progress.setValue(status.get("progress_count", 0))
            progress.setFormat("")
            progress.setFixedHeight(8)
            progress.setStyleSheet(f"""
                QProgressBar {{
                    background: rgba(255,255,255,0.06);
                    border: none; border-radius: 4px;
                }}
                QProgressBar::chunk {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {PRIMARY}, stop:1 {SECONDARY});
                    border-radius: 3px;
                }}
            """)
            layout.addWidget(progress)

        # Stats row
        if source == "output":
            stats = QHBoxLayout()
            stats.setSpacing(16)
            epub = QLabel(f"EPUB: {'checkmark' if status.get('has_epub') else '-'}")
            epub.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY};")
            stats.addWidget(epub)
            audio = QLabel(f"Audio: {status.get('mp3_count', 0)} files")
            audio.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY};")
            stats.addWidget(audio)
            stats.addStretch()
            layout.addLayout(stats)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        if source == "input":
            translate_btn = GlassButton("Bat dau dich", "success")
        else:
            translate_btn = GlassButton("Dich")
        translate_btn.clicked.connect(lambda: self.translate_clicked.emit(slug))
        btn_layout.addWidget(translate_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)


class LogPanel(QFrame):
    """Realtime log panel."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("log_panel")
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(0,0,0,0.3);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: {RADIUS_MD}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        header = QLabel("📋 Realtime Log")
        header.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_SECONDARY};")
        layout.addWidget(header)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                border: none;
                color: {TEXT_SECONDARY};
                font-family: Consolas, Courier New, monospace;
                font-size: 12px;
            }}
        """)
        layout.addWidget(self.log_text)

    def log(self, message: str, level: str = "info"):
        colors = {"info": TEXT_SECONDARY, "success": SUCCESS, "warning": WARNING, "error": ERROR}
        color = colors.get(level, TEXT_SECONDARY)
        self.log_text.append(f'<span style="color:{color}">{message}</span>')
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )


class BooksPage(QWidget):
    """Trang hiển thị danh sách sách — 2 tab: Input va Output."""
    translate_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(0)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: rgba(255,255,255,0.04);
                color: {TEXT_SECONDARY};
                padding: 10px 24px;
                margin-right: 4px;
                border: none;
                border-bottom: 2px solid transparent;
                font-size: 14px;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                color: {TEXT_PRIMARY};
                border-bottom: 2px solid {PRIMARY};
                background: rgba(255,255,255,0.06);
            }}
            QTabBar::tab:hover {{
                color: {TEXT_PRIMARY};
                background: rgba(255,255,255,0.06);
            }}
        """)

        # Tab Input
        self.input_tab = self._create_tab("📁 Input (Chua dich)")
        self.tabs.addTab(self.input_tab[0], "📁 Input")

        # Tab Output
        self.output_tab = self._create_tab("📖 Output (Da dich)")
        self.tabs.addTab(self.output_tab[0], "📖 Output")

        layout.addWidget(self.tabs)

    def _create_tab(self, title: str) -> tuple:
        """Tao 1 tab voi scroll area."""
        widget = QWidget()
        widget_layout = QVBoxLayout(widget)
        widget_layout.setContentsMargins(0, 8, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        cards_widget = QWidget()
        cards_layout = QVBoxLayout(cards_widget)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        cards_layout.setSpacing(12)
        scroll.setWidget(cards_widget)

        widget_layout.addWidget(scroll)
        return widget, cards_layout

    def load_books(self, statuses: list):
        # Clear both tabs
        for tab_layout in [self.input_tab[1], self.output_tab[1]]:
            while tab_layout.count():
                child = tab_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

        input_statuses = [s for s in statuses if s.get("source") == "input"]
        output_statuses = [s for s in statuses if s.get("source") != "input"]

        # Input tab
        if input_statuses:
            for s in input_statuses:
                card = BookCard(s.get("slug", s.get("slug_key", "")), s)
                card.translate_clicked.connect(self.translate_clicked.emit)
                self.input_tab[1].addWidget(card)
        else:
            empty = QLabel("Khong co sach nao trong input/\nDat file PDF/EPUB vao thu muc input/")
            empty.setStyleSheet(f"color: {TEXT_DIM}; font-size: 14px; padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.input_tab[1].addWidget(empty)
        self.input_tab[1].addStretch()

        # Update tab title with count
        self.tabs.setTabText(0, f"📁 Input ({len(input_statuses)})")

        # Output tab
        if output_statuses:
            for s in output_statuses:
                card = BookCard(s["slug"], s)
                card.translate_clicked.connect(self.translate_clicked.emit)
                self.output_tab[1].addWidget(card)
        else:
            empty = QLabel("Chua co sach nao dich xong")
            empty.setStyleSheet(f"color: {TEXT_DIM}; font-size: 14px; padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.output_tab[1].addWidget(empty)
        self.output_tab[1].addStretch()

        # Update tab title with count
        self.tabs.setTabText(1, f"📖 Output ({len(output_statuses)})")


class APISettingsPage(QWidget):
    """Trang cài đặt API."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)

        header = QLabel("⚙️ API Settings")
        header.setStyleSheet(f"font-size: {FONT_SIZE_XL}px; font-weight: bold; color: {TEXT_PRIMARY};")
        layout.addWidget(header)

        # Provider selector
        provider_frame = GlassFrame()
        pf_layout = QFormLayout(provider_frame)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["gemini", "deepseek", "custom"])
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        pf_layout.addRow("Provider:", self.provider_combo)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Nhập API key...")
        pf_layout.addRow("API Key:", self.api_key_input)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("Model name")
        pf_layout.addRow("Model:", self.model_input)

        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("Base URL (cho custom provider)")
        pf_layout.addRow("Base URL:", self.base_url_input)

        # Test button
        self.test_btn = GlassButton("🔍 Test Connection")
        self.test_btn.clicked.connect(self._test_connection)
        pf_layout.addRow("", self.test_btn)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"font-size: 13px; padding: 8px;")
        pf_layout.addRow("", self.status_label)

        layout.addWidget(provider_frame)
        layout.addStretch()

        # Load current config
        self._load_config()

    def _load_config(self):
        try:
            from api.config import get_active_provider, get_provider_config
            provider = get_active_provider()
            self.provider_combo.setCurrentText(provider)
            config = get_provider_config(provider)
            if config:
                self.api_key_input.setText(config.get("api_key", ""))
                self.model_input.setText(config.get("model", ""))
                self.base_url_input.setText(config.get("base_url", ""))
        except Exception:
            pass

    def _on_provider_changed(self, provider):
        try:
            from api.config import get_provider_config
            config = get_provider_config(provider)
            if config:
                self.api_key_input.setText(config.get("api_key", ""))
                self.model_input.setText(config.get("model", ""))
                self.base_url_input.setText(config.get("base_url", ""))
                self.base_url_input.setVisible(provider == "custom")
        except Exception:
            pass

    def _test_connection(self):
        self.status_label.setText("⏳ Đang test...")
        self.status_label.setStyleSheet(f"color: {INFO}; font-size: 13px; padding: 8px;")
        QApplication.processEvents()

        provider = self.provider_combo.currentText()
        api_key = self.api_key_input.text()
        model = self.model_input.text()
        base_url = self.base_url_input.text()

        if not api_key:
            self.status_label.setText("❌ Chưa nhập API key")
            self.status_label.setStyleSheet(f"color: {ERROR}; font-size: 13px; padding: 8px;")
            return

        # Save config temporarily
        try:
            from api.config import set_provider_config, set_active_provider, test_provider_connection
            set_provider_config(provider, api_key, model, base_url)
            set_active_provider(provider)
            ok, msg = test_provider_connection(provider)
            if ok:
                self.status_label.setText(f"✅ {msg}")
                self.status_label.setStyleSheet(f"color: {SUCCESS}; font-size: 13px; padding: 8px;")
            else:
                self.status_label.setText(f"❌ {msg}")
                self.status_label.setStyleSheet(f"color: {ERROR}; font-size: 13px; padding: 8px;")
        except Exception as e:
            self.status_label.setText(f"❌ {e}")
            self.status_label.setStyleSheet(f"color: {ERROR}; font-size: 13px; padding: 8px;")

    def save(self):
        try:
            from api.config import set_provider_config, set_active_provider
            provider = self.provider_combo.currentText()
            set_provider_config(provider, self.api_key_input.text(),
                              self.model_input.text(), self.base_url_input.text())
            set_active_provider(provider)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu: {e}")
            return False


class MainWindow(QMainWindow):
    """Main window với Liquid Glass UI."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Translate Book")
        self.setMinimumSize(1000, 700)

        # Load stylesheet
        qss_path = os.path.join(os.path.dirname(__file__), "styles", "liquid.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.nav_changed.connect(self._on_nav)
        main_layout.addWidget(self.sidebar)

        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Stacked pages
        self.pages = QStackedWidget()

        self.books_page = BooksPage()
        self.books_page.translate_clicked.connect(self._on_translate)
        self.pages.addWidget(self.books_page)

        # Audio page (placeholder)
        audio_page = QWidget()
        audio_layout = QVBoxLayout(audio_page)
        audio_layout.setContentsMargins(24, 16, 24, 16)
        audio_header = QLabel("🎧 Audiobook")
        audio_header.setStyleSheet(f"font-size: {FONT_SIZE_XL}px; font-weight: bold;")
        audio_layout.addWidget(audio_header)
        audio_empty = QLabel("Chọn sách ở trang Sách → click 'Dịch' để tạo audio")
        audio_empty.setStyleSheet(f"color: {TEXT_DIM}; font-size: 14px; padding: 40px;")
        audio_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        audio_layout.addWidget(audio_empty)
        self.pages.addWidget(audio_page)

        self.api_page = APISettingsPage()
        self.pages.addWidget(self.api_page)

        content_layout.addWidget(self.pages, stretch=1)

        # Log panel
        self.log_panel = LogPanel()
        self.log_panel.setFixedHeight(180)
        content_layout.addWidget(self.log_panel)

        main_layout.addWidget(content, stretch=1)

        # Load books
        self._load_books()
        self.log_panel.log("🚀 Translate Book ready", "info")

    def _on_nav(self, idx):
        self.pages.setCurrentIndex(idx)

    def _load_books(self):
        try:
            from api.config import get_active_provider
            provider = get_active_provider()
            self.sidebar.update_api_status(provider, True)
        except Exception:
            self.sidebar.update_api_status("—", False)

        # Load book statuses
        try:
            from pathlib import Path
            import re, json
            project_root = Path(__file__).parent.parent.parent
            books_dir = project_root / "output" / "books"
            input_dir = project_root / "input"
            statuses = []

            # Sách trong output/books/ (đã/x đang dịch)
            if books_dir.exists():
                for d in sorted(books_dir.iterdir()):
                    if not d.is_dir():
                        continue
                    slug = d.name
                    vi_md = d / "final" / "vi.md"
                    epub = d / "trilingual.epub"
                    audiobook_dir = d / "audiobook"
                    mp3_count = len(list(audiobook_dir.glob("ch*.mp3"))) if audiobook_dir.exists() else 0
                    progress_count = 0
                    total_chunks = 0
                    progress_slug = project_root / "working" / "progress" / slug
                    if progress_slug.exists():
                        progress_count = len(list(progress_slug.glob("chunk_*.json")))
                    chunks_slug = project_root / "working" / "chunks" / slug
                    if chunks_slug.exists():
                        total_chunks = len(list(chunks_slug.glob("chunk-*.json")))
                    audio_chapters = []
                    audio_progress = project_root / "working" / "progress_audio" / f"{slug}.json"
                    if audio_progress.exists():
                        try:
                            ap = json.loads(audio_progress.read_text(encoding='utf-8'))
                            audio_chapters = ap.get("completed_chapters", [])
                        except Exception:
                            pass
                    total_chapters = 0
                    if vi_md.exists():
                        content = vi_md.read_text(encoding='utf-8')
                        total_chapters = len(re.findall(r'^# ', content, re.MULTILINE))
                    statuses.append({
                        "slug": slug, "source": "output",
                        "has_vi_md": vi_md.exists(), "has_epub": epub.exists(),
                        "mp3_count": mp3_count, "total_chapters": total_chapters,
                        "progress_count": progress_count, "total_chunks": total_chunks,
                        "audio_done": len(audio_chapters), "audio_total": total_chapters,
                    })

            # Sách trong input/ (chưa dịch)
            known_slugs = {s["slug"] for s in statuses}
            if input_dir.exists():
                for f in sorted(input_dir.iterdir()):
                    if f.suffix.lower() in ('.pdf', '.epub', '.docx'):
                        slug = f.stem.lower().replace(' ', '-')
                        if slug not in known_slugs:
                            statuses.append({
                                "slug": f.name, "slug_key": slug, "source": "input",
                                "has_vi_md": False, "has_epub": False,
                                "mp3_count": 0, "total_chapters": 0,
                                "progress_count": 0, "total_chunks": 0,
                                "audio_done": 0, "audio_total": 0,
                            })

            self.books_page.load_books(statuses)
            self.log_panel.log(f"📚 Da tai {len(statuses)} cuon sach", "info")
        except Exception as e:
            self.log_panel.log(f"Loi tai sach: {e}", "warning")

    def _on_translate(self, slug):
        self.log_panel.log(f"🚀 Bắt đầu dịch: {slug}", "info")
        self.log_panel.log("  → Gõ /dich trong terminal để chạy pipeline", "info")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG_DARK))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(BG_MEDIUM))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(BG_GLASS))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(PRIMARY))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
