# Changelog

Todos os registros de alterações relevantes para este projeto serão documentados neste arquivo.

O formato é baseado no [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/) e este projeto segue o padrão de [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [0.1.0] - 2026-05-28
### Adicionado
- **Conversão Silenciosa DWG:** Processamento automático em segundo plano do LibreDWG para decodificar DWGs.
- **Visualização Vetorial:** Renderizador interativo PyQt6 (Canvas 2D) para visualizar Pontos, Linhas, Polígonos e Textos CAD.
- **Seleção Espacial de Feições:** Ferramenta interativa de seleção de geometrias no Canvas com tabela dinâmica de atributos.
- **Hierarquia de Camadas:** Árvore interativa de camadas com suporte a toggle de visibilidade em cascata e filtro textual.
- **Exportação Shapefile:** Geração automatizada de múltiplos Shapefiles ESRI contendo tabelas de atributos e o CRS detectado correspondente.
- **Estruturação de Logs:** Buffer de console de logs circular integrado à barra de progresso.

---

## [0.2.0] - Em Planejamento
### Adicionado
- Preparação de rotinas para auto-updater.
- Pipeline de testes automatizados unitários no pacote `/tests`.
- Sistema de compilação aprimorado (`build.bat`, `build_spec.py` e `GeoCad.spec`) unificado sob o script principal `main.py`.
