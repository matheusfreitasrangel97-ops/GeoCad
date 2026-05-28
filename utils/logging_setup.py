"""
Configuração do sistema de logging do GeoCAD Bridge.

Responsabilidades:
    - Configura handlers de console e arquivo rotativo
    - Define formato padrão de mensagens de log
    - Garante que logs duplicados não sejam emitidos
"""

import os
import logging
from logging.handlers import RotatingFileHandler


def setup_logging():
    """
    Inicializa o sistema de logging com saída em console e arquivo rotativo.
    O arquivo de log é criado na pasta 'logs' do diretório do projeto.
    """
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "geocad_bridge.log")

    # Limpa handlers existentes para evitar duplicação de logs
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = []

    # Formato padrão de mensagens de log
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    )

    # Handler de console — exibe mensagens no terminal
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # Handler de arquivo rotativo — grava logs em disco com limite de tamanho
    # Máximo de 5 MB por arquivo, mantendo até 3 backups anteriores
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    # Ativa nível DEBUG para loggers específicos do projeto
    logging.getLogger("geocad_bridge").setLevel(logging.DEBUG)

    logging.info(f"Sistema de logging inicializado. Arquivo de log: {log_file}")
