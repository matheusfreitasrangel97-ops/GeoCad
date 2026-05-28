@echo off
echo =======================================================
echo Compilador GeoCAD Bridge (Distribuicao Standalone)
echo =======================================================
echo.

echo [1/3] Limpando arquivos de builds anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo.

echo [2/3] Iniciando empacotamento com PyInstaller...
echo Isso pode levar alguns minutos. Aguarde...
call "C:\Program Files\QGIS 4.0.1\bin\python-qgis.bat" -m PyInstaller --noconfirm --onedir --windowed --name "GeoCAD_Bridge" --add-binary "bin/dwg2dxf.exe;bin" Solucoes_DWG.py
echo.

echo [3/3] Processo finalizado!
echo =======================================================
echo O seu aplicativo pronto para uso esta localizado na pasta:
echo %CD%\dist\GeoCAD_Bridge
echo.
echo Para abrir o programa, basta entrar nessa pasta e dar um
echo clique duplo no arquivo GeoCAD_Bridge.exe
echo =======================================================
pause
