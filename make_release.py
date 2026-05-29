# -*- coding: utf-8 -*-
"""
GeoCad - Script Auxiliar para Criação de Releases no GitHub.
Este script empacota os arquivos do GeoCad, calcula o hash SHA256,
atualiza o version.json e cria a Release oficial com os assets no GitHub.
"""
import os
import sys
import zipfile
import hashlib
import json
import requests
import subprocess

# Garante que o diretório atual está no path para importação modular
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geocad.version import VERSION

REPO = "matheusfreitasrangel97-ops/GeoCad"
TAG_NAME = f"v{VERSION}"

def get_github_token():
    """Recupera o token do GitHub armazenado no gerenciador de credenciais do Git local."""
    print("Buscando token do GitHub no gerenciador de credenciais do Git...")
    try:
        p = subprocess.Popen(['git', 'credential', 'fill'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        out, _ = p.communicate('protocol=https\nhost=github.com\n\n')
        for line in out.splitlines():
            if line.startswith('password='):
                token = line.split('=', 1)[1].strip()
                if token:
                    print("Token do GitHub obtido com sucesso via Git Credential Helper.")
                    return token
    except Exception as e:
        print(f"Aviso ao consultar credenciais do Git: {e}")
        
    # Fallback para variável de ambiente
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        print("Token obtido da variável de ambiente GITHUB_TOKEN.")
        return token
        
    return ""

def main():
    token = get_github_token()
    if not token:
        print("ERRO: Token do GitHub não encontrado!")
        print("Certifique-se de estar autenticado no Git ou de configurar a variável de ambiente GITHUB_TOKEN.")
        return
        
    print(f"Iniciando empacotamento do GeoCad v{VERSION}...")
    zip_filename = "GeoCad.zip"
    
    # Arquivos e pastas a incluir no pacote
    include_dirs = ["geocad", "ui", "cad", "gis", "render", "utils", "workers"]
    include_files = [
        "main.py",
        "updater.exe",
        "updater_launcher.py",
        "updater_process.py",
        "requirements.txt",
        "requirements-dev.txt",
        "LICENSE",
        "README.md",
        "CHANGELOG.md",
        "build.bat",
        "GeoCad.spec",
        "installer.iss"
    ]
    
    # 1. Cria a versão inicial do version.json localmente (com hash temporário)
    download_url = f"https://github.com/{REPO}/releases/download/{TAG_NAME}/{zip_filename}"
    version_data = {
        "version": VERSION,
        "sha256": "placeholder",
        "download_url": download_url
    }
    with open("version.json", "w", encoding="utf-8") as f:
        json.dump(version_data, f, indent=2)
    print("version.json inicial criado.")

    # 2. Cria o arquivo ZIP contendo o version.json inicial
    if os.path.exists(zip_filename):
        os.remove(zip_filename)
        
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as z:
        # Adiciona version.json inicial
        z.write("version.json")
        print("Adicionado version.json inicial ao ZIP.")
        
        # Adiciona arquivos individuais
        for file in include_files:
            if os.path.exists(file):
                z.write(file)
                print(f"Adicionado arquivo: {file}")
                
        # Adiciona diretórios recursivamente
        for directory in include_dirs:
            if os.path.exists(directory):
                for root, dirs, files in os.walk(directory):
                    # Ignora __pycache__ e logs
                    if "__pycache__" in root:
                        continue
                    for file in files:
                        filepath = os.path.join(root, file)
                        z.write(filepath)
                        print(f"Adicionado: {filepath}")

    print("ZIP gerado com sucesso. Calculando hash SHA256 do ZIP final contendo version.json...")
    
    # 3. Calcula SHA256 do ZIP final
    sha256_hash = hashlib.sha256()
    with open(zip_filename, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    sha256_val = sha256_hash.hexdigest()
    print(f"Hash SHA256 final calculado: {sha256_val}")
    
    # 4. Atualiza version.json localmente com o hash definitivo do ZIP final
    version_data["sha256"] = sha256_val
    with open("version.json", "w", encoding="utf-8") as f:
        json.dump(version_data, f, indent=2)
    print("version.json final atualizado localmente com o hash definitivo.")

    # 4. Criar a release no GitHub via API
    print("Conectando à API do GitHub para criar a Release...")
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }
    
    release_url = f"https://api.github.com/repos/{REPO}/releases"
    release_payload = {
        "tag_name": TAG_NAME,
        "target_commitish": "main",
        "name": TAG_NAME,
        "body": f"Lançamento oficial da versão {VERSION} do GeoCad com sistema de auto-atualização em background.",
        "draft": False,
        "prerelease": False
    }
    
    # Verifica se a release já existe
    check_resp = requests.get(f"{release_url}/tags/{TAG_NAME}", headers=headers)
    if check_resp.status_code == 200:
        existing_release = check_resp.json()
        print(f"Release {TAG_NAME} já existe. Deletando release antiga (ID: {existing_release['id']}) para recriar...")
        del_resp = requests.delete(f"{release_url}/{existing_release['id']}", headers=headers)
        if del_resp.status_code == 204:
            print("Release antiga deletada.")
            
    # Cria a nova release
    resp = requests.post(release_url, headers=headers, json=release_payload)
    if resp.status_code not in [200, 201]:
        print(f"Erro ao criar a release: {resp.status_code}")
        print(resp.text)
        return
        
    release_info = resp.json()
    upload_url_tmpl = release_info["upload_url"]
    upload_url = upload_url_tmpl.split("{")[0]
    print(f"Release criada com sucesso! ID: {release_info['id']}")
    
    # 5. Upload dos assets
    for asset_name, mime_type in [("GeoCad.zip", "application/zip"), ("version.json", "application/json")]:
        print(f"Enviando asset '{asset_name}'...")
        with open(asset_name, "rb") as asset_file:
            asset_data = asset_file.read()
            
        asset_upload_url = f"{upload_url}?name={asset_name}"
        upload_headers = headers.copy()
        upload_headers["Content-Type"] = mime_type
        upload_headers["Content-Length"] = str(len(asset_data))
        
        up_resp = requests.post(asset_upload_url, headers=upload_headers, data=asset_data)
        if up_resp.status_code in [200, 201, 202]:
            print(f"Asset '{asset_name}' enviado com sucesso!")
        else:
            print(f"Erro ao enviar asset '{asset_name}': {up_resp.status_code}")
            print(up_resp.text)

if __name__ == "__main__":
    main()
