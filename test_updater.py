# -*- coding: utf-8 -*-
"""
GeoCad - Script de Teste e Simulação do Auto-Atualizador
Este script cria um zip de teste local, inicia um servidor HTTP temporário,
dispara o diálogo PyQt6 de progresso de download e testa a substituição e reinício.
"""
import os
import sys
import time
import shutil
import zipfile
import hashlib
import threading
import http.server
import socketserver
from PyQt6.QtWidgets import QApplication

# Adiciona o diretório atual ao sys.path para permitir os imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.update_dialog import UpdateProgressDialog

PORT = 8089
ZIP_NAME = "GeoCad_mock_update.zip"

def create_mock_update_zip():
    print("[TESTE] Criando arquivos de atualização simulada...")
    temp_update_dir = "mock_update_dir"
    os.makedirs(temp_update_dir, exist_ok=True)
    
    # Cria um arquivo de teste que simula a nova versão
    with open(os.path.join(temp_update_dir, "versao_nova.txt"), "w", encoding="utf-8") as f:
        f.write("Esta é a nova versão 1.2.0 carregada de forma 100% automática!")
        
    # Zipa a pasta
    if os.path.exists(ZIP_NAME):
        os.remove(ZIP_NAME)
    shutil.make_archive("GeoCad_mock_update", 'zip', temp_update_dir)
    shutil.rmtree(temp_update_dir)
    
    # Calcula o hash SHA256
    sha256_hash = hashlib.sha256()
    with open(ZIP_NAME, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
            
    sha256_val = sha256_hash.hexdigest()
    print(f"[TESTE] Zip de teste criado: '{ZIP_NAME}' (SHA256: {sha256_val})")
    return sha256_val

class SilentTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def run_local_server():
    """Inicia um servidor web local simples para servir o ZIP de teste."""
    handler = http.server.SimpleHTTPRequestHandler
    with SilentTCPServer(("", PORT), handler) as httpd:
        print(f"[TESTE] Servidor HTTP local iniciado na porta {PORT}.")
        httpd.serve_forever()

def main():
    # 1. Cria o zip simulado e pega seu hash
    expected_sha256 = create_mock_update_zip()
    
    # 2. Inicia o servidor HTTP local em segundo plano
    server_thread = threading.Thread(target=run_local_server, daemon=True)
    server_thread.start()
    time.sleep(1) # Aguarda o servidor subir
    
    # 3. Prepara a aplicação PyQt6
    app = QApplication(sys.argv)
    
    download_url = f"http://localhost:{PORT}/{ZIP_NAME}"
    print(f"[TESTE] Iniciando UpdateProgressDialog para baixar de {download_url}...")
    
    # 4. Abre a janela do atualizador
    dialog = UpdateProgressDialog(download_url, expected_sha256)
    
    # Mostra o diálogo e aguarda
    dialog.show()
    
    # O diálogo em si disparará a finalização e o sys.exit() ao concluir com sucesso
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
