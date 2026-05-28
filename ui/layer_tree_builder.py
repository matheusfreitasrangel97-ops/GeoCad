from PyQt6.QtCore import Qt
from PyQt6.QtGui import QStandardItem

class LayerTreeBuilder:
    """
    Construtor e organizador da hierarquia de camadas CAD no QStandardItemModel.
    Organiza as camadas na estrutura profissional: Tipo Geométrico -> Camada -> Feições.
    """

    @staticmethod
    def build_tree(tree_model, layers_data):
        """
        Popula o QStandardItemModel com a árvore hierárquica das camadas por tipo geométrico.
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
            root_item.setCheckState(Qt.CheckState.Checked)
            root_item.setEditable(False)

            type_item = QStandardItem("")
            type_item.setEditable(False)

            count_item = QStandardItem("0")
            count_item.setEditable(False)

            tree_model.appendRow([root_item, type_item, count_item])
            roots[key] = root_item

        # Ordena as camadas alfabeticamente pelo nome da camada
        sorted_layers = sorted(layers_data, key=lambda x: x[0].upper())

        for layer_name, geom_type, count in sorted_layers:
            root_node = roots.get(geom_type)
            if not root_node:
                continue

            # Nó da camada CAD real
            layer_item = QStandardItem(layer_name)
            layer_item.setCheckable(True)
            layer_item.setCheckState(Qt.CheckState.Checked)
            # Armazena a tupla (layer_name, geom_type) para identificação única no Lazy Loading e visibilidade
            layer_item.setData((layer_name, geom_type), Qt.ItemDataRole.UserRole)
            layer_item.setEditable(False)

            type_lbl = geom_name_map.get(geom_type, geom_type)
            type_item = QStandardItem(type_lbl)
            type_item.setEditable(False)

            count_item = QStandardItem(f"{count:,}".replace(",", "."))
            count_item.setEditable(False)

            # Cria um nó dummy "Carregando..." para possibilitar a expansão do nó da camada
            dummy_item = QStandardItem("Carregando...")
            dummy_item.setEditable(False)
            layer_item.appendRow([dummy_item])

            root_node.appendRow([layer_item, type_item, count_item])

        # Atualiza a contagem consolidada das feições para os grupos raiz
        for key, root_node in roots.items():
            total = 0
            for r in range(root_node.rowCount()):
                child_col0 = root_node.child(r, 0)
                if child_col0:
                    try:
                        # Busca o valor correspondente na coluna 2 (Feições) daquela linha
                        val_item = root_node.child(r, 2)
                        if val_item:
                            val_str = val_item.text().replace(".", "")
                            total += int(val_str)
                    except Exception:
                        pass

            # Atualiza o rótulo de feições do próprio grupo de topo
            root_row = root_node.row()
            root_count_item = tree_model.item(root_row, 2)
            if root_count_item:
                root_count_item.setText(f"{total:,}".replace(",", "."))
