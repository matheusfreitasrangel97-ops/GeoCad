[Setup]
; =======================================================
; Script Inno Setup para o GeoCAD Bridge
; =======================================================

; Informacoes do Aplicativo
AppName=GeoCAD Bridge
AppVersion=1.0
AppPublisher=Matheus Freitas Rangel
AppSupportURL=matheus-freitas-rangel@hotmail.com

; Diretorio de Instalacao (Arquivos de Programas)
DefaultDirName={autopf}\GeoCAD Bridge

; Pasta no Menu Iniciar
DefaultGroupName=GeoCAD Bridge

; Icone exibido no desinstalador (opcional, ele puxa do proprio .exe se omitido)
UninstallDisplayIcon={app}\GeoCAD_Bridge.exe

; Compressao dos dados do instalador
Compression=lzma2
SolidCompression=yes

; Onde o arquivo "Setup.exe" vai ser gerado
OutputDir=userdocs:GeoCAD_Setup

; Nome do instalador gerado
OutputBaseFilename=GeoCAD_Bridge_Instalador

; Permite ao instalador pular aviso se o app ja existir
SetupLogging=yes

[Files]
; Copia todo o conteudo da pasta gerada pelo PyInstaller para a pasta de instalacao
Source: "dist\GeoCAD_Bridge\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Atalho no Menu Iniciar
Name: "{group}\GeoCAD Bridge"; Filename: "{app}\GeoCAD_Bridge.exe"

; Atalho na Area de Trabalho
Name: "{autodesktop}\GeoCAD Bridge"; Filename: "{app}\GeoCAD_Bridge.exe"; Tasks: desktopicon

[Tasks]
; Opcao marcada por padrao no instalador para criar o atalho
Name: "desktopicon"; Description: "Criar um atalho na Area de Trabalho"; GroupDescription: "Atalhos:"
