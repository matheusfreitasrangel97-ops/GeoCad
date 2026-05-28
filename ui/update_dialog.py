# -*- coding: utf-8 -*-
"""
GeoCad - Diálogo de Progresso de Atualização
Interface gráfica (modal) para exibir o progresso de download e validação do ZIP.
"""
import os
import logging
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QMessageBox

from geocad.updater import UpdateDownloaderWorker
from updater_launcher import launch_updater_and_exit

logger = logging.getLogger("geocad.ui.update_dialog")

class UpdateProgressDialog(QDialog):
    """
    Diálogo modal PyQt6 que exibe o progresso do download do zip de atualização,
    valida integridade (SHA256) e chama o atualizador externo para reiniciar.
    """
    def __init__(self, download_url, sha256_hash, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.sha256_hash = sha256_hash
        self.zip_path = None
        self.worker = None
        
        self.setWindowTitle("Atualização do GeoCad")
        self.resize(450, 180)
        self.setModal(True)
        # Desabilita botão de fechar direto para forçar cancelamento via botão ou gerenciar thread
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        
        self.setup_ui()
        self.start_download()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Rótulo de status da etapa
        self.lbl_status = QLabel("Preparando download da atualização...")
        self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #1e293b;")
        layout.addWidget(self.lbl_status)

        # Barra de progresso do Qt
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                text-align: center;
                background-color: #f8fafc;
                color: #0f766e;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #0f766e;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Rótulo auxiliar (tamanho / porcentagem)
        self.lbl_details = QLabel("0% (0.0 MB / 0.0 MB)")
        self.lbl_details.setStyleSheet("font-size: 11px; color: #64748b;")
        layout.addWidget(self.lbl_details)

        # Botão de Cancelar
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setFixedHeight(32)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                color: #475569;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """)
        self.btn_cancel.clicked.connect(self.cancel_download)
        layout.addWidget(self.btn_cancel)

    def start_download(self):
        """Dispara a thread secundária para download do arquivo."""
        self.worker = UpdateDownloaderWorker(self.download_url, self.sha256_hash)
        
        # Conecta os sinais Qt do worker
        self.worker.progress.connect(self.on_download_progress)
        self.worker.finished.connect(self.on_download_finished)
        self.worker.error.connect(self.on_download_error)
        self.worker.cancelled.connect(self.on_download_cancelled)
        
        self.worker.start()

    def on_download_progress(self, percent, downloaded_mb, total_mb):
        """Atualiza a UI em resposta aos sinais da thread de download."""
        if percent < 0:
            # Tamanho do conteúdo é desconhecido
            self.lbl_status.setText("Baixando atualização (tamanho indefinido)...")
            self.progress_bar.setRange(0, 0) # Barra indeterminada
            self.lbl_details.setText(f"{downloaded_mb:.2f} MB baixados")
        else:
            self.lbl_status.setText("Baixando arquivos da nova versão...")
            self.progress_bar.setRange(0, 100)
            val = int(percent * 100)
            self.progress_bar.setValue(val)
            self.lbl_details.setText(f"{val}% ({downloaded_mb:.2f} MB de {total_mb:.2f} MB)")

    def on_download_finished(self, zip_path):
        """Callback executado quando o download e validação terminam com sucesso."""
        if not zip_path:
            # Indica que foi cancelado antes do fim
            return
            
        self.zip_path = zip_path
        self.lbl_status.setText("Validando integridade SHA256...")
        self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #16a34a;")
        self.progress_bar.setValue(100)
        self.btn_cancel.setEnabled(False)
        
        # Obter a pasta raiz do aplicativo de forma robusta
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(current_dir) == "ui":
            app_dir = os.path.dirname(current_dir)
        else:
            app_dir = current_dir
        updates_dir = os.path.join(app_dir, "updates")
        os.makedirs(updates_dir, exist_ok=True)
        
        # Move o zip baixado para a pasta updates/
        final_zip_path = os.path.join(updates_dir, "GeoCad_update.zip")
        try:
            if os.path.exists(final_zip_path):
                os.remove(final_zip_path)
            shutil_move_safely(self.zip_path, final_zip_path)
            self.zip_path = final_zip_path
        except Exception as e:
            logger.error(f"Erro ao mover arquivo de staging para pasta updates: {e}")
            # Se falhar ao mover, mantém na pasta temporária atual
            pass
            
        self.lbl_status.setText("Atualização pronta! Reiniciando...")
        self.update()
        
        # Agenda encerramento e lançamento do instalador externo
        self.close()
        launch_updater_and_exit(self.zip_path)

    def on_download_error(self, err_msg):
        """Callback para erros na thread de download."""
        QMessageBox.critical(
            self,
            "Erro no Download",
            f"Não foi possível concluir a atualização automática:\n\n{err_msg}"
        )
        self.reject()

    def on_download_cancelled(self):
        """Callback executado após a thread encerrar por cancelamento."""
        self.reject()

    def cancel_download(self):
        """Solicita o cancelamento seguro da thread."""
        self.btn_cancel.setEnabled(False)
        self.lbl_status.setText("Cancelando download...")
        if self.worker and self.worker.isRunning():
            self.worker.cancel()

    def closeEvent(self, event):
        """Garante que a thread do download seja parada se o diálogo for fechado de alguma forma."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
        super().closeEvent(event)


def shutil_move_safely(src, dst):
    """Auxiliar para mover arquivos de forma compatível entre diferentes partições no Windows."""
    import shutil
    try:
        shutil.move(src, dst)
    except OSError:
        # Fallback se mover entre partições lógicas diferentes
        shutil.copy2(src, dst)
        os.remove(src)
