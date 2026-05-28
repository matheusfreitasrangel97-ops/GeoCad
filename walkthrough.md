# GeoCad Standalone — Relatório de Entrega & Manual Técnico

Este documento resume a evolução e reestruturação do **GeoCad** para um ambiente autônomo, resiliente a falhas e de alta produtividade para usuários de GIS. O software agora roda fora do runtime do QGIS, utiliza o LibreDWG e processa arquivos CAD corrompidos ou estruturalmente inconsistentes sem interromper o fluxo de trabalho do usuário.

Adicionalmente, esta versão inclui as correções de visualização, seleção e exportação de camadas, a tradução total de comentários para Português Brasileiro (pt-BR), a inclusão de créditos e a reformulação completa do estilo visual para um tema híbrido claro/slate de alta legibilidade.

---

## 📂 1. Estrutura Modular Final

O projeto está organizado com uma arquitetura desacoplada e modular de pacotes:

```
workspace/
├── Solucoes_DWG.py      # Ponto de entrada (Bootstrap launcher)
├── requirements.txt      # Requisitos de ambiente standalone
├── build_spec.py         # Script de compilação PyInstaller
├── bin/                  # Binários do LibreDWG (empacotados no build)
│   ├── dwg2dxf.exe       # Executável do conversor LibreDWG
│   └── *.dll             # Bibliotecas de suporte DLL (C/C++ runtime)
├── utils/
│   └── logging_setup.py  # Logger rotativo integrado (pt-BR)
├── cad/
│   ├── converter.py      # Conversor silencioso DWG -> DXF via LibreDWG
│   └── parser.py         # Parser tolerante de DXF via ezdxf.recover (pt-BR)
├── gis/
│   ├── geometry_engine.py# Geometrias Shapely & Heurística de CRS (pt-BR)
│   └── exporter.py       # Gravador de Shapefiles via pyogrio/gpd (pt-BR)
├── render/
│   └── canvas.py         # Visualizador vetorial e QGraphicsView
├── workers/
│   └── parser_worker.py  # Worker assíncrono em QThread com auditoria (pt-BR)
└── ui/
    ├── main_window.py    # Controladora da Interface Principal com fallback (pt-BR)
    └── style.py          # Folha de estilo CSS (Tema escuro)
```

---

## 🛠️ 2. Correções Aplicadas & Melhorias Implementadas

1. **Modo de Recuperação do ezdxf (Recover Mode)**:
   * Substituímos o carregador de arquivos comum do ezdxf pela API `ezdxf.recover.readfile()`. Essa API analisa e corrige automaticamente a estrutura física do arquivo CAD na inicialização, corrigindo erros como ponteiros órfãos ou códigos de controle inválidos.
   * **Monkeypatch para Tabelas de Ordenação (`SORTENTSTABLE`)**: Arquivos CAD malformados podem conter códigos de ordenação inconsistentes nas tabelas de desenho do CAD. Implementamos um patch em runtime para `SortEntsTable.load_table` de forma a filtrar essas inconsistências de maneira silenciosa, evitando falhas físicas como `DXFStructureError: Invalid sort handle code 331, expected 5`.
2. **Proteção e Isolamento na Varredura**:
   * Envolvemos a leitura geométrica de cada entidade vetorial e sub-elementos de blocos (`INSERT`) em blocos de exceção `try-except` individuais. Se uma entidade específica estiver corrompida, ela é pulada e logada, mas a varredura continua normalmente.
   * **Correção de ValueError/TypeError em Polígonos Aninhados (`process_incoming_batch` / `get_chunk_coords`)**: Corrigimos o canvas para desempacotar recursivamente o primeiro ponto da casca externa.
