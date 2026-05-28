[Setup]
; =======================================================
; Script Inno Setup para o GeoCad
; =======================================================

; Informacoes do Aplicativo
AppName=GeoCad
AppVersion=0.1.0
AppPublisher=Matheus Freitas Rangel
AppSupportURL=matheus-freitas-rangel@hotmail.com

; Diretorio de Instalacao (Arquivos de Programas)
DefaultDirName={autopf}\GeoCad

; Pasta no Menu Iniciar
DefaultGroupName=GeoCad

; Icone exibido no desinstalador (opcional, ele puxa do proprio .exe se omitido)
UninstallDisplayIcon={app}\GeoCad.exe

; Compressao dos dados do instalador
Compression=lzma2
SolidCompression=yes

; Onde o arquivo "Setup.exe" vai ser gerado
OutputDir=userdocs:GeoCad_Setup

; Nome do instalador gerado
OutputBaseFilename=GeoCad_Instalador

; Permite ao instalador pular aviso se o app ja existir
SetupLogging=yes

[Files]
; Copia todo o conteudo da pasta gerada pelo PyInstaller para a pasta de instalacao
Source: "dist\GeoCad\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Atalho no Menu Iniciar
Name: "{group}\GeoCad"; Filename: "{app}\GeoCad.exe"

; Atalho na Area de Trabalho
Name: "{autodesktop}\GeoCad"; Filename: "{app}\GeoCad.exe"; Tasks: desktopicon

[Tasks]
; Opcao marcada por padrao no instalador para criar o atalho
Name: "desktopicon"; Description: "Criar um atalho na Area de Trabalho"; GroupDescription: "Atalhos:"
