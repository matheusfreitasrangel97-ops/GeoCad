import re
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QStandardItem

class LayerTreeBuilder:
    """
    Construtor e organizador da hierarquia lógica virtual de camadas CAD no QStandardItemModel.
    Converte uma lista plana de camadas do CAD em uma árvore agrupada por prefixos e separadores comuns.
    """

    @staticmethod
    def build_tree(tree_model, layers_data):
        """
        Popula o QStandardItemModel com a árvore hierárquica das camadas.
        layers_data: lista de tuplas (layer_name, geom_type, count)
        """
        # Limpa o modelo e redefine os cabeçalhos
        tree_model.clear()
        tree_model.setHorizontalHeaderLabels(["Camada", "Tipo", "Feições"])

        # Ordena as camadas alfabeticamente
        sorted_layers = sorted(layers_data, key=lambda x: x[0].upper())

        # Mapeia caminho (tupla de partes) -> QStandardItem da coluna 0
        nodes = {}

        # Expressão regular para encontrar os separadores: _ - . :
        split_pattern = re.compile(r"[_.:-]")

        for full_name, geom_type, count in sorted_layers:
            # Divide o nome da camada e remove partes vazias
            parts = [p for p in split_pattern.split(full_name) if p.strip()]
            if not parts:
                parts = [full_name]

            # Constrói cada nível da hierarquia
            for i in range(1, len(parts) + 1):
                path = tuple(parts[:i])
                if path not in nodes:
                    is_leaf = (i == len(parts))

                    if is_leaf:
                        # Nó folha (representa a camada CAD real)
                        row_item = QStandardItem(parts[-1])
                        row_item.setCheckable(True)
                        row_item.setCheckState(Qt.CheckState.Unchecked)
                        row_item.setData(full_name, Qt.ItemDataRole.UserRole)
                        row_item.setEditable(False)

                        type_item = QStandardItem(geom_type)
                        type_item.setEditable(False)

                        count_item = QStandardItem(f"{count:,}".replace(",", "."))
                        count_item.setEditable(False)
                    else:
                        # Nó grupo (agrupador virtual intermediário)
                        row_item = QStandardItem(parts[i - 1])
                        row_item.setCheckable(True)
                        row_item.setCheckState(Qt.CheckState.Unchecked)
                        row_item.setEditable(False)

                        type_item = QStandardItem("")
                        type_item.setEditable(False)

                        count_item = QStandardItem("0")
                        count_item.setEditable(False)

                    # Anexa ao pai correto
                    if i == 1:
                        tree_model.appendRow([row_item, type_item, count_item])
                    else:
                        parent_path = tuple(parts[:i - 1])
                        parent_node = nodes[parent_path]
                        parent_node.appendRow([row_item, type_item, count_item])

                    nodes[path] = row_item

        # Atualiza a contagem acumulada das feições para os grupos recursivamente
        def update_totals(item):
            if not item.hasChildren():
                # Se for folha, retorna o seu valor inteiro de feições
                try:
                    parent_item = item.parent()
                    if parent_item:
                        count_item = parent_item.child(item.row(), 2)
                    else:
                        count_item = tree_model.item(item.row(), 2)
                    val_str = count_item.text().replace(".", "")
                    return int(val_str)
                except Exception:
                    return 0

            total = 0
            child_count = item.rowCount()
            for r in range(child_count):
                child_col0 = item.child(r, 0)
                total += update_totals(child_col0)

            # Atualiza o rótulo de feições do próprio grupo
            parent_item = item.parent()
            if parent_item:
                count_item = parent_item.child(item.row(), 2)
            else:
                count_item = tree_model.item(item.row(), 2)

            if count_item:
                count_item.setText(f"{total:,}".replace(",", "."))

            return total

        # Roda a atualização para todos os nós de topo (raiz)
        for r in range(tree_model.rowCount()):
            root_item = tree_model.item(r, 0)
            if root_item:
                update_totals(root_item)