3. **Consolidação de Visualização e Renderização Seletiva**:
   * **Correção de Chave Composta no Canvas**: Anteriormente, o visualizador agrupava chunks no canvas utilizando apenas as coordenadas espaciais `chunk_id` como chave. Caso uma camada contivesse múltiplos tipos geométricos (pontos e linhas) ou cores diferentes no mesmo local físico, seus caminhos vetoriais eram mesclados incorretamente e estilos eram sobrescritos. Implementamos uma chave composta `(chunk_id, geom_type, color)` em `process_incoming_batch()`.
   * **Sincronização de Estado com o Tree Model**: Quando novos lotes de geometria são gerados incrementalmente em segundo plano pela thread de importação, o canvas agora verifica dinamicamente a propriedade `tree_model` da janela principal para certificar-se de que a camada está ativa (marcada). Se estiver desmarcada, o item gráfico correspondente é imediatamente criado oculto, garantindo que o visualizador renderize **apenas** camadas ativas.
   * **Salvaguarda de Coluna na Escuta de Sinais**: Protegemos a conexão `itemChanged` em `ui/main_window.py` para ignorar qualquer evento que não seja de alteração do checkbox da coluna 0 (a coluna que contém a caixa de seleção da camada), prevenindo ciclos infinitos ou overheads.
4. **Controle Seletivo sob Filtro de Busca**:
   * O comportamento dos botões "Selecionar Todas" e "Desmarcar Todas" foi refinado. Em vez de operar sobre o modelo bruto (`tree_model`), eles agora operam sobre as linhas visíveis do `proxy_model`. Se você realizar uma pesquisa na barra de pesquisa (ex: filtrando por "eletrica") e clicar em "Desmarcar Todas", apenas as camadas que atendem a esse critério de busca serão desmarcadas.
5. **Zoom Focado Seguro**:
   * Ajustamos a ação de clique direito no menu da árvore de camadas para `"🔍 Direcionar Zoom para a Camada"`.
   * Corrigimos o cálculo do bounding box unificado no canvas para aplicar uma margem de padding de segurança (mínimo de 10 unidades de extensão física) caso a camada possua dimensões puntiformes (apenas pontos ou linhas microscópicas), evitando erros de viewport ou zoom infinito.
6. **Exportação Estrita de Selecionados**:
   * O botão "Exportar Shapefiles" filtra os objetos vetoriais com precisão comparando o atributo `"layer"` das feições contra o conjunto de camadas que possuem caixa de seleção ativa (`Qt.CheckState.Checked`) no modelo da árvore. Camadas desmarcadas são completamente omitidas do processo de escrita física, não gerando nenhum arquivo Shapefile no diretório de destino.
7. **Tema Híbrido Claro/Slate Moderno e Correção de Diálogos**:
   * Substituímos o estilo antigo (escuro neon) por uma folha de estilos limpa e de alto contraste em tons claros e cinza-slate (azul-acinzentado). A janela do programa agora possui fundo cinza claro (`#f3f4f6`) com a barra lateral em branco puro (`#ffffff`) e textos em grafite escuro (`#1f2937`), garantindo extrema legibilidade.
   * **Correção de Legibilidade do QMessageBox (Cinza no Branco)**: Solucionamos o vazamento de cor que deixava as letras dos avisos do sistema cinzas sobre fundo branco. A folha de estilo agora formata as janelas `QMessageBox` explicitamente com texto escuro e botões contornados legíveis.
   * **Visualizador Técnico Confortável**: Mantivemos o fundo interno do canvas de desenho vetorial como escuro (`#0b0c10`), pois desenhos de engenharia CAD utilizam linhas amarelas, cianas e brancas que seriam completamente invisíveis em uma tela branca. Essa abordagem híbrida é o padrão de mercado adotado por softwares como AutoCAD e QGIS.
8. **Créditos do Criador Integrados**:
   * Adicionamos a assinatura do criador no rodapé da barra lateral: `"Criado por Matheus Freitas Rangel Contato (51)997903841"`, perfeitamente alinhada e integrada ao layout.
9. **Sweep Completo para Português Brasileiro (pt-BR)**:
   * Varremos todos os arquivos da aplicação (`Solucoes_DWG.py`, `render/canvas.py`, `ui/main_window.py`, etc.) traduzindo todos os comentários de desenvolvimento, anotações de código e documentações (`docstrings`) remanescentes em inglês para o Português do Brasil de forma definitiva.

