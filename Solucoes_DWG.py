import sys
import os

# Adiciona o diretório atual ao path para garantir que as importações modulares funcionem corretamente
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from utils.logging_setup import setup_logging
from ui.main_window import MainWindow

def main():
    # Configura o log rotativo e de console
    setup_logging()
    
    # Inicia a aplicação GUI Qt
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()