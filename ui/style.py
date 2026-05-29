# Folha de estilos do tema visual claro profissional do GeoCAD Bridge
# Todos os comentários em Português Brasileiro conforme padrão do projeto

DARK_THEME_STYLESHEET = """
QMainWindow {
    background-color: #f3f4f6; /* Fundo principal cinza claro */
}

QWidget {
    color: #1f2937; /* Texto escuro e legível em toda a aplicação */
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

/* Painel da Barra Lateral */
QFrame#sidebar {
    background-color: #ffffff; /* Fundo branco puro para a barra lateral */
    border-right: 1px solid #e5e7eb; /* Borda cinza suave */
    border-radius: 0px;
}

/* Divisor Redimensionável (QSplitter) */
QSplitter::handle:horizontal {
    background-color: #e5e7eb;
    width: 3px;
    margin: 0px;
}

QSplitter::handle:horizontal:hover {
    background-color: #0f766e;
}

/* Rótulos de Texto */
QLabel {
    font-weight: 500;
    color: #1f2937;
}

QLabel#title_label {
    font-size: 20px;
    font-weight: bold;
    color: #0f766e; /* Azul esverdeado / Petrol premium */
    margin-bottom: 2px;
}

QLabel#crs_status {
    background-color: #f8fafc;
    color: #475569;
    padding: 10px;
    font-weight: bold;
    border-radius: 6px;
    border: 1px solid #cbd5e1;
}

/* Botões da Interface */
QPushButton {
    background-color: #ffffff;
    color: #0f766e;
    border: 1.5px solid #0f766e;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #0f766e;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #115e59;
    color: #ffffff;
}

QPushButton#export_btn {
    background-color: #2563eb; /* Azul brilhante e moderno */
    color: #ffffff;
    border: 1.5px solid #1d4ed8;
}

QPushButton#export_btn:hover {
    background-color: #1d4ed8;
}

QPushButton#export_btn:disabled {
    background-color: #f3f4f6;
    color: #9ca3af;
    border-color: #e5e7eb;
}

QPushButton#action_btn {
    background-color: #f1f5f9;
    color: #334155;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: bold;
    font-size: 12px;
}

QPushButton#action_btn:hover {
    background-color: #e2e8f0;
    color: #0f766e;
    border-color: #94a3b8;
}

/* Botão de Alternância de Painel Recolhível */
QToolButton#toggle_status {
    background-color: #f1f5f9;
    color: #475569;
    border: 1px solid #e5e7eb;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: bold;
}

QToolButton#toggle_status:hover {
    background-color: #e2e8f0;
    color: #0f766e;
    border-color: #0f766e;
}

QToolButton#toggle_status:checked {
    background-color: #ccfbf1;
    color: #0f766e;
    border-color: #0f766e;
}

/* Botões de Modo de Interação na Toolbar */
QPushButton#mode_btn_active {
    background-color: #0f766e;
    color: #ffffff;
    border: 1.5px solid #115e59;
    border-radius: 6px;
    padding: 5px 12px;
    font-weight: bold;
    font-size: 12px;
}

QPushButton#mode_btn_inactive {
    background-color: #ffffff;
    color: #64748b;
    border: 1.5px solid #cbd5e1;
    border-radius: 6px;
    padding: 5px 12px;
    font-weight: bold;
    font-size: 12px;
}

QPushButton#mode_btn_inactive:hover {
    color: #0f766e;
    border-color: #0f766e;
}

/* Campos de Texto (Busca) */
QLineEdit {
    background-color: #ffffff;
    color: #1f2937;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 7px;
}

QLineEdit:focus {
    border: 2px solid #0f766e;
}

/* Tabela de Camadas (TreeView) */
QTreeView {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    alternate-background-color: #f8fafc;
}

QTreeView::item {
    padding: 6px;
    border-bottom: 1px solid #f1f5f9;
}

QTreeView::item:hover {
    background-color: #f1f5f9;
    color: #0f766e;
}

QTreeView::item:selected {
    background-color: #ccfbf1;
    color: #0f766e;
    font-weight: bold;
}

QTreeView::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    background-color: #ffffff;
}

QTreeView::indicator:hover {
    border-color: #0d9488;
    background-color: #f0fdfa;
}

QTreeView::indicator:checked {
    border-color: #0d9488;
    background-color: #0d9488;
}

QTreeView::indicator:checked:hover {
    border-color: #0f766e;
    background-color: #0f766e;
}

QTreeView::indicator:indeterminate {
    border-color: #0d9488;
    background-color: #ccfbf1;
}

QTreeView::indicator:indeterminate:hover {
    border-color: #0f766e;
    background-color: #a7f3d0;
}

QHeaderView::section {
    background-color: #f1f5f9;
    color: #0f766e;
    padding: 6px;
    border: none;
    font-weight: bold;
}

/* Barra de Progresso */
QProgressBar {
    background-color: #e2e8f0;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    text-align: center;
    color: #1f2937;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #0d9488, stop:1 #0f766e);
    border-radius: 5px;
}

/* Log de Processamento estilo Terminal Premium */
QTextEdit {
    background-color: #1e293b; /* Fundo azul slate escuro */
    color: #f8fafc;            /* Texto quase branco super visível */
    border: 1px solid #475569;
    border-radius: 6px;
    font-family: Consolas, 'Courier New', monospace;
    font-size: 11px;
}

/* Menu de Contexto Profissional */
QMenu {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 4px 0px;
}

QMenu::item {
    padding: 6px 24px;
    color: #1f2937;
    font-size: 12px;
}

QMenu::item:selected {
    background-color: #ccfbf1;
    color: #0f766e;
    font-weight: bold;
}

QMenu::separator {
    height: 1px;
    background-color: #e5e7eb;
    margin: 4px 8px;
}

/* Barras de Rolagem */
QScrollBar:vertical {
    border: none;
    background: #f1f5f9;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}

QScrollBar:horizontal {
    border: none;
    background: #f1f5f9;
    height: 8px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #cbd5e1;
    min-width: 20px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background: #94a3b8;
}

/* Estilo explícito para caixas de diálogo QMessageBox para sanar o erro do cinza no branco */
QMessageBox {
    background-color: #ffffff;
}

QMessageBox QLabel {
    color: #1f2937;
    font-size: 13px;
}

QMessageBox QPushButton {
    background-color: #ffffff;
    color: #0f766e;
    border: 1.5px solid #cbd5e1;
    border-radius: 4px;
    padding: 5px 15px;
    font-weight: bold;
}

QMessageBox QPushButton:hover {
    background-color: #f1f5f9;
}

/* Rótulo de créditos da barra lateral */
QLabel#credits_label {
    color: #64748b;
    font-size: 11px;
    margin-top: 10px;
    font-style: italic;
    line-height: 14px;
}

/* Painel Lateral de Detalhes da Feição */
QFrame#details_sidebar {
    background-color: #ffffff;
    border-left: 1px solid #e5e7eb;
    border-radius: 0px;
}

QFrame#details_sidebar QTableWidget {
    background-color: #ffffff;
    gridline-color: #f1f5f9;
    border: none;
}

QFrame#details_sidebar QTableWidget::item {
    padding: 5px;
    border-bottom: 1px solid #f1f5f9;
    color: #1f2937;
}

QFrame#details_sidebar QTableWidget::item:selected {
    background-color: #ccfbf1;
    color: #0f766e;
}
"""
