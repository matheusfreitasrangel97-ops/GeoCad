"""
Estado Central de Renderização — Fonte Única de Verdade.

Concentra TODO o estado de visualização para evitar duplicação
entre canvas, árvore de camadas, menu contextual e toolbar.

Nenhum outro módulo deve manter estado de visibilidade ou seleção próprio.
Canvas, TreeView, MenuContextual e Toolbar CONSULTAM este objeto.

Este módulo NÃO depende de Qt. É um objeto Python puro e leve.
"""


class RenderState:
    """
    Estado centralizado do motor gráfico.

    Responsabilidades:
        - Rastrear quais camadas estão visíveis
        - Rastrear quais camadas possuem rótulos ativos
        - Rastrear quais feições (handles) estão selecionadas
        - Rastrear o modo de interação atual (navegação ou seleção)

    Regras:
        - Este é o ÚNICO lugar onde esses estados existem.
        - O canvas lê este estado para decidir o que renderizar.
        - A UI modifica este estado via métodos do canvas.
        - Nenhum componente deve duplicar esta informação.
    """

    __slots__ = (
        "visible_layers",
        "visible_labels",
        "selected_handles",
        "render_mode",
    )

    def __init__(self):
        self.visible_layers = set()       # Nomes de camadas geométricas visíveis
        self.visible_labels = set()       # Nomes de camadas com rótulos ativos
        self.selected_handles = set()     # Handles CAD de feições selecionadas
        self.render_mode = "navigation"   # "navigation" ou "selection"

    # ──── Camadas Geométricas ────

    def is_layer_geom_visible(self, name, geom_type):
        """Verifica se uma combinação de camada e tipo geométrico está visível."""
        return (name, geom_type) in self.visible_layers

    def set_layer_geom_visible(self, name, geom_type, visible):
        """Define a visibilidade de uma combinação de camada e tipo geométrico."""
        if visible:
            self.visible_layers.add((name, geom_type))
        else:
            self.visible_layers.discard((name, geom_type))

    # ──── Rótulos (Labels) ────

    def is_labels_visible(self, name):
        """Verifica se os rótulos de uma camada estão ativos."""
        return name in self.visible_labels

    def set_labels_visible(self, name, visible):
        """Define a visibilidade dos rótulos de uma camada."""
        if visible:
            self.visible_labels.add(name)
        else:
            self.visible_labels.discard(name)

    def set_all_labels_visible(self, layer_names, visible):
        """Liga ou desliga rótulos de todas as camadas fornecidas."""
        if visible:
            self.visible_labels.update(layer_names)
        else:
            self.visible_labels.clear()

    # ──── Seleção Espacial ────

    def select_handles(self, handles, additive=False):
        """Seleciona feições pelos seus handles CAD."""
        if not additive:
            self.selected_handles.clear()
            self.selected_handles.update(handles)
        else:
            for h in handles:
                if h in self.selected_handles:
                    self.selected_handles.discard(h)
                else:
                    self.selected_handles.add(h)

    def clear_selection(self):
        """Limpa toda a seleção de feições."""
        self.selected_handles.clear()

    def is_selected(self, handle):
        """Verifica se uma feição está selecionada."""
        return handle in self.selected_handles

    # ──── Modo de Interação ────

    def set_mode(self, mode):
        """Define o modo de interação: 'navigation' ou 'selection'."""
        self.render_mode = mode

    def is_selection_mode(self):
        """Verifica se o modo de seleção espacial está ativo."""
        return self.render_mode == "selection"

    # ──── Reset ────

    def reset(self):
        """Reseta todo o estado de renderização para o padrão inicial."""
        self.visible_layers.clear()
        self.visible_labels.clear()
        self.selected_handles.clear()
        self.render_mode = "navigation"
