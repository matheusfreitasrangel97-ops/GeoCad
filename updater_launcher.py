# -*- coding: utf-8 -*-
"""
GeoCad - Inicializador do Atualizador Externo
Responsável por disparar o atualizador isolado (processo externo) e fechar o app.
"""
import os
import sys
import tempfile
import subprocess

def launch_updater_and_exit(zip_path):
    """
    Configura os argumentos, dispara o processo do atualizador externo 
    e finaliza o GeoCad imediatamente para liberar os arquivos ativos.
    """
    if getattr(sys, 'frozen', False):
        app_executable = sys.executable
        app_dir = os.path.dirname(app_executable)
        exe_name = os.path.basename(app_executable)
        restart_cmd = app_executable
        updater_executable = os.path.join(app_dir, "updater.exe")
        is_frozen = True
    else:
        # Execução via código fonte (desenvolvimento)
        app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        exe_name = "python.exe"
        restart_cmd = os.path.join(app_dir, "main.py")
        updater_executable = os.path.join(app_dir, "updater.exe")
        is_frozen = False

    backup_dir = os.path.join(app_dir, "backup", "current")
    
    # Garante que os diretórios necessários existem
    os.makedirs(os.path.join(app_dir, "updates"), exist_ok=True)
    os.makedirs(os.path.join(app_dir, "backup"), exist_ok=True)

    # Argumentos para o updater
    args = [
        "--app-dir", app_dir,
        "--zip-path", zip_path,
        "--exe-name", exe_name,
        "--backup-dir", backup_dir,
        "--restart-cmd", restart_cmd,
        "--pid", str(os.getpid())
    ]

    # Se estiver rodando como executável compilado e o updater.exe existir na pasta
    if is_frozen and os.path.exists(updater_executable):
        cmd = [updater_executable] + args
        print(f"[LAUNCHER] Executando executável compilado: {cmd}")
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        # Se for ambiente de desenvolvimento (código fonte), gera um updater.bat temporário que executa o script python
        updater_py = os.path.join(app_dir, "updater_process.py")
        if os.path.exists(updater_py):
            bat_path = os.path.join(tempfile.gettempdir(), "geocad_updater_dev.bat")
            cmd_args = subprocess.list2cmdline([sys.executable, updater_py] + args)
            
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write("@echo off\n")
                f.write("chcp 65001 > nul\n")
                f.write("echo =======================================================\n")
                f.write("echo Instalando Atualizacao do GeoCad (Modo Desenvolvimento)...\n")
                f.write("echo =======================================================\n")
                f.write(f"{cmd_args}\n")
                f.write("del \"%~f0\"\n")
                
            print(f"[LAUNCHER] Gerado e executando bat de desenvolvimento: {bat_path}")
            subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            # Caso extremo de fallback (cria um arquivo batch temporário que faz o backup e extração via powershell)
            bat_path = os.path.join(tempfile.gettempdir(), "geocad_fallback_updater.bat")
            
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write("@echo off\n")
                f.write("chcp 65001 > nul\n")
                f.write("echo =======================================================\n")
                f.write("echo Instalando Atualização do GeoCad (Modo de Fallback)...\n")
                f.write("echo =======================================================\n")
                f.write("echo Aguardando o GeoCad encerrar...\n")
                f.write("timeout /t 2 /nobreak > nul\n")
                
                # Backup de segurança
                f.write(f"echo Criando backup em backup/current/...\n")
                f.write(f"if exist \"{backup_dir}\" rd /s /q \"{backup_dir}\"\n")
                f.write(f"mkdir \"{backup_dir}\"\n")
                f.write(f"xcopy /y /e /s /i \"{app_dir}\\*.*\" \"{backup_dir}\\\" >nul\n")
                
                # Descompactação
                f.write(f"echo Extraindo arquivos...\n")
                f.write(f"powershell -Command \"Expand-Archive -Path '{zip_path}' -DestinationPath '{app_dir}' -Force\" >nul\n")
                
                # Reinício
                f.write(f"echo Reiniciando aplicativo...\n")
                if is_frozen:
                    f.write(f"start \"\" \"{app_executable}\"\n")
                else:
                    f.write(f"start \"\" \"{sys.executable}\" \"{restart_cmd}\"\n")
                
                f.write(f"del /q \"{zip_path}\"\n")
                f.write("del \"%~f0\"\n")
                
            subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE)

    # Encerra o app principal imediatamente para que o updater consiga escrever nos arquivos
    sys.exit(0)
