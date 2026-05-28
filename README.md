# GeoCad

> Solução profissional para conversão e visualização de desenhos vetoriais CAD (DWG/DXF) para arquivos GIS (Shapefiles).

![Status do Projeto](https://img.shields.io/badge/Status-Ativo-success?style=for-the-badge)
![Versão](https://img.shields.io/badge/Versão-0.1.0-blue?style=for-the-badge)
![Licença](https://img.shields.io/badge/Licença-MIT-green?style=for-the-badge)

---

## 📌 Descrição do Software

O **GeoCad** é um software desktop intuitivo projetado para preencher a lacuna entre ferramentas de CAD e Sistemas de Informação Geográfica (GIS). Ele simplifica a importação de desenhos vetoriais complexos do AutoCAD, permitindo a leitura e o processamento de entidades geométricas para conversão rápida e exportação para formatos geoespaciais abertos, preservando camadas, comprimentos, áreas e atributos espaciais.

---

## 🎯 Objetivo do Projeto

O objetivo principal do GeoCad é fornecer um ecossistema leve, rápido e resiliente para:
1. **Importar arquivos de CAD (DWG e DXF)** de forma segura e tolerante a falhas.
2. **Visualizar os dados vetoriais** em um canvas interativo com suporte a pan, zoom e seleção de feições.
3. **Exibir informações hierárquicas de camadas** permitindo a filtragem visual rápida.
4. **Gerar arquivos Shapefiles (.shp)** estruturados contendo informações tabulares, CRS e atributos das geometrias convertidas.
5. **Oferecer um ambiente desktop empacotado** que dispense configurações complexas de bibliotecas externas por parte do usuário final.

---

## ✨ Funcionalidades

* 🚀 **Conversão Silenciosa de DWG para DXF:** Integração transparente com o utilitário LibreDWG para decodificar DWGs proprietários automaticamente.
* 🛡️ **Motor de Leitura Tolerante (ezdxf.recover):** Mecanismo resiliente que tenta corrigir e auditar automaticamente arquivos CAD inconsistentes ou corrompidos.
* 🎨 **Visualizador Vetorial (Canvas):** Renderização ágil das entidades de CAD (Pontos, Linhas, Polígonos e Textos) com renderizador customizado PyQt6.
* 📋 **Tabela de Atributos Dinâmica:** Visualização instantânea de handles, camadas e propriedades geométricas detalhadas de feições selecionadas no canvas.
* 🌳 **Hierarquia e Filtro de Camadas:** Árvore de camadas interativa que suporta marcação recursiva, buscas e toggle de visibilidade em lote.
* 💾 **Exportação GIS Robusta:** Conversão direta das feições de CAD para o formato ESRI Shapefile com criação automatizada de metadados de CRS e suporte a geoprocessamento.

---

## 📷 Captura de Tela (Interface Principal)

*(Espaço reservado para capturas de tela do software)*
```
+-----------------------------------------------------------------+
| GeoCad v0.1.0                                                   |
+-----------------------------------+-----------------------------+
| [ Carregar DWG / DXF ]            |                             |
|                                   |                             |
| CRS Status: SIRGAS 2000 / UTM 23S |                             |
|                                   |                             |
| [🔍 Filtrar camadas...]            |         CANVAS DE           |
|                                   |         PREVIEW             |
| [+] Camada 0                      |         VETORIAL            |
|  [x] Pontos                       |         INTERATIVO          |
|  [x] Linhas                       |                             |
|                                   |                             |
| [Barra de Progresso (Logs)  100%] |                             |
|                                   |                             |
| [ Exportar Shapefiles ]           | [✋ Nav] [🖱️ Sel] [🚫 Desf]  |
+-----------------------------------+-----------------------------+
```

---

## 🛠️ Tecnologias Utilizadas

* **Linguagem Principal:** Python 3.12+
* **Interface Gráfica (GUI):** PyQt6
* **Processamento de CAD:** ezdxf (com recover API)
* **Processamento Geocad/GIS:** Shapely, PyProj, GeoPandas, PyOgrio
* **Compilação e Empacotamento:** PyInstaller / Inno Setup
* **Conversor de DWG Integrado:** LibreDWG (dwg2dxf)

---

## 🚀 Como Executar (Ambiente de Desenvolvimento)

### Requisitos Prévios
* Python instalado (preferencialmente versão 3.10 ou superior).
* Executável `dwg2dxf.exe` presente no subdiretório `bin/`.

### Configuração do Ambiente
1. Clone o repositório oficial:
   ```bash
   git clone https://github.com/matheusfreitasrangel97-ops/GeoCad.git
   cd GeoCad
   ```
2. Crie e ative um ambiente virtual:
   ```bash
   python -m venv .venv
   # No Windows:
   .venv\Scripts\activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
4. Execute o GeoCad:
   ```bash
   python main.py
   ```

---

## 📦 Como Compilar (.exe Standalone)

O GeoCad pode ser empacotado em um executável autônomo para facilitar o uso final sem a necessidade de instalar interpretadores de Python.

### Usando o Script em Lote (Windows)
Basta dar dois cliques ou executar no terminal o arquivo `build.bat`:
```bash
build.bat
```
Ele executará o compilador e deixará o aplicativo portátil pronto para uso na pasta `dist/GeoCad`.

### Compilando via Python
Você também pode rodar o compilador customizado que gerencia o processo programaticamente:
```bash
python build_spec.py
```
Isso gerará o executável standalone de arquivo único no diretório `dist/`.

---

## 📂 Estrutura do Projeto

Abaixo está a árvore organizada do repositório:

```
GeoCad/
│
├── bin/                 # Utilitários binários (ex: dwg2dxf.exe)
├── build/               # Arquivos intermediários de compilação (gerados pelo PyInstaller)
├── cad/                 # Módulo de manipulação de CAD (parser, conversores)
├── config/              # Configurações globais e de atualização
├── dist/                # Executável gerado após a compilação final
├── docs/                # Documentação técnica e manuais de desenvolvimento
├── gis/                 # Módulo de processamento GIS (exporter, geometry engine)
├── logs/                # Histórico de registros de execução da aplicação
├── releases/            # Snapshots e versões empacotadas oficiais
├── render/              # Visualização gráfica (Canvas 2D, estilos)
├── tests/               # Conjunto de testes unitários e de integração
├── ui/                  # Componentes de interface e folhas de estilo (PyQt6)
├── updater/             # Arquitetura prevista para rotinas de auto-update
├── workers/             # Processamento assíncrono em segundo plano (QThread)
│
├── .gitignore           # Filtros de arquivos ignorados no controle de versão
├── CHANGELOG.md         # Registro cronológico de alterações do sistema
├── GeoCad.spec          # Arquivo de configuração de build do PyInstaller
├── LICENSE              # Termos de uso e licenciamento do projeto
├── build.bat            # Script rápido de compilação em ambiente Windows
├── build_spec.py        # Compilador python para empacotamento
├── installer.iss        # Script de geração do instalador final (Inno Setup)
├── main.py              # Ponto de entrada do sistema
├── requirements.txt     # Dependências obrigatórias de execução
└── requirements-dev.txt # Dependências específicas para desenvolvimento
```

---

## 👥 Como Contribuir

Seja bem-vindo a contribuir com o GeoCad! Siga estes passos para propor melhorias:

1. Realize um Fork do projeto.
2. Crie uma branch de funcionalidade a partir da branch `dev` (ex: `git checkout -b feature/minha-melhoria`).
3. Faça commit de suas alterações respeitando o padrão de commits.
4. Faça o push para a branch correspondente no seu Fork (`git push origin feature/minha-melhoria`).
5. Abra um Pull Request direcionado à branch `dev` deste repositório original.

---

## 🔀 Fluxo Git e Versionamento Seguro

Para garantir a estabilidade do produto em produção, adotamos o seguinte fluxo:

* **`main` (branch principal):** Apenas código testado e versões totalmente estáveis em produção. Nunca faça commits diretos aqui.
* **`dev` (branch de desenvolvimento):** Branch ativa onde novas funcionalidades e correções de bugs são unificadas e testadas antes do merge na main.
* **Tags Semânticas (`vX.Y.Z`):** Cada versão estável finalizada na branch `main` deve receber uma tag correspondente (ex: `v0.1.0`), que gerará automaticamente as releases históricas do software.

Para mais detalhes sobre comandos, branches e commits, leia o [Guia de Fluxo de Trabalho Git](file:///c:/Users/estagiario/.gemini/antigravity-ide/scratch/QFieldLiteWorkspace/docs/git_workflow.md).

---

## 📝 Histórico de Versões

Veja o histórico detalhado de cada lançamento em nosso [CHANGELOG.md](file:///c:/Users/estagiario/.gemini/antigravity-ide/scratch/QFieldLiteWorkspace/CHANGELOG.md).

---

## ⚖️ Licença

Este projeto está licenciado sob a Licença MIT - consulte o arquivo [LICENSE](file:///c:/Users/estagiario/.gemini/antigravity-ide/scratch/QFieldLiteWorkspace/LICENSE) para obter detalhes.
