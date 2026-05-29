import os
import sys
import subprocess

def run_build():
    """
    Executa o empacotamento do GeoCad com PyInstaller.
    Compila o projeto em um único arquivo executável standalone (.exe)
    incluindo todas as dependências internas e utilitários do LibreDWG.
    """
    print("Iniciando build do GeoCad...")
    
    # Valida presença dos binários do LibreDWG
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    bin_path = os.path.join(workspace_dir, "bin", "dwg2dxf.exe")
    if not os.path.exists(bin_path):
        print(f"ERRO: Executável do conversor LibreDWG não localizado em: {bin_path}")
        print("Certifique-se de que os binários do LibreDWG estão na pasta 'bin' antes de compilar.")
        sys.exit(1)

    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller não está instalado no ambiente Python. Instalando dependência de build...")
        # Usa o pip do interpretador atual para instalar o pyinstaller
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    import PyInstaller.__main__

    # Parâmetros de compilação do PyInstaller:
    # - --onefile: compacta tudo em um único arquivo .exe independente
    # - --noconsole: oculta a janela de terminal preta ao abrir a GUI
    # - --add-data: inclui a pasta 'bin/' (LibreDWG) no diretório de recursos internos do executável
    # - --clean: limpa o cache do compilador antes de iniciar
    args = [
        'main.py',
        '--onefile',
        '--noconsole',
        '--add-data=bin/*;bin',
        '--collect-all=pyogrio',
        '--name=GeoCad',
        '--clean'
    ]

    print(f"Executando comando do PyInstaller com argumentos: {args}")
    PyInstaller.__main__.run(args)
    print("Compilação finalizada! O executável final estará disponível na pasta 'dist/'.")

if __name__ == "__main__":
    run_build()
