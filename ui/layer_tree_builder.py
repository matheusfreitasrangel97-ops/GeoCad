from PyQt6.QtCore import Qt
from PyQt6.QtGui import QStandardItem

class LayerTreeBuilder:
    """
    Construtor e organizador da hierarquia de camadas CAD no QStandardItemModel.
    Organiza as camadas na estrutura: Tipo Geométrico -> Camada.
    """

    @staticmethod
    def build_tree(tree_model, layers_data):
        """
        Popula o QStandardItemModel com os nós raiz (tipos geométricos) e nós dummy.
        layers_data: lista de tuplas (layer_name, geom_type, count)
        """
        # Limpa o modelo e redefine os cabeçalhos
        tree_model.clear()
        tree_model.setHorizontalHeaderLabels(["Camada", "Tipo", "Feições"])

        # Mapeamento de tipos geométricos para nomes amigáveis em português
        geom_name_map = {
            "Point": "Pontos",
            "LineString": "Linhas",
            "Polygon": "Polígonos",
            "Text": "Textos"
        }

        # Cria os 4 nós raiz estáticos e os adiciona ao modelo
        roots = {}
        for key, name in geom_name_map.items():
            root_item = QStandardItem(f"📁 {name}")
            root_item.setCheckable(True)
            root_item.setCheckState(Qt.CheckState.Unchecked)
            # Armazena o tipo geométrico no nó raiz para identificação no lazy loading
            root_item.setData(key, Qt.ItemDataRole.UserRole)
            root_item.setEditable(False)

            type_item = QStandardItem("")
            type_item.setEditable(False)

            count_item = QStandardItem("0")
            count_item.setEditable(False)

            tree_model.appendRow([root_item, type_item, count_item])
            roots[key] = root_item

            # Cria um nó dummy "Carregando..." sob a raiz para habilitar a expansão na árvore
            dummy_item = QStandardItem("Carregando...")
            dummy_item.setEditable(False)
            dummy_type = QStandardItem("")
            dummy_type.setEditable(False)
            dummy_count = QStandardItem("")
            dummy_count.setEditable(False)
            root_item.appendRow([dummy_item, dummy_type, dummy_count])

        # Atualiza a contagem consolidada das feições para os grupos raiz a partir de layers_data
        for key, root_node in roots.items():
            total = sum(count for _, g_type, count in layers_data if g_type == key)
            
            root_row = root_node.row()
            root_count_item = tree_model.item(root_row, 2)
            if root_count_item:
                root_count_item.setText(f"{total:,}".replace(",", "."))

    @staticmethod
    def populate_layer_nodes(root_node, geom_type, layers_data):
        """
        Popula sob demanda as camadas correspondentes sob o nó raiz expandido.
        layers_data: lista completa de tuplas (layer_name, geom_type, count)
        """
        geom_name_map = {
            "Point": "Pontos",
            "LineString": "Linhas",
            "Polygon": "Polígonos",
            "Text": "Textos"
        }

        # Filtra as camadas deste tipo geométrico
        filtered = [item for item in layers_data if item[1] == geom_type]
        # Ordena alfabeticamente
        sorted_layers = sorted(filtered, key=lambda x: x[0].upper())

        for layer_name, g_type, count in sorted_layers:
            # Nó da camada CAD real
            layer_item = QStandardItem(layer_name)
            layer_item.setCheckable(True)
            layer_item.setCheckState(Qt.CheckState.Unchecked)
            # Armazena a tupla (layer_name, geom_type) para identificação única
            layer_item.setData((layer_name, geom_type), Qt.ItemDataRole.UserRole)
            layer_item.setEditable(False)

            type_lbl = geom_name_map.get(geom_type, geom_type)
            type_item = QStandardItem(type_lbl)
            type_item.setEditable(False)

            count_item = QStandardItem(f"{count:,}".replace(",", "."))
            count_item.setEditable(False)

            root_node.appendRow([layer_item, type_item, count_item])
