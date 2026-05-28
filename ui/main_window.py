import os
import logging
from PyQt6.QtCore import Qt, QThread, QSettings, QSortFilterProxyModel
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QFileDialog, QLabel, QLineEdit, QHeaderView, QMessageBox,
    QTreeView, QProgressBar, QTextEdit, QFrame, QSplitter,
    QToolButton, QCheckBox, QDialog, QSizePolicy,
    QTableWidget, QTableWidgetItem
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QTextCursor, QCursor

from render.canvas import CADPreviewCanvas
from workers.parser_worker import CADGeometryWorker
from gis.exporter import export_features_to_shapefiles
from ui.style import DARK_THEME_STYLESHEET
from cad.converter import find_bundled_converter
from ui.layer_tree_builder import LayerTreeBuilder
from geocad.version import APP_NAME, VERSION

logger = logging.getLogger("geocad.ui.main_window")

# Limite máximo de linhas no buffer circular do console de logs
MAX_LOG_LINES = 500


class ClickableProgressBar(QProgressBar):
    from PyQt6.QtCore import pyqtSignal
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Clique para exibir os logs de processamento detalhados")

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class AttributesDialog(QDialog):
    def __init__(self, selected_handles, handle_to_feature, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Atributos da Seleção ({len(selected_handles)} feições)")
        self.resize(650, 400)
        self.setStyleSheet("background-color: #ffffff; color: #1f2937;")
        layout = QVBoxLayout(self)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Handle", "Camada", "Tipo Geométrico", "Conteúdo/Texto"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        
        self.table.setRowCount(len(selected_handles))
        
        for row, handle in enumerate(selected_handles):
            feat = handle_to_feature.get(handle, {})
            self.table.setItem(row, 0, QTableWidgetItem(str(handle)))
            self.table.setItem(row, 1, QTableWidgetItem(str(feat.get("layer", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(feat.get("geom_type", ""))))
            
            text_val = ""
            if feat.get("geom_type") == "Text" and feat.get("coords") and len(feat["coords"]) > 0 and len(feat["coords"][0]) > 2:
                text_val = str(feat["coords"][0][2])
            self.table.setItem(row, 3, QTableWidgetItem(text_val))
            
        layout.addWidget(self.table)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.resize(1300, 800)
        self.setStyleSheet(DARK_THEME_STYLESHEET)

        self.settings = QSettings("GeoCad")

        # Estado Interno
        self.thread = None
        self.worker = None
        self.detected_crs = None
        self.crs_status_level = "WARNING"
        self.all_parsed_features = []

        self.setup_ui()
        self.detect_bundled_converter()

    def setup_ui(self):
        """Constrói a interface principal com QSplitter horizontal e painel recolhível."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ──────────────────────────────────────────────
        # QSplitter Horizontal: Sidebar ↔ Canvas
        # ──────────────────────────────────────────────
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Painel Esquerdo (Controles e Camadas)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        sidebar.setMinimumWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 15, 15, 15)
        sidebar_layout.setSpacing(12)

        # Título do Aplicativo
        title_lbl = QLabel("GeoCad")
        title_lbl.setObjectName("title_label")
        desc_lbl = QLabel("Conversão DWG → Shapefile GIS")
        desc_lbl.setStyleSheet("color: #4b5563; font-size: 11px; margin-bottom: 5px;")
        sidebar_layout.addWidget(title_lbl)
        sidebar_layout.addWidget(desc_lbl)

        # Botões de Controle
        self.btn_load = QPushButton("Carregar DWG / DXF")
        self.btn_load.setFixedHeight(45)
        self.btn_load.clicked.connect(self.open_file)
        sidebar_layout.addWidget(self.btn_load)

        # Status do CRS
        self.lbl_crs_status = QLabel("Aguardando carregamento de desenho...")
        self.lbl_crs_status.setObjectName("crs_status")
        self.lbl_crs_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_crs_status.setWordWrap(True)
        sidebar_layout.addWidget(self.lbl_crs_status)

        # Barra de Pesquisa de Camadas
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Filtrar camadas por nome...")
        self.txt_search.textChanged.connect(self.filter_layers)
        sidebar_layout.addWidget(self.txt_search)

        # Botões Selecionar/Desmarcar Todas
        self.btn_select_all = QPushButton("☑️ Selecionar Todas")
        self.btn_unselect_all = QPushButton("⬜ Desmarcar Todas")
        self.btn_select_all.setStyleSheet("font-size: 11px; padding: 5px;")
        self.btn_unselect_all.setStyleSheet("font-size: 11px; padding: 5px;")
        self.btn_select_all.clicked.connect(self.select_all_layers)
        self.btn_unselect_all.clicked.connect(self.unselect_all_layers)

        selection_btns_layout = QHBoxLayout()
        selection_btns_layout.addWidget(self.btn_select_all)
        selection_btns_layout.addWidget(self.btn_unselect_all)
        sidebar_layout.addLayout(selection_btns_layout)

        # Lista com Checkboxes (TreeView Hierárquica)
        self.tree_view = QTreeView()
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["Camada", "Tipo", "Feições"])
        self.tree_model.itemChanged.connect(self.on_layer_checkbox_changed)
        self.tree_view.expanded.connect(self.on_tree_node_expanded)
        self.tree_view.clicked.connect(self.on_tree_node_clicked)

        # Habilita menu de contexto de clique direito nas camadas
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_layer_context_menu)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.tree_model)
        self.proxy_model.setFilterKeyColumn(0)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setRecursiveFilteringEnabled(True)

        self.tree_view.setModel(self.proxy_model)
        self.tree_view.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tree_view.header().setStretchLastSection(True)
        self.tree_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sidebar_layout.addWidget(self.tree_view)

        # ──────────────────────────────────────────────
        # Barra de Progresso Clicável
        # ──────────────────────────────────────────────
        self.progress_bar = ClickableProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.clicked.connect(self._show_status_dialog)
        sidebar_layout.addWidget(self.progress_bar)

        # Configuração da Janela de Status Independente (Logs)
        self.status_dialog = QDialog(self)
        self.status_dialog.setWindowTitle("Logs e Detalhes do Processamento")
        self.status_dialog.resize(600, 350)
        status_layout = QVBoxLayout(self.status_dialog)
        status_layout.setContentsMargins(10, 10, 10, 10)
        
        self.console_logs = QTextEdit()
        self.console_logs.setReadOnly(True)
        self.console_logs.setPlaceholderText("Mensagens e registros de processamento...")
        # Usa a mesma fonte monospace do tema escuro
        self.console_logs.setStyleSheet("background-color: #1e293b; color: #f8fafc; font-family: Consolas, monospace; font-size: 11px;")
        status_layout.addWidget(self.console_logs)

        # Botão de Exportação de Shapefiles
        self.btn_export = QPushButton("Exportar Shapefiles")
        self.btn_export.setObjectName("export_btn")
        self.btn_export.setFixedHeight(50)
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_to_shapefiles)
        sidebar_layout.addWidget(self.btn_export)

        # Checkbox para exportar apenas feições selecionadas
        self.chk_export_selected = QCheckBox("Exportar apenas feições selecionadas")
        self.chk_export_selected.setChecked(False)
        self.chk_export_selected.setEnabled(False)
        self.chk_export_selected.setStyleSheet("font-size: 11px; color: #475569; padding: 2px 0;")
        sidebar_layout.addWidget(self.chk_export_selected)

        # Créditos do Criador (Removido o addStretch() para permitir expansão irrestrita das camadas)
        self.lbl_credits = QLabel("Criado por Matheus Freitas Rangel\nContato: matheus-freitas-rangel@hotmail.com")
        self.lbl_credits.setObjectName("credits_label")
        self.lbl_credits.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(self.lbl_credits)

        self.splitter.addWidget(sidebar)

        # ──────────────────────────────────────────────
        # Painel Direito (Preview Vetorial + Toolbar)
        # ──────────────────────────────────────────────
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.preview_canvas = CADPreviewCanvas()
        self.preview_canvas.setMinimumWidth(400)
        self.preview_canvas.selection_changed.connect(self._on_selection_changed)
        right_layout.addWidget(self.preview_canvas)

        # Barra de Ações Rápidas (Zoom + Modo de Interação)
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(10, 8, 10, 8)
        toolbar.setSpacing(8)

        # Botão de Reajustar Zoom
        btn_fit = QPushButton("🔄 Reajustar ZOOM")
        btn_fit.setObjectName("action_btn")
        btn_fit.clicked.connect(self.preview_canvas.fit_scene_to_view)
        toolbar.addWidget(btn_fit)

        toolbar.addStretch()

        # Seletor de Modo: Navegação ↔ Seleção
        self.btn_mode_nav = QPushButton("✋ Navegação")
        self.btn_mode_nav.setObjectName("mode_btn_active")
        self.btn_mode_nav.clicked.connect(lambda: self._set_interaction_mode("nav"))

        self.btn_mode_sel = QPushButton("🖱️ Seleção")
        self.btn_mode_sel.setObjectName("mode_btn_inactive")
        self.btn_mode_sel.clicked.connect(lambda: self._set_interaction_mode("sel"))

        # Botão Desfazer Seleção
        self.btn_clear_sel = QPushButton("🚫 Desfazer Seleção")
        self.btn_clear_sel.setObjectName("action_btn")
        self.btn_clear_sel.clicked.connect(self.preview_canvas.clear_selection)

        # Botão Atributos da Seleção
        self.btn_show_attributes = QPushButton("📋 Atributos da Seleção")
        self.btn_show_attributes.setObjectName("action_btn")
        self.btn_show_attributes.clicked.connect(self.show_selection_attributes)
        self.btn_show_attributes.setEnabled(False)

        # Label de contagem de seleção
        self.lbl_selection_count = QLabel("")
        self.lbl_selection_count.setStyleSheet("color: #64748b; font-size: 12px; font-weight: bold; padding: 0 6px;")

        toolbar.addWidget(self.btn_mode_nav)
        toolbar.addWidget(self.btn_mode_sel)
        toolbar.addWidget(self.btn_clear_sel)
        toolbar.addWidget(self.btn_show_attributes)
        toolbar.addWidget(self.lbl_selection_count)

        right_layout.addLayout(toolbar)

        self.splitter.addWidget(right_container)

        # ──────────────────────────────────────────────
        # Painel Lateral Direito (Detalhes da Feição)
        # ──────────────────────────────────────────────
        self.details_sidebar = QFrame()
        self.details_sidebar.setObjectName("details_sidebar")
        self.details_sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        self.details_sidebar.setMinimumWidth(250)
        self.details_sidebar.setMaximumWidth(400)
        self.details_sidebar.hide()  # Oculto por padrão

        details_layout = QVBoxLayout(self.details_sidebar)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setSpacing(10)

        # Cabeçalho do Painel
        header_layout = QHBoxLayout()
        details_title = QLabel("Informações da Feição")
        details_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #0f766e;")
        btn_close_details = QPushButton("×")
        btn_close_details.setFixedSize(22, 22)
        btn_close_details.setStyleSheet(
            "padding: 0; font-size: 14px; font-weight: bold; border-radius: 11px; "
            "border: 1px solid #cbd5e1; background-color: #f1f5f9; color: #64748b;"
        )
        btn_close_details.clicked.connect(self.details_sidebar.hide)

        header_layout.addWidget(details_title)
        header_layout.addWidget(btn_close_details)
        details_layout.addLayout(header_layout)

        # Painel de Resumo Superior
        self.details_summary_lbl = QLabel()
        self.details_summary_lbl.setWordWrap(True)
        self.details_summary_lbl.setStyleSheet(
            "font-size: 11px; color: #475569; padding: 8px; background-color: #f8fafc; "
            "border-radius: 4px; border: 1px solid #e2e8f0; line-height: 1.4;"
        )
        details_layout.addWidget(self.details_summary_lbl)

        # Árvore de Atributos da Seleção (QTreeWidget)
        from PyQt6.QtWidgets import QTreeWidget
        self.details_tree = QTreeWidget()
        self.details_tree.setHeaderHidden(True)
        self.details_tree.setAlternatingRowColors(True)
        self.details_tree.setStyleSheet(
            "QTreeWidget { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 4px; color: #1f2937; }"
            "QTreeWidget::item { padding: 4px; }"
        )
        details_layout.addWidget(self.details_tree)

        self.splitter.addWidget(self.details_sidebar)

        # Proporções padrão do splitter: sidebar 25%, canvas 50%, detalhes 25%
        self.splitter.setStretchFactor(0, 25)
        self.splitter.setStretchFactor(1, 50)
        self.splitter.setStretchFactor(2, 25)

        # Restaura o estado do splitter salvo anteriormente
        saved_state = self.settings.value("splitter_state")
        if saved_state:
            self.splitter.restoreState(saved_state)

        main_layout.addWidget(self.splitter)

    # ──────────────────────────────────────────────
    # Inicialização e Detecção
    # ──────────────────────────────────────────────

    def detect_bundled_converter(self):
        """Verifica silenciosamente a presença do LibreDWG na inicialização."""
        path = find_bundled_converter()
        if path:
            self.log_message(f"Sistema conversor LibreDWG ativo e integrado: {path}")
        else:
            self.log_message("AVISO: Conversor executável LibreDWG não localizado na pasta 'bin'.")

    def filter_layers(self, text):
        """Filtra a árvore de camadas pelo texto digitado."""
        self.proxy_model.setFilterFixedString(text)

    # ──────────────────────────────────────────────
    # Sistema de Logs com Buffer Circular
    # ──────────────────────────────────────────────

    def log_message(self, message):
        """
        Adiciona uma mensagem ao console de logs com buffer circular.
        Remove as linhas mais antigas quando excede MAX_LOG_LINES para evitar
        crescimento infinito de memória no QTextEdit.
        """
        self.console_logs.append(message)
        logger.info(message)

        # Buffer circular: remove linhas excedentes do topo
        doc = self.console_logs.document()
        if doc.blockCount() > MAX_LOG_LINES:
            excess = doc.blockCount() - MAX_LOG_LINES
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(excess):
                cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor)
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            cursor.deleteChar()  # Remove o newline residual

        # A janela de status agora permanece oculta até o usuário clicar na barra de carregamento

    # ──────────────────────────────────────────────
    # Painel de Status Flutuante
    # ──────────────────────────────────────────────

    def _show_status_dialog(self):
        """Abre a janela de status independente."""
        self.status_dialog.show()
        self.status_dialog.raise_()
        self.status_dialog.activateWindow()

    # ──────────────────────────────────────────────
    # Modo de Interação (Navegação ↔ Seleção)
    # ──────────────────────────────────────────────

    def _set_interaction_mode(self, mode):
        """Alterna entre modo de navegação (pan) e modo de seleção espacial."""
        if mode == "nav":
            self.preview_canvas.set_selection_mode(False)
            self.btn_mode_nav.setObjectName("mode_btn_active")
            self.btn_mode_sel.setObjectName("mode_btn_inactive")
        else:
            self.preview_canvas.set_selection_mode(True)
            self.btn_mode_nav.setObjectName("mode_btn_inactive")
            self.btn_mode_sel.setObjectName("mode_btn_active")

        # Força a recarga do estilo CSS com base no objectName atualizado
        self.btn_mode_nav.style().unpolish(self.btn_mode_nav)
        self.btn_mode_nav.style().polish(self.btn_mode_nav)
        self.btn_mode_sel.style().unpolish(self.btn_mode_sel)
        self.btn_mode_sel.style().polish(self.btn_mode_sel)

    def _on_selection_changed(self, selected_handles):
        """Callback quando a seleção de feições muda no canvas."""
        count = len(selected_handles)
        if count > 0:
            self.lbl_selection_count.setText(f"{count} feições selecionadas")
            self.chk_export_selected.setEnabled(True)
            self.btn_show_attributes.setEnabled(True)
            self.update_details_sidebar(selected_handles)
            self.details_sidebar.show()
        else:
            self.lbl_selection_count.setText("")
            self.chk_export_selected.setEnabled(False)
            self.chk_export_selected.setChecked(False)
            self.btn_show_attributes.setEnabled(False)
            self.details_sidebar.hide()

    def update_details_sidebar(self, selected_handles):
        """Atualiza o painel lateral direito com a visualização hierárquica e resumo das feições selecionadas."""
        self.details_tree.clear()
        if not selected_handles:
            self.details_summary_lbl.setText("Nenhuma feição selecionada")
            return

        # Dicionário de tradução dos tipos geométricos
        geom_name_map = {
            "Point": "Pontos",
            "LineString": "Linhas",
            "Polygon": "Polígonos",
            "Text": "Textos"
        }

        # Agrupa os handles selecionados por tipo geométrico
        grouped_handles = {
            "Point": [],
            "LineString": [],
            "Polygon": [],
            "Text": []
        }

        valid_selected = []
        for h in selected_handles:
            reg = self.preview_canvas.feature_registry.get(h)
            if reg:
                geom_type = reg.get("entity_type") or reg.get("attributes", {}).get("geom_type")
                if geom_type in grouped_handles:
                    grouped_handles[geom_type].append(h)
                    valid_selected.append(h)

        # Atualiza a contagem consolidada no painel de resumo superior
        total_sel = len(valid_selected)
        pts_count = len(grouped_handles["Point"])
        lines_count = len(grouped_handles["LineString"])
        polys_count = len(grouped_handles["Polygon"])
        texts_count = len(grouped_handles["Text"])

        summary_text = (
            f"<b>Feições Selecionadas: {total_sel}</b><br>"
            f"• Pontos: {pts_count}<br>"
            f"• Linhas: {lines_count}<br>"
            f"• Polígonos: {polys_count}"
        )
        if texts_count > 0:
            summary_text += f"<br>• Textos: {texts_count}"
        self.details_summary_lbl.setText(summary_text)

        from PyQt6.QtWidgets import QTreeWidgetItem

        # Constrói os nós de topo (tipo geométrico) e os filhos (feições e atributos)
        for geom_key, geom_lbl in geom_name_map.items():
            handles = grouped_handles[geom_key]
            if not handles:
                continue

            # Ordena os handles de forma crescente
            handles.sort()

            # Cria o nó da categoria geométrica (ex: "LINHAS (5)")
            parent_node = QTreeWidgetItem(self.details_tree)
            parent_node.setText(0, f"{geom_lbl.upper()} ({len(handles)})")
            
            # Deixa a categoria expandida por padrão para o usuário ver
            parent_node.setExpanded(True)

            feat_lbl_map = {
                "Point": "Ponto",
                "LineString": "Linha",
                "Polygon": "Polígono",
                "Text": "Texto"
            }
            lbl_prefix = feat_lbl_map.get(geom_key, "Feição")

            for h in handles:
                reg = self.preview_canvas.feature_registry.get(h)
                attrs = reg.get("attributes", {})
                
                # Cria o nó da feição individual (ex: "Linha #145")
                feat_node = QTreeWidgetItem(parent_node)
                feat_node.setText(0, f"{lbl_prefix} #{h}")

                # Calcula dinamicamente as métricas espaciais (comprimento, área) da geometria shapely
                geom = reg.get("geometry")
                length_val = "N/A"
                area_val = "N/A"
                if geom and not geom.is_empty:
                    if geom_key == "LineString":
                        length_val = f"{geom.length:.4f} m"
                    elif geom_key == "Polygon":
                        area_val = f"{geom.area:.4f} m²"
                        length_val = f"{geom.length:.4f} m"

                espessura = attrs.get("lineweight", -1)
                if isinstance(espessura, int):
                    if espessura == -1:
                        espessura_str = "PorCamada"
                    elif espessura == -2:
                        espessura_str = "PorBloco"
                    elif espessura == -3:
                        espessura_str = "Padrão"
                    else:
                        espessura_str = f"{espessura/100:.2f} mm"
                else:
                    espessura_str = str(espessura)

                # Cria os nós de atributos recolhidos sob a feição
                QTreeWidgetItem(feat_node).setText(0, f"Handle: {h}")
                QTreeWidgetItem(feat_node).setText(0, f"Layer: {attrs.get('layer', '0')}")
                
                if geom_key == "LineString":
                    QTreeWidgetItem(feat_node).setText(0, f"Comprimento: {length_val}")
                elif geom_key == "Polygon":
                    QTreeWidgetItem(feat_node).setText(0, f"Área: {area_val}")
                    QTreeWidgetItem(feat_node).setText(0, f"Perímetro: {length_val}")

                QTreeWidgetItem(feat_node).setText(0, f"Cor CAD: {attrs.get('color', '#ffffff')}")
                QTreeWidgetItem(feat_node).setText(0, f"Tipo Linha: {attrs.get('linetype', 'BYLAYER')}")
                QTreeWidgetItem(feat_node).setText(0, f"Espessura: {espessura_str}")

                texto_val = attrs.get("texto", "")
                if geom_key == "Text" and texto_val:
                    QTreeWidgetItem(feat_node).setText(0, f"Texto CAD: {texto_val}")

    def show_selection_attributes(self):
        """Abre a janela com os atributos das feições atualmente selecionadas."""
        if not self.preview_canvas.state.selected_handles:
            return
            
        dialog = AttributesDialog(
            list(self.preview_canvas.state.selected_handles),
            self.preview_canvas._handle_to_feature,
            self
        )
        dialog.exec()

    # ──────────────────────────────────────────────
    # Árvore de Camadas Hierárquica
    # ──────────────────────────────────────────────

    def add_layers_batch(self, layers_data):
        """Constrói a árvore visual das camadas em lote."""
        # Registra tudo como visível por padrão no RenderState do canvas
        for layer_name, geom_type, count in layers_data:
            self.preview_canvas.state.set_layer_geom_visible(layer_name, geom_type, True)
        LayerTreeBuilder.build_tree(self.tree_model, layers_data)

    # ──────────────────────────────────────────────
    # Carregamento de Arquivos CAD
    # ──────────────────────────────────────────────

    def open_file(self, checked=False, force_dxf_filter=False):
        """Abre e processa um arquivo DWG ou DXF."""
        last_dir = self.settings.value("last_dir", "")

        file_filter = "Arquivos CAD (*.dwg *.dxf);;AutoCAD DWG (*.dwg);;AutoCAD DXF (*.dxf)"
        title = "Selecionar Arquivo DWG ou DXF"
        if force_dxf_filter:
            file_filter = "AutoCAD DXF (*.dxf)"
            title = "Selecionar Arquivo DXF Manualmente"

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            title,
            last_dir,
            file_filter
        )

        if not file_path:
            return

        self.settings.setValue("last_dir", os.path.dirname(file_path))

        # Verifica se o arquivo é DWG e se o conversor silencioso está presente
        _, ext = os.path.splitext(file_path.lower())
        if ext == ".dwg":
            converter_path = find_bundled_converter()
            if not converter_path:
                QMessageBox.critical(
                    self,
                    "Conversor Ausente",
                    "Falha ao carregar DWG: O executável do conversor LibreDWG (dwg2dxf.exe) não foi encontrado na pasta 'bin' do programa."
                )
                return

        # Reseta os controles visuais
        self.tree_model.removeRows(0, self.tree_model.rowCount())
        self.details_sidebar.hide()
        self.preview_canvas.clear_canvas()
        self.console_logs.clear()
        self.progress_bar.setValue(0)
        self.btn_export.setEnabled(False)
        self.chk_export_selected.setEnabled(False)
        self.chk_export_selected.setChecked(False)
        self.all_parsed_features = []
        self.detected_crs = None
        self.crs_status_level = "WARNING"
        self.lbl_selection_count.setText("")

        self.lbl_crs_status.setText("Processando...")
        self.lbl_crs_status.setStyleSheet("background-color: #f1f5f9; color: #0f766e; padding: 10px; font-weight: bold; border-radius: 6px; border: 1px solid #0f766e;")

        # Desabilita o botão de carregar durante a execução do parser worker
        self.btn_load.setEnabled(False)

        # Cria a thread de segundo plano
        self.thread = QThread()
        self.worker = CADGeometryWorker(file_path, find_bundled_converter())
        self.worker.moveToThread(self.thread)

        # Conexões de sinais
        self.thread.started.connect(self.worker.run)

        self.worker.progress_changed.connect(self.progress_bar.setValue)
        self.worker.status_msg.connect(self.log_message)
        self.worker.grid_initialized.connect(self.preview_canvas.initialize_grid)
        self.worker.crs_detected.connect(self.update_crs_ui)
        self.worker.layers_found.connect(self.add_layers_batch)

        # Sinais separados para geometrias e labels (desacoplamento)
        self.worker.batch_ready.connect(self.preview_canvas.process_incoming_batch)
        self.worker.labels_ready.connect(self.preview_canvas.process_incoming_labels)

        self.worker.error_occurred.connect(self.show_error_dialog)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.on_thread_completed)

        self.thread.start()

    def show_error_dialog(self, error_msg):
        """Exibe diálogo de erro com opção de fallback para DXF manual."""
        self.lbl_crs_status.setText("Erro")
        self.lbl_crs_status.setStyleSheet("background-color: #fee2e2; color: #991b1b; padding: 10px; font-weight: bold; border-radius: 6px; border: 1px solid #fca5a5;")

        logger.warning(f"Erro reportado no processamento: {error_msg}")

        # Diálogo amigável de fallback
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Falha na Leitura Automática")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setText(
            "Não foi possível interpretar este arquivo DWG automaticamente.\n\n"
            "O desenho pode conter estruturas incompatíveis ou corrompidas.\n\n"
            "Deseja tentar abrir uma versão DXF manualmente? - Recomenda-se utilizar conversores online."
        )

        yes_btn = msg_box.addButton("Sim", QMessageBox.ButtonRole.YesRole)
        cancel_btn = msg_box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        msg_box.setDefaultButton(yes_btn)
        msg_box.exec()

        if msg_box.clickedButton() == yes_btn:
            self.open_file(force_dxf_filter=True)

    def on_thread_completed(self):
        """Callback executado ao término do processamento da thread."""
        self.btn_load.setEnabled(True)

        if self.worker:
            self.all_parsed_features = self.worker.parsed_features

        if self.all_parsed_features:
            self.btn_export.setEnabled(True)

            # fitInView executado APENAS aqui — ao final do carregamento completo
            self.preview_canvas.fit_scene_to_view()

            # Constrói o índice espacial para seleção interativa (uma única vez)
            self.preview_canvas.build_spatial_index(self.all_parsed_features)

            self.log_message(f"Processamento concluído. {len(self.all_parsed_features)} geometrias carregadas.")

            # Explora a árvore e expande todos os nós do primeiro nível
            for r in range(self.tree_model.rowCount()):
                root_item = self.tree_model.item(r, 0)
                if root_item:
                    proxy_index = self.proxy_model.mapFromSource(root_item.index())
                    self.tree_view.expand(proxy_index)
        else:
            self.log_message("Aviso: Nenhuma geometria extraída do arquivo.")

        self.worker = None
        self.thread = None

    # ──────────────────────────────────────────────
    # Camadas: Adição, Seleção, Visibilidade
    # ──────────────────────────────────────────────

    def on_layer_checkbox_changed(self, item):
        """Sincroniza visibilidade das camadas e grupos ao alterar checkboxes de forma recursiva."""
        if item.column() != 0:
            return

        self.tree_model.itemChanged.disconnect(self.on_layer_checkbox_changed)
        try:
            # Propaga o estado para baixo recursivamente
            def propagate_down(node, state):
                if node.hasChildren():
                    for r in range(node.rowCount()):
                        child = node.child(r, 0)
                        if child:
                            child.setCheckState(state)
                            propagate_down(child, state)
                
                # Altera o estado do próprio nó se for folha (camada CAD real)
                data = node.data(Qt.ItemDataRole.UserRole)
                if data and isinstance(data, tuple) and len(data) == 2:
                    layer_name, geom_type = data
                    self.preview_canvas.toggle_layer_visibility(layer_name, geom_type, state == Qt.CheckState.Checked)

            # Sincroniza os estados para cima (nós pais)
            def propagate_up(node):
                parent = node.parent()
                if not parent:
                    return
                checked_count = 0
                unchecked_count = 0
                child_count = parent.rowCount()
                for r in range(child_count):
                    child = parent.child(r, 0)
                    if child:
                        state = child.checkState()
                        if state == Qt.CheckState.Checked:
                            checked_count += 1
                        elif state == Qt.CheckState.Unchecked:
                            unchecked_count += 1

                if checked_count == child_count:
                    parent.setCheckState(Qt.CheckState.Checked)
                elif unchecked_count == child_count:
                    parent.setCheckState(Qt.CheckState.Unchecked)
                else:
                    parent.setCheckState(Qt.CheckState.PartiallyChecked)
                propagate_up(parent)

            state = item.checkState()
            propagate_down(item, state)
            propagate_up(item)
        finally:
            self.tree_model.itemChanged.connect(self.on_layer_checkbox_changed)

    def select_all_layers(self):
        """Marca todas as camadas na árvore como selecionadas."""
        self.set_all_layers_check_state(Qt.CheckState.Checked)

    def unselect_all_layers(self):
        """Desmarca todas as camadas na árvore."""
        self.set_all_layers_check_state(Qt.CheckState.Unchecked)

    def set_all_layers_check_state(self, state):
        """Define o estado de checkstate para todas as camadas de forma recursiva."""
        self.tree_model.itemChanged.disconnect(self.on_layer_checkbox_changed)
        try:
            def apply_state(item):
                item.setCheckState(state)
                if item.hasChildren():
                    for r in range(item.rowCount()):
                        child = item.child(r, 0)
                        if child:
                            apply_state(child)
                
                data = item.data(Qt.ItemDataRole.UserRole)
                if data and isinstance(data, tuple) and len(data) == 2:
                    layer_name, geom_type = data
                    self.preview_canvas.toggle_layer_visibility(layer_name, geom_type, state == Qt.CheckState.Checked)

            for r in range(self.tree_model.rowCount()):
                root_item = self.tree_model.item(r, 0)
                if root_item:
                    apply_state(root_item)
        finally:
            self.tree_model.itemChanged.connect(self.on_layer_checkbox_changed)

    # ──────────────────────────────────────────────
    # Menu Contextual Profissional por Camada
    # ──────────────────────────────────────────────

    def show_layer_context_menu(self, position):
        """Exibe o menu de contexto simplificado e profissional na camada."""
        index = self.tree_view.indexAt(position)
        if not index.isValid():
            return

        source_index = self.proxy_model.mapToSource(index)
        item = self.tree_model.itemFromIndex(source_index)
        if not item:
            return

        # Verifica se o item possui UserRole com tupla (layer_name, geom_type)
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data or not isinstance(data, tuple) or len(data) != 2:
            return

        layer_name, geom_type = data

        from PyQt6.QtGui import QAction
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)

        # 🔍 Zoom para layer
        zoom_action = QAction("🔍 Zoom para layer", self)
        zoom_action.triggered.connect(lambda: self.zoom_to_layer(layer_name))
        menu.addAction(zoom_action)

        menu.addSeparator()

        # 👁️ Mostrar layer (marca checkbox)
        show_action = QAction("👁️ Mostrar layer", self)
        show_action.triggered.connect(lambda: item.setCheckState(Qt.CheckState.Checked))
        menu.addAction(show_action)

        # 🚫 Ocultar layer (desmarca checkbox)
        hide_action = QAction("🚫 Ocultar layer", self)
        hide_action.triggered.connect(lambda: item.setCheckState(Qt.CheckState.Unchecked))
        menu.addAction(hide_action)

        menu.addSeparator()

        # 🏷️ Ligar labels
        label_on_action = QAction("🏷️ Ligar labels", self)
        label_on_action.triggered.connect(lambda: self.preview_canvas.toggle_layer_labels(layer_name, True))
        menu.addAction(label_on_action)

        # 🚫 Desligar labels
        label_off_action = QAction("🚫 Desligar labels", self)
        label_off_action.triggered.connect(lambda: self.preview_canvas.toggle_layer_labels(layer_name, False))
        menu.addAction(label_off_action)

        menu.exec(self.tree_view.viewport().mapToGlobal(position))

    def zoom_to_group(self, group_item):
        """Ajusta o zoom para cobrir todas as camadas filhas de um grupo."""
        leaf_layers = []
        def collect_leaves(node):
            if node.hasChildren():
                for r in range(node.rowCount()):
                    child = node.child(r, 0)
                    if child:
                        collect_leaves(child)
            else:
                layer_name = node.data(Qt.ItemDataRole.UserRole)
                if layer_name:
                    leaf_layers.append(layer_name)
        collect_leaves(group_item)

        bbox = QRectF()
        for layer_name in leaf_layers:
            if layer_name in self.preview_canvas.layers_items:
                geom_items = self.preview_canvas.layers_items[layer_name]["geometry"].values()
                for geom_item in geom_items:
                    if bbox.isEmpty():
                        bbox = geom_item.boundingRect()
                    else:
                        bbox = bbox.united(geom_item.boundingRect())

        if not bbox.isEmpty():
            if bbox.width() < 1.0 or bbox.height() < 1.0:
                bbox = bbox.adjusted(-5.0, -5.0, 5.0, 5.0)
            self.preview_canvas.fitInView(bbox, Qt.AspectRatioMode.KeepAspectRatio)

    def zoom_to_layer(self, layer_name):
        """Direciona o zoom do canvas para os limites de uma camada específica."""
        self.preview_canvas.zoom_to_layer(layer_name)

    # ──────────────────────────────────────────────
    # Status do CRS
    # ──────────────────────────────────────────────

    def update_crs_ui(self, status, message):
        """Atualiza a caixa de status do sistema de referência espacial."""
        self.crs_status_level = status

        if status == "SUCCESS":
            self.lbl_crs_status.setStyleSheet("background-color: #dcfce7; color: #166534; padding: 10px; font-weight: bold; border-radius: 6px; border: 1px solid #86efac;")
            self.lbl_crs_status.setText(f"🟢 {message}")

            # Mapeia código EPSG do CRS detectado
            if "31982" in message:
                self.detected_crs = "EPSG:31982"
            elif "31981" in message:
                self.detected_crs = "EPSG:31981"
            elif "31983" in message:
                self.detected_crs = "EPSG:31983"
            elif "4674" in message:
                self.detected_crs = "EPSG:4674"
            elif "4326" in message:
                self.detected_crs = "EPSG:4326"
            else:
                self.detected_crs = None
        else:
            # Coordenadas locais, inconsistentes ou desconhecidas
            self.lbl_crs_status.setStyleSheet("background-color: #fef3c7; color: #92400e; padding: 10px; font-weight: bold; border-radius: 6px; border: 1px solid #fde047;")
            self.lbl_crs_status.setText(f"⚠️ {message}")
            self.detected_crs = None

    # ──────────────────────────────────────────────
    # Exportação de Shapefiles
    # ──────────────────────────────────────────────

    def export_to_shapefiles(self):
        """Gatilho de gravação dos arquivos Shapefiles GIS."""
        if not self.all_parsed_features:
            QMessageBox.warning(self, "Sem Dados", "Não existem feições válidas em memória para exportar.")
            return

        # Verifica se deve exportar apenas feições selecionadas
        export_only_selected = self.chk_export_selected.isChecked()
        selected_handles = self.preview_canvas.state.selected_handles if export_only_selected else None

        if export_only_selected:
            features_to_export = [f for f in self.all_parsed_features if f.get("handle") in selected_handles]
        else:
            # Filtra recursivamente para coletar as camadas marcadas (checadas) na árvore
            selected_layer_geoms = set()
            def collect_checked_leaves(node):
                if node.hasChildren():
                    for r in range(node.rowCount()):
                        child = node.child(r, 0)
                        if child:
                            collect_checked_leaves(child)
                
                # Se for folha ou nó camada que possui o UserRole
                data = node.data(Qt.ItemDataRole.UserRole)
                if data and isinstance(data, tuple) and len(data) == 2:
                    if node.checkState() == Qt.CheckState.Checked:
                        selected_layer_geoms.add(data)

            for r in range(self.tree_model.rowCount()):
                root_item = self.tree_model.item(r, 0)
                if root_item:
                    collect_checked_leaves(root_item)

            features_to_export = [f for f in self.all_parsed_features if (f.get("layer"), f.get("geom_type")) in selected_layer_geoms]

        if not features_to_export:
            if export_only_selected:
                QMessageBox.warning(self, "Sem Feições Selecionadas",
                    "Nenhuma feição selecionada pertence às camadas marcadas para exportação.")
            else:
                QMessageBox.warning(self, "Sem Camadas Selecionadas",
                    "Nenhuma das camadas marcadas com checkbox possui feições para exportar.")
            return

        # 1. Validação Heurística do CRS de Georreferenciamento
        if self.crs_status_level == "WARNING" or not self.detected_crs:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Confirmação de Georreferenciamento")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setText("Este arquivo parece não possuir coordenadas geográficas válidas.\n\nDeseja exportar mesmo assim?")

            yes_btn = msg_box.addButton("Sim", QMessageBox.ButtonRole.YesRole)
            cancel_btn = msg_box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
            msg_box.setDefaultButton(cancel_btn)
            msg_box.exec()

            if msg_box.clickedButton() == cancel_btn:
                self.log_message("Exportação de Shapefiles cancelada pelo usuário devido a CRS inválido.")
                return

        # 2. Solicita a pasta de destino para a gravação
        last_dir = self.settings.value("last_dir", "")
        dest_directory = QFileDialog.getExistingDirectory(
            self,
            "Selecionar Pasta de Destino para os Shapefiles",
            last_dir
        )

        if not dest_directory:
            return

        self.settings.setValue("last_dir", dest_directory)
        self.log_message("Iniciando exportação de Shapefiles...")

        # CRS padrão ou nulo se for um desenho sem georreferenciamento
        crs_to_use = self.detected_crs

        try:
            success = export_features_to_shapefiles(features_to_export, dest_directory, crs_to_use)
            if success:
                target_path = os.path.join(dest_directory, "DWG_Shp")
                count_msg = f"{len(features_to_export)} feições"
                if export_only_selected:
                    count_msg += " (apenas selecionadas)"
                self.log_message(f"Shapefiles gravados na pasta: {target_path} — {count_msg}")
                QMessageBox.information(
                    self,
                    "Exportação Concluída",
                    f"ESRI Shapefiles gerados com sucesso!\n\nSalvo em: {target_path}\nProjeção: {crs_to_use or 'Coordenadas Locais'}\n{count_msg}"
                )
            else:
                QMessageBox.warning(self, "Gravação Vazia", "Nenhuma camada pôde ser gerada.")
        except Exception as e:
            logger.error(f"Erro ao exportar Shapefile: {e}", exc_info=True)
            QMessageBox.critical(self, "Falha de Exportação", f"Ocorreu um erro ao gerar os Shapefiles:\n{str(e)}")

    # ──────────────────────────────────────────────
    # Encerramento Seguro
    # ──────────────────────────────────────────────

    def closeEvent(self, event):
        """Finalização segura interrompendo workers e threads ativas. Salva estado do splitter."""
        # Persiste o estado do splitter para restauração futura
        self.settings.setValue("splitter_state", self.splitter.saveState())

        if self.worker:
            self.worker.cancel()
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        event.accept()

    def on_tree_node_expanded(self, index):
        """Carrega as feições individuais sob demanda quando a camada é expandida (Lazy Loading)."""
        source_index = self.proxy_model.mapToSource(index)
        item = self.tree_model.itemFromIndex(source_index)
        if not item:
            return

        data = item.data(Qt.ItemDataRole.UserRole)
        if not data or not isinstance(data, tuple) or len(data) != 2:
            return

        layer_name, geom_type = data

        # Verifica se o nó possui o filho dummy "Carregando..." e o substitui pelas feições reais
        if item.rowCount() == 1 and item.child(0, 0).text() == "Carregando...":
            item.removeRow(0)

            feats = [f for f in self.all_parsed_features if f.get("layer") == layer_name and f.get("geom_type") == geom_type]

            geom_lbl_map = {
                "Point": "Ponto",
                "LineString": "Linha",
                "Polygon": "Polígono",
                "Text": "Texto"
            }
            lbl = geom_lbl_map.get(geom_type, "Feição")

            for f in feats:
                handle = f.get("handle")
                feat_item = QStandardItem(f"{lbl} #{handle}")
                feat_item.setCheckable(False)
                feat_item.setEditable(False)
                feat_item.setData(handle, Qt.ItemDataRole.UserRole)
                item.appendRow([feat_item])

    def on_tree_node_clicked(self, index):
        """Sincroniza o clique na feição da árvore para selecioná-la no canvas."""
        source_index = self.proxy_model.mapToSource(index)
        item = self.tree_model.itemFromIndex(source_index)
        if not item:
            return

        handle = item.data(Qt.ItemDataRole.UserRole)
        # Se for um inteiro (handle), seleciona
        if handle and isinstance(handle, int):
            modifiers = QApplication.keyboardModifiers()
            additive = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
            self.preview_canvas.select_features([handle], additive=additive)
