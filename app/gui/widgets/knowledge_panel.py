"""
Knowledge Base Management & RAG Interface for Zero AI.
Enables opening the Knowledge/ folder, viewing indexed files and status,
manual full-text/semantic search with excerpts, and triggering incremental reindexing.
"""

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QScrollArea,
    QFrame,
    QMessageBox,
)
from app.knowledge.service import get_knowledge_service


class ReindexWorkerThread(QThread):
    """Background worker to index knowledge files without blocking the UI."""
    finished_report = Signal(object)

    def __init__(self, force_all: bool = False):
        super().__init__()
        self.force_all = force_all

    def run(self):
        svc = get_knowledge_service()
        report = svc.sync_and_index(force_all=self.force_all)
        self.finished_report.emit(report)


class KnowledgePanelWidget(QWidget):
    """Panel for managing Knowledge/ files, indexing status, and manual queries."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: ReindexWorkerThread | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # 1. Header with Controls
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("KNOWLEDGE REPOSITORY & RAG")
        title.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold; letter-spacing: 1.5px;")
        sub = QLabel("Local document index & contextual retrieval engine")
        sub.setStyleSheet("color: #00FF88; font-size: 11px;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.btn_open_folder = QPushButton("📂  Open Folder")
        self.btn_open_folder.setProperty("class", "btn-secondary")
        self.btn_open_folder.setCursor(Qt.PointingHandCursor)
        self.btn_open_folder.clicked.connect(self._open_folder)
        header_layout.addWidget(self.btn_open_folder)

        self.btn_reindex = QPushButton("⟳  Reindex All")
        self.btn_reindex.setProperty("class", "btn-primary")
        self.btn_reindex.setCursor(Qt.PointingHandCursor)
        self.btn_reindex.clicked.connect(self._start_reindex)
        header_layout.addWidget(self.btn_reindex)

        layout.addLayout(header_layout)

        # 2. Stats Telemetry Card
        self.stats_card = QFrame()
        self.stats_card.setProperty("class", "hud-card")
        sc_layout = QHBoxLayout(self.stats_card)
        sc_layout.setContentsMargins(16, 10, 16, 10)

        self.stat_files_lbl = QLabel("Files: 0")
        self.stat_files_lbl.setStyleSheet("color: #E2E8F0; font-size: 11px; font-weight: bold;")
        self.stat_chunks_lbl = QLabel("Chunks: 0")
        self.stat_chunks_lbl.setStyleSheet("color: #00FF88; font-size: 11px; font-weight: bold;")
        self.stat_last_sync_lbl = QLabel("Last Sync: Never")
        self.stat_last_sync_lbl.setStyleSheet("color: #8A8A8A; font-size: 11px;")

        sc_layout.addWidget(self.stat_files_lbl)
        sc_layout.addSpacing(20)
        sc_layout.addWidget(self.stat_chunks_lbl)
        sc_layout.addSpacing(20)
        sc_layout.addWidget(self.stat_last_sync_lbl)
        sc_layout.addStretch()

        layout.addWidget(self.stats_card)

        # 3. Knowledge Search Bar
        search_box = QFrame()
        search_box.setProperty("class", "hud-card")
        sb_layout = QVBoxLayout(search_box)
        sb_layout.setContentsMargins(14, 10, 14, 10)
        sb_layout.setSpacing(8)

        sb_title = QLabel("SEARCH KNOWLEDGE PASSAGES")
        sb_title.setStyleSheet("color: #8A8A8A; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        sb_layout.addWidget(sb_title)

        s_input_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter keywords or query (e.g. 'architecture', 'api key', 'billing')...")
        self.search_input.setFixedHeight(34)
        self.search_input.returnPressed.connect(self._perform_search)
        s_input_row.addWidget(self.search_input)

        btn_search = QPushButton("Search 🔍")
        btn_search.setProperty("class", "btn-secondary")
        btn_search.setFixedHeight(34)
        btn_search.setCursor(Qt.PointingHandCursor)
        btn_search.clicked.connect(self._perform_search)
        s_input_row.addWidget(btn_search)
        sb_layout.addLayout(s_input_row)

        self.search_results_area = QWidget()
        self.results_vbox = QVBoxLayout(self.search_results_area)
        self.results_vbox.setContentsMargins(0, 4, 0, 0)
        self.results_vbox.setSpacing(6)
        sb_layout.addWidget(self.search_results_area)

        layout.addWidget(search_box)

        # 4. Tracked Documents List
        docs_header_row = QHBoxLayout()
        docs_title = QLabel("INDEXED DOCUMENTS IN KNOWLEDGE/")
        docs_title.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        docs_header_row.addWidget(docs_title)
        docs_header_row.addStretch()
        layout.addLayout(docs_header_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.docs_container = QWidget()
        self.docs_layout = QVBoxLayout(self.docs_container)
        self.docs_layout.setContentsMargins(0, 0, 10, 0)
        self.docs_layout.setSpacing(8)
        self.docs_layout.addStretch()
        scroll.setWidget(self.docs_container)
        layout.addWidget(scroll)

        self.reload_data()

    def _open_folder(self):
        svc = get_knowledge_service()
        svc.open_knowledge_folder()

    def _start_reindex(self):
        self.btn_reindex.setText("⏳ Indexing...")
        self.btn_reindex.setEnabled(False)
        self._worker = ReindexWorkerThread(force_all=True)
        self._worker.finished_report.connect(self._on_reindex_complete)
        self._worker.start()

    def _on_reindex_complete(self, report):
        self.btn_reindex.setText("⟳  Reindex All")
        self.btn_reindex.setEnabled(True)
        self.reload_data()
        QMessageBox.information(
            self,
            "Reindex Complete",
            f"Knowledge sync complete!\n\n"
            f"• Scanned: {report.scanned_files}\n"
            f"• Indexed / Updated: {report.indexed_files + report.updated_files}\n"
            f"• Searchable Chunks: {report.total_chunks}\n"
            f"• Rejected (Audio/Video): {report.rejected_files}\n"
            f"• Errors: {report.error_files}",
        )

    def _perform_search(self):
        query = self.search_input.text().strip()
        # Clear previous results
        while self.results_vbox.count() > 0:
            item = self.results_vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not query:
            return

        svc = get_knowledge_service()
        results = svc.search(query, limit=3)
        if not results:
            lbl = QLabel(f"No passages found matching '{query}'.")
            lbl.setStyleSheet("color: #8A8A8A; font-style: italic; font-size: 11px;")
            self.results_vbox.addWidget(lbl)
            return

        for r in results:
            res_box = QFrame()
            res_box.setStyleSheet("background-color: #0A0F14; border: 1px solid #1E293B; border-radius: 4px; padding: 6px;")
            rb_layout = QVBoxLayout(res_box)
            rb_layout.setContentsMargins(8, 6, 8, 6)

            src_row = QHBoxLayout()
            src_lbl = QLabel(f"📄 {r.source_file} ({r.section_label})")
            src_lbl.setStyleSheet("color: #00FF88; font-weight: bold; font-size: 11px;")
            src_row.addWidget(src_lbl)
            src_row.addStretch()

            score_lbl = QLabel(f"Relevance: {r.score}")
            score_lbl.setStyleSheet("color: #6E7681; font-size: 10px;")
            src_row.addWidget(score_lbl)
            rb_layout.addLayout(src_row)

            snippet_lbl = QLabel(r.content[:240] + ("..." if len(r.content) > 240 else ""))
            snippet_lbl.setWordWrap(True)
            snippet_lbl.setStyleSheet("color: #CBD5E1; font-size: 11px;")
            rb_layout.addWidget(snippet_lbl)

            self.results_vbox.addWidget(res_box)

    def reload_data(self):
        """Refresh stats and file listing."""
        svc = get_knowledge_service()
        status = svc.get_status()
        stats = status.get("stats", {})

        total_files = stats.get("total_files", 0)
        indexed_files = stats.get("indexed_files", 0)
        total_chunks = stats.get("total_chunks", 0)
        last_sync = stats.get("last_indexed_at")
        last_sync_str = last_sync[:19].replace("T", " ") if last_sync else "Never"

        self.stat_files_lbl.setText(f"Files: {indexed_files} / {total_files}")
        self.stat_chunks_lbl.setText(f"Searchable Chunks: {total_chunks}")
        self.stat_last_sync_lbl.setText(f"Last Sync: {last_sync_str}")

        # Populate file cards
        while self.docs_layout.count() > 1:
            item = self.docs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        files = svc.list_files()
        if not files:
            empty_lbl = QLabel("No files in Knowledge/ folder yet. Click 'Open Folder' to add documents.")
            empty_lbl.setStyleSheet("color: #8A8A8A; font-style: italic; padding: 20px;")
            self.docs_layout.insertWidget(0, empty_lbl)
            return

        for f in files:
            card = QFrame()
            card.setProperty("class", "hud-card")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(14, 10, 14, 10)

            vbox = QVBoxLayout()
            name_lbl = QLabel(f["id"])
            name_lbl.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 12px;")
            vbox.addWidget(name_lbl)

            size_kb = f["file_size"] / 1024.0
            meta_str = f"Size: {size_kb:.1f} KB | Chunks: {f['chunk_count']}"
            if f.get("error_message"):
                meta_str += f" | Notice: {f['error_message']}"
            meta_lbl = QLabel(meta_str)
            meta_lbl.setStyleSheet("color: #8A8A8A; font-size: 10px;")
            vbox.addWidget(meta_lbl)
            card_layout.addLayout(vbox)
            card_layout.addStretch()

            # Status pill
            status_val = f["status"]
            status_lbl = QLabel(status_val)
            if status_val == "INDEXED":
                status_lbl.setStyleSheet(
                    "background-color: #0E2A1A; color: #00FF88; border: 1px solid #14532D; border-radius: 4px; padding: 4px 8px; font-size: 10px; font-weight: bold;"
                )
            elif status_val == "REJECTED":
                status_lbl.setStyleSheet(
                    "background-color: #2A1D0E; color: #F59E0B; border: 1px solid #78350F; border-radius: 4px; padding: 4px 8px; font-size: 10px; font-weight: bold;"
                )
            else:
                status_lbl.setStyleSheet(
                    "background-color: #2D1418; color: #FF4757; border: 1px solid #7F1D1D; border-radius: 4px; padding: 4px 8px; font-size: 10px; font-weight: bold;"
                )
            card_layout.addWidget(status_lbl)

            count = self.docs_layout.count()
            self.docs_layout.insertWidget(count - 1, card)

    def refresh_all(self):
        """Alias for reload_data to synchronize with navigation events."""
        self.reload_data()
