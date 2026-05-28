import os
import sys
import subprocess
import tempfile
import logging

logger = logging.getLogger("geocad.cad.converter")

def find_bundled_converter():
    """
    Tenta localizar automaticamente o executável do dwg2dxf.exe embutido.
    Suporta caminhos do script de desenvolvimento, workspace e executável empacotado.
    """
    # 1. Se estiver rodando dentro do executável PyInstaller (sys._MEIPASS)
    if hasattr(sys, "_MEIPASS"):
        path = os.path.join(sys._MEIPASS, "bin", "dwg2dxf.exe")
        if os.path.exists(path):
            logger.info(f"Conversor LibreDWG localizado em recursos temporários: {path}")
            return path

    # 2. Verifica relativo ao diretório do script principal executado
    main_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    path = os.path.join(main_dir, "bin", "dwg2dxf.exe")
    if os.path.exists(path):
        logger.info(f"Conversor LibreDWG localizado relativo ao executável: {path}")
        return path

    # 3. Verifica relativo ao workspace atual
    workspace_dir = r"C:\Users\estagiario\.gemini\antigravity-ide\scratch\QFieldLiteWorkspace"
    path = os.path.join(workspace_dir, "bin", "dwg2dxf.exe")
    if os.path.exists(path):
        logger.info(f"Conversor LibreDWG localizado no diretório de desenvolvimento: {path}")
        return path

    logger.warning("Conversor dwg2dxf.exe não pôde ser localizado de forma automatizada.")
    return None

def convert_dwg_to_dxf(dwg_path, converter_path=None, timeout=60):
    """
    Converte um arquivo DWG para DXF de forma silenciosa usando o LibreDWG (dwg2dxf.exe).
    Salva o resultado em uma pasta temporária do sistema e retorna o caminho gerado.
    """
    if not os.path.exists(dwg_path):
        raise FileNotFoundError(f"Arquivo DWG não encontrado: {dwg_path}")

    if not converter_path:
        converter_path = find_bundled_converter()
        if not converter_path:
            raise FileNotFoundError(
                "O executável do conversor LibreDWG (dwg2dxf.exe) não foi encontrado no pacote da aplicação."
            )

    if not os.path.exists(converter_path):
        raise FileNotFoundError(f"O caminho configurado do conversor não existe: {converter_path}")

    # Define o caminho de saída no diretório temporário do sistema
    filename = os.path.basename(dwg_path)
    name_part, _ = os.path.splitext(filename)
    temp_dxf_path = os.path.join(tempfile.gettempdir(), f"{name_part}_temp_converted.dxf")
    
    # Se já existir um arquivo temporário de conversão anterior, tentamos remover
    if os.path.exists(temp_dxf_path):
        try:
            os.remove(temp_dxf_path)
        except Exception:
            pass

    logger.info(f"Iniciando conversão silenciosa de DWG: {filename}")
    
    # Executa a conversão via CLI do LibreDWG:
    # dwg2dxf.exe -y -o "caminho_saida.dxf" "caminho_entrada.dwg"
    args = [
        converter_path,
        "-y",               # Sobrescrever se já existir
        "-o", temp_dxf_path, # Caminho de saída
        dwg_path            # Caminho de entrada
    ]
    
    logger.debug(f"Executando processo: {' '.join(args)}")
    
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False
    )
    
    if result.returncode != 0:
        logger.error(f"Erro no processo de conversão (código {result.returncode}): {result.stderr}")
        raise RuntimeError(
            f"Falha ao converter arquivo DWG para DXF via LibreDWG.\nDetalhes: {result.stderr or result.stdout}"
        )
        
    # Valida o arquivo DXF de saída gerado
    if not os.path.exists(temp_dxf_path):
        raise RuntimeError("Conversão concluída, mas o arquivo DXF resultante não foi gerado.")
        
    if os.path.getsize(temp_dxf_path) == 0:
        raise RuntimeError("O arquivo DXF temporário gerado está vazio (0 bytes).")

    logger.info(f"Conversão concluída com sucesso. DXF temporário salvo em: {temp_dxf_path}")
    return temp_dxf_path
