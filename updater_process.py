# -*- coding: utf-8 -*-
"""
GeoCad - Módulo de Atualização Externo (Isolado)
Este script roda fora do processo principal do GeoCad e realiza a cópia
dos arquivos de atualização, backup e restauração em caso de erros (Rollback).
"""
import os
import sys
import time
import shutil
import zipfile
import subprocess
import argparse

def log_message(msg):
    log_line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(log_line)
    sys.stdout.flush()
    try:
        # Resolve a pasta logs relativa ao diretório deste script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logs_dir = os.path.join(script_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, "updater.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except Exception:
        pass

def is_pid_running(pid):
    """Verifica se um determinado PID está em execução no Windows."""
    if pid <= 0:
        return False
    try:
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
    except Exception:
        pass
    
    try:
        output = subprocess.check_output(
            f'tasklist /fi "PID eq {pid}"', 
            shell=True
        ).decode('utf-8', errors='ignore')
        return "No tasks are running" not in output and str(pid) in output
    except Exception:
        return False

def wait_for_process_exit(pid, exe_name, timeout_sec=15):
    """Aguarda o fechamento do processo do GeoCad (por PID ou nome) para evitar bloqueios de arquivo."""
    if pid > 0:
        log_message(f"Aguardando encerramento do processo GeoCad (PID: {pid})...")
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            if not is_pid_running(pid):
                log_message(f"Processo (PID: {pid}) encerrado.")
                return True
            time.sleep(1)
        
        # Se estourar o tempo limite, tenta forçar o encerramento por PID (seguro, não mata outros pythons)
        log_message(f"Tempo limite esgotado. Tentando encerrar processo PID {pid} de forma forçada...")
        try:
            subprocess.run(f'taskkill /f /pid {pid}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        return True

    # Fallback por nome de imagem (apenas se não houver PID e se o nome for seguro)
    if exe_name.lower() in ["python.exe", "pythonw.exe"]:
        log_message("Aviso: Nome de executável genérico (python.exe). Aguardando fechamento apenas por tempo (1s)...")
        time.sleep(1)
        return True

    log_message(f"Aguardando encerramento do processo '{exe_name}'...")
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        try:
            output = subprocess.check_output(
                f'tasklist /fi "IMAGENAME eq {exe_name}"', 
                shell=True
            ).decode('utf-8', errors='ignore')
            
            if exe_name.lower() not in output.lower():
                log_message(f"Processo '{exe_name}' encerrado.")
                return True
        except Exception as e:
            log_message(f"Aviso ao consultar processos: {e}")
            break
        time.sleep(1)
    
    # Se estourar o tempo limite, tenta forçar o encerramento do processo
    log_message("Tempo limite esgotado. Tentando encerrar processo de forma forçada...")
    try:
        subprocess.run(f'taskkill /f /im "{exe_name}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    return True

def create_backup(app_dir, backup_dir):
    """Cria uma cópia de segurança de todos os arquivos da instalação atual em backup/current/."""
    log_message("Criando backup de segurança da versão instalada...")
    if os.path.exists(backup_dir):
        try:
            shutil.rmtree(backup_dir)
        except Exception as e:
            log_message(f"Erro ao remover backup antigo: {e}")
            
    os.makedirs(backup_dir, exist_ok=True)
    
    exclude_dirs = {'updates', 'backup', '.git', '.venv', '__pycache__', 'build', 'dist', 'logs'}
    exclude_files = {'updater.exe', 'updater_process.py', 'updater_launcher.py', 'GeoCad.spec'}
    
    copied_count = 0
    for root, dirs, files in os.walk(app_dir):
        # Filtra os diretórios para não entrar nas pastas excluídas
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file in exclude_files:
                continue
            src_file = os.path.join(root, file)
            rel_path = os.path.relpath(src_file, app_dir)
            dest_file = os.path.join(backup_dir, rel_path)
            
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            shutil.copy2(src_file, dest_file)
            copied_count += 1
            
    log_message(f"Backup concluído. {copied_count} arquivos salvos.")

def extract_update(zip_path, app_dir):
    """Extrai os arquivos do ZIP diretamente na pasta raiz do aplicativo."""
    log_message(f"Extraindo arquivos da atualização: '{zip_path}'...")
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"Arquivo de atualização não localizado em: {zip_path}")
        
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Extrai tudo diretamente
        zip_ref.extractall(app_dir)
    log_message("Arquivos da atualização extraídos com sucesso.")

def restore_backup(backup_dir, app_dir):
    """Restaura o backup anterior caso ocorra falha crítica na atualização (Rollback)."""
    log_message("ERRO CRÍTICO DETECTADO: Iniciando restauração do backup (Rollback)...")
    if not os.path.exists(backup_dir):
        log_message("Falha catastrófica: Pasta de backup não localizada!")
        return
        
    restored_count = 0
    for root, dirs, files in os.walk(backup_dir):
        for file in files:
            src_file = os.path.join(root, file)
            rel_path = os.path.relpath(src_file, backup_dir)
            dest_file = os.path.join(app_dir, rel_path)
            
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            shutil.copy2(src_file, dest_file)
            restored_count += 1
            
    log_message(f"Rollback concluído! {restored_count} arquivos restaurados da versão anterior.")

def restart_app(app_executable):
    """Reinicia o GeoCad em uma nova console do sistema."""
    log_message(f"Reiniciando o aplicativo: '{app_executable}'...")
    try:
        # Limpa variáveis de ambiente do PyInstaller para evitar conflitos no processo filho
        env = os.environ.copy()
        env.pop('_MEIPASS', None)
        env.pop('_MEIPASS2', None)

        if sys.platform == "win32":
            import ctypes
            try:
                ctypes.windll.kernel32.SetDllDirectoryW(None)
            except Exception as e:
                log_message(f"Falha ao resetar SetDllDirectoryW: {e}")

        # Se for script Python (desenvolvimento), executa via python
        if app_executable.endswith('.py'):
            subprocess.Popen([sys.executable, app_executable], env=env, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen([app_executable], env=env, creationflags=subprocess.CREATE_NEW_CONSOLE)
        log_message("Aplicativo reiniciado.")
    except Exception as e:
        log_message(f"Erro ao reiniciar o aplicativo: {e}")

def main():
    parser = argparse.ArgumentParser(description="Atualizador externo para GeoCad.")
    parser.add_argument("--app-dir", required=True, help="Diretório raiz do GeoCad")
    parser.add_argument("--zip-path", required=True, help="Caminho do arquivo ZIP da atualização")
    parser.add_argument("--exe-name", default="GeoCad.exe", help="Nome do arquivo executável do GeoCad")
    parser.add_argument("--backup-dir", required=True, help="Diretório onde salvar o backup")
    parser.add_argument("--restart-cmd", required=True, help="Caminho ou script do executável para reiniciar")
    parser.add_argument("--pid", type=int, default=0, help="PID do processo do GeoCad a aguardar")
    
    args = parser.parse_args()
    
    time.sleep(1) # Pequena pausa para liberação inicial de processos
    
    # 1. Aguarda o fechamento do GeoCad
    wait_for_process_exit(args.pid, args.exe_name)
    
    backup_success = False
    try:
        # 2. Cria o backup antes de alterar os arquivos
        create_backup(args.app_dir, args.backup_dir)
        backup_success = True
        
        # 3. Extrai e instala a atualização
        extract_update(args.zip_path, args.app_dir)
        log_message("Atualização concluída com sucesso!")
        
        # Limpa o ZIP baixado após atualização bem-sucedida
        try:
            os.remove(args.zip_path)
            log_message("Arquivo ZIP temporário limpo.")
        except Exception:
            pass
            
    except Exception as e:
        log_message(f"Falha na instalação da atualização: {e}")
        # 4. Executa rollback em caso de falhas
        if backup_success:
            try:
                restore_backup(args.backup_dir, args.app_dir)
            except Exception as re:
                log_message(f"Erro ao restaurar backup: {re}")
        else:
            log_message("Não foi possível realizar o rollback pois o backup falhou.")
            
    finally:
        # 5. Reinicia o GeoCad
        restart_app(args.restart_cmd)
        log_message("Processo de atualização finalizado.")
        time.sleep(2)

if __name__ == "__main__":
    main()
