# -*- coding: utf-8 -*-
"""
GeoCad - Lógica de Atualizações (Verificação e Download)
Contém os workers QThread para checagem assíncrona de releases e downloads em streaming.
"""
import os
import hashlib
import tempfile
import logging
import requests
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger("geocad.updater")

class UpdateCheckerWorker(QThread):
    """
    Worker assíncrono para verificar atualizações no GitHub Releases.
    Não bloqueia a interface do usuário.
    """
    update_available = pyqtSignal(str, str, str, str)  # versão, download_url, sha256, notas
    finished = pyqtSignal()

    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version

    def run(self):
        try:
            # Consulta a API oficial de releases do GitHub
            url = "https://api.github.com/repos/matheusfreitasrangel97-ops/GeoCad/releases/latest"
            headers = {
                'User-Agent': 'GeoCad-Updater-Agent',
                'Accept': 'application/vnd.github+json'
            }
            
            response = requests.get(url, headers=headers, timeout=6)
            if response.status_code == 200:
                release_data = response.json()
                tag_name = release_data.get("tag_name", "")
                remote_version_str = tag_name.lstrip('v') # Remove prefixo 'v' se houver
                
                # Procura os assets version.json e GeoCad.zip
                version_asset = None
                zip_asset = None
                for asset in release_data.get("assets", []):
                    name = asset.get("name", "")
                    if name == "version.json":
                        version_asset = asset
                    elif name == "GeoCad.zip":
                        zip_asset = asset

                if version_asset:
                    # Faz o download do arquivo de metadados version.json da release
                    v_resp = requests.get(version_asset["browser_download_url"], headers=headers, timeout=6)
                    if v_resp.status_code == 200:
                        v_data = v_resp.json()
                        remote_version = v_data.get("version", remote_version_str)
                        sha256_val = v_data.get("sha256", "")
                        download_url = v_data.get("download_url") or (zip_asset["browser_download_url"] if zip_asset else "")
                        notes = release_data.get("body", "Sem notas de lançamento disponíveis.")
                        
                        # Compara as strings de versão de forma segura
                        from distutils.version import LooseVersion
                        try:
                            is_newer = LooseVersion(remote_version) > LooseVersion(self.current_version)
                        except Exception:
                            # Fallback simples por quebra de pontos
                            is_newer = tuple(map(int, remote_version.split('.'))) > tuple(map(int, self.current_version.split('.')))
                            
                        if is_newer:
                            logger.info(f"Nova versão identificada: {remote_version} (Versão Atual: {self.current_version})")
                            self.update_available.emit(remote_version, download_url, sha256_val, notes)
                        else:
                            logger.info(f"O GeoCad já está rodando a versão mais recente ({self.current_version})")
            else:
                logger.warning(f"Erro ao consultar API do GitHub: Status {response.status_code}")
        except Exception as e:
            logger.error(f"Falha na checagem de atualizações: {e}")
        finally:
            self.finished.emit()


class UpdateDownloaderWorker(QThread):
    """
    Worker assíncrono para baixar a atualização em streaming (chunks).
    Calcula e valida o SHA256 durante/após a gravação física.
    """
    progress = pyqtSignal(float, float, float)  # porcentagem, baixado_mb, total_mb
    finished = pyqtSignal(str)                 # caminho do ZIP baixado
    error = pyqtSignal(str)                    # mensagem de erro
    cancelled = pyqtSignal()

    def __init__(self, download_url, expected_sha256):
        super().__init__()
        self.download_url = download_url
        self.expected_sha256 = expected_sha256
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            logger.info(f"Iniciando download da atualização a partir de: {self.download_url}")
            headers = {'User-Agent': 'GeoCad-Updater-Agent'}
            
            # Streaming ativado (stream=True)
            response = requests.get(self.download_url, headers=headers, stream=True, timeout=15)
            if response.status_code != 200:
                self.error.emit(f"Falha na conexão de download. Servidor retornou código HTTP {response.status_code}")
                return

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            block_size = 16384  # Chunks de 16KB para suavidade no relatório de progresso
            
            temp_dir = tempfile.gettempdir()
            zip_path = os.path.join(temp_dir, "GeoCad_update.zip")
            
            # Inicializa hasher SHA256
            sha256_hash = hashlib.sha256()
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if self._is_cancelled:
                        logger.info("Download cancelado pelo usuário.")
                        # Limpa o arquivo inacabado
                        f.close()
                        try:
                            os.remove(zip_path)
                        except Exception:
                            pass
                        self.cancelled.emit()
                        return
                        
                    if chunk:
                        f.write(chunk)
                        sha256_hash.update(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            percent = downloaded_size / total_size
                            self.progress.emit(percent, downloaded_size / (1024 * 1024), total_size / (1024 * 1024))
                        else:
                            self.progress.emit(-1.0, downloaded_size / (1024 * 1024), 0.0)

            # Calcula o hash final
            calculated_sha = sha256_hash.hexdigest().lower()
            expected_sha = self.expected_sha256.strip().lower()
            
            logger.info(f"Download concluído. Hash SHA256 calculado: {calculated_sha}")
            
            if expected_sha and calculated_sha != expected_sha:
                logger.error(f"Erro de integridade! Hash calculado ({calculated_sha}) diferente do esperado ({expected_sha})")
                self.error.emit(
                    f"A validação de integridade falhou!\n\n"
                    f"SHA256 Esperado: {expected_sha}\n"
                    f"SHA256 Obtido: {calculated_sha}\n\n"
                    f"O download pode ter sido corrompido ou interceptado."
                )
                try:
                    os.remove(zip_path)
                except Exception:
                    pass
                return

            self.finished.emit(zip_path)
        except Exception as e:
            logger.error(f"Erro no download da atualização: {e}")
            self.error.emit(f"Erro durante o download da atualização:\n{str(e)}")