---

## 📐 3. Explicação da Arquitetura Final

O sistema opera com um padrão híbrido **MVC/MVVM** assíncrono que protege a responsividade da interface gráfica:

* **Camada de Interface (View)**: O arquivo `ui/main_window.py` renderiza o painel de camadas e controle.
* **Motor de Visualização (Render)**: `render/canvas.py` agrupa geometrias vetoriais em lotes e cria mega-caminhos por células de grade, otimizando o redesenho e a velocidade do canvas.
* **Controlador de Trabalho (Worker)**: `workers/parser_worker.py` roda em uma thread dedicada (`QThread`) e monitora o gerador do parser DXF em tempo real, informando o console e a barra de progresso.
* **Motor de Dados (Model/GIS)**: `gis/geometry_engine.py` trata as coordenadas CAD e avalia as projeções do arquivo. `gis/exporter.py` recebe a lista original do worker e grava os Shapefiles organizados em pontos, linhas e polígonos.

---

## ⚠️ 4. Relatório de Limitações Técnicas

* **Formato CAD/DWG R2018+**: O conversor LibreDWG 0.13.4 integrado suporta leitura e conversão de arquivos de desenho criados até o formato AutoCAD R2018 (AutoCAD 2018 a 2026).
* **Limitações de Shapefiles**: Limite de tamanho de arquivo de até 2GB e limite de 10 caracteres para nomes de atributos do banco de dados do DBF.

---

## 📦 5. Instruções de Compilação do Executável Standalone

### Passo 1: Instalação das Dependências no Ambiente Python Standalone
```powershell
pip install -r requirements.txt
```

### Passo 2: Executar o Script de Compilação
```powershell
python build_spec.py
```

### Passo 3: Executável Gerado
Após o término, o executável final **`GeoCad.exe`** estará disponível na pasta **`dist/`** na raiz do projeto.

---

## 🎓 6. Guia Didático de Customização de Design e UI em PyQt6

Para que você possa evoluir e ajustar a interface do GeoCad por conta própria, reunimos aqui os principais conceitos e exemplos práticos de como a UI é estruturada neste projeto.

### 6.1 Como Funcionam os Layouts (Estrutura Física)
No PyQt, os elementos visuais (botões, campos de texto, tabelas) são posicionados utilizando layouts gerenciadores de espaço. Os mais comuns são:
* **`QVBoxLayout`**: Organiza elementos verticalmente (de cima para baixo).
* **`QHBoxLayout`**: Organiza elementos horizontalmente (da esquerda para a direita).
* **`QGridLayout`**: Organiza elementos em uma grade bidimensional (linhas e colunas).

**Exemplo de Hierarquia Usado na Sidebar**:
```python
sidebar_layout = QVBoxLayout(sidebar_widget) # Cria o layout vertical principal da barra lateral

# 1. Adiciona o título e descrição
sidebar_layout.addWidget(title_lbl) 
sidebar_layout.addWidget(desc_lbl)

# 2. Adiciona o botão de carregar desenho
sidebar_layout.addWidget(self.btn_load)

# 3. Adiciona uma seção horizontal para os botões de seleção em massa
selection_btns_layout = QHBoxLayout() # Novo layout horizontal
selection_btns_layout.addWidget(self.btn_select_all)
selection_btns_layout.addWidget(self.btn_unselect_all)

# Adiciona o layout horizontal de botões dentro do layout vertical da sidebar
sidebar_layout.addLayout(selection_btns_layout)
```
> [!TIP]
> Se quiser adicionar um novo elemento visível na sidebar (como um novo botão), basta criá-lo e chamar `sidebar_layout.addWidget(seu_elemento)` ou inseri-lo em uma linha de layout horizontal específica.

---

### 6.2 O Sistema de Estilos (CSS do Qt - QSS)
As cores, bordas, fontes e efeitos visuais são configurados no arquivo `ui/style.py` usando regras idênticas ao CSS padrão de páginas web.

**Principais propriedades que você pode alterar no arquivo `ui/style.py`**:
* **`background-color`**: Altera a cor de fundo do elemento.
* **`color`**: Altera a cor do texto.
* **`border`**: Define bordas (ex: `1px solid #cbd5e1`).
* **`border-radius`**: Define cantos arredondados (ex: `6px`).
* **`font-family`** e **`font-size`**: Controlam a tipografia e o tamanho do texto.

**Evitando "Texto Cinza no Fundo Branco" em Caixas de Diálogo**:
Para evitar que diálogos como `QMessageBox` herdem cores cinza claro de janelas escuras e fiquem ilegíveis, definimos regras de estilo dedicadas:
```css
QMessageBox {
    background-color: #ffffff; /* Fundo branco fixo para o aviso */
}
QMessageBox QLabel {
    color: #1f2937;            /* Texto cinza-escuro/grafite de alto contraste */
    font-size: 13px;
}
QMessageBox QPushButton {
    background-color: #ffffff;
    color: #0f766e;
    border: 1.5px solid #cbd5e1;
    border-radius: 4px;
}
```

---

### 6.3 Conectando Ações: Sinais e Slots (Signals & Slots)
O PyQt6 utiliza o mecanismo de **Signals** (eventos disparados) e **Slots** (funções que respondem ao evento) para conectar a lógica de código ao clique do usuário.

**Conectando o Clique de um Botão**:
```python
# Conecta o sinal clicked do botão à função de abrir arquivo na janela principal
self.btn_load.clicked.connect(self.open_file)
```

**Conectando o Clique Direito (Menu de Contexto) no TreeView**:
Para criar um menu flutuante quando o usuário clica com o botão direito sobre um item:
1. Define a política de menu de contexto customizado no widget:
   ```python
   self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
   ```
2. Conecta o sinal `customContextMenuRequested` à função tratadora:
   ```python
   self.tree_view.customContextMenuRequested.connect(self.show_layer_context_menu)
   ```
3. Na função, identifica o item selecionado e exibe o menu:
   ```python
   def show_layer_context_menu(self, position):
       index = self.tree_view.indexAt(position) # Posição do clique
       if not index.isValid():
           return
       
       # Cria o menu de pop-up flutuante
       menu = QMenu(self)
       
       # Cria uma ação do menu com seu texto e conecta sua resposta
       zoom_action = QAction("🔍 Zoom para layer", self)
       zoom_action.triggered.connect(lambda: self.zoom_to_layer(layer_name))
       menu.addAction(zoom_action)
       
       # Executa o menu na tela nos limites reais da janela do mouse
       menu.exec(self.tree_view.viewport().mapToGlobal(position))
   ```

---

### 6.4 Entendendo Modelos de Dados (Model/View e Proxy)
Para listas e árvores de camadas, este projeto utiliza o paradigma **Model/View** do Qt:
1. **`QStandardItemModel` (tree_model)**: É o banco de dados interno da tabela de camadas. Armazena os textos, valores numéricos e se o checkbox está marcado ou não.
2. **`QSortFilterProxyModel` (proxy_model)**: Fica "no meio do caminho" entre o banco de dados e a tela. Ele filtra as linhas exibidas com base na busca digitada na caixa de texto.
3. **`QTreeView` (tree_view)**: É o componente de tela que apenas renderiza o que o `proxy_model` deixa passar.

**Trabalhando com Índices sob Filtro**:
Quando a barra de busca está ativa, clicar na tela retorna um índice relativo ao que está sendo visto na tela (o `proxy_model`). Para obter o item real na lista original, você deve mapeá-lo:
```python
# 1. Pega o índice correspondente à linha clicada
index = self.tree_view.currentIndex()

# 2. Converte o índice do modelo visual (filtrado) para o modelo real de dados
source_index = self.proxy_model.mapToSource(index)

# 3. Recupera o item real a partir do índice real convertido
item = self.tree_model.itemFromIndex(source_index)
```
Seguindo este guia prático, você terá total autonomia para criar novos botões, alterar comportamentos de filtragem, trocar cores e reajustar o tamanho dos painéis da interface.
