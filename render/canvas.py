"""
Motor Visual Vetorial de Alta Performance — GeoCAD Bridge.

Princípios arquiteturais:
    - ChunkGraphicsItem: mega-path contendo milhares de geometrias em paint()
    - LabelChunkItem: texto manual via painter.drawText() — NUNCA QPainterPath.addText()
    - RenderState: fonte única de verdade para visibilidade/seleção/modo
    - Zero Shapely no loop de renderização
    - Seleção incremental: apenas altera estado visual, nunca reconstrói cena
    - fitInView controlado: apenas ao final do carregamento ou ação do usuário
"""

import logging
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPathItem,
    QGraphicsItem, QRubberBand, QGraphicsRectItem
)
from PyQt6.QtGui import (
    QPainter, QPainterPath, QPen, QBrush, QColor, QFont
)

from render.state import RenderState

logger = logging.getLogger("geocad_bridge.render.canvas")


# ═══════════════════════════════════════════════════════
# Item Gráfico de Geometrias (Mega-Path)
# ═══════════════════════════════════════════════════════

class ChunkGraphicsItem(QGraphicsPathItem):
    """
    Item gráfico que consolida MILHARES de geometrias em um único QPainterPath.
    Desenhado inteiramente em paint() com otimização LOD.

    Cada instância representa um fragmento espacial (chunk) de uma camada,
    podendo conter centenas ou milhares de polilinhas, pontos ou polígonos.

    NUNCA deve existir um QGraphicsPathItem por feição individual.
    """

    def __init__(self, path, layer_name, chunk_id, geom_type, color_hex, parent=None):
        super().__init__(path, parent)
        self.layer_name = layer_name
        self.chunk_id = chunk_id
        self.geom_type = geom_type
        self.color_hex = color_hex

        # Desabilita processamento de eventos desnecessários para performance
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        # Configura estilo padrão com base no tipo geométrico
        color = QColor(color_hex)

        if geom_type in ("Point", "Text"):
            self._default_pen = QPen(color, 0.5)
            self._default_brush = QBrush(color)
        elif geom_type == "Polygon":
            self._default_pen = QPen(color, 1.0)
            fill_color = QColor(color.red(), color.green(), color.blue(), 50)
            self._default_brush = QBrush(fill_color)
        else:  # LineString
            pen = QPen(color, 1.0)
            pen.setCosmetic(True)  # Espessura constante independente do zoom
            self._default_pen = pen
            self._default_brush = QBrush()

        self.setPen(self._default_pen)
        self.setBrush(self._default_brush)

        # Flag de highlight para seleção (evita criar novos objetos Qt)
        self._highlighted = False

    def paint(self, painter, option, widget=None):
        """Renderização com otimização de Nível de Detalhe (LOD)."""
        from PyQt6.QtWidgets import QStyleOptionGraphicsItem
        lod = QStyleOptionGraphicsItem.levelOfDetailFromTransform(painter.worldTransform())

        # LOD ultra-baixo: desenha apenas bounding box como proxy visual
        if lod < 0.08:
            rect = self.boundingRect()
            painter.setPen(self.pen())
            painter.drawRect(rect)
        else:
            # Renderização padrão do mega-path consolidado
            super().paint(painter, option, widget)


# ═══════════════════════════════════════════════════════
# Item Gráfico de Rótulos (Texto Manual)
# ═══════════════════════════════════════════════════════

class LabelChunkItem(QGraphicsItem):
    """
    Item gráfico dedicado a rótulos de texto.
    Desenha texto MANUALMENTE com painter.drawText() para máxima performance.

    PROIBIDO:
        - QPainterPath.addText()   → cria path complexo por caractere
        - QGraphicsTextItem        → overhead massivo por instância

    CORRETO:
        - painter.drawText(QPointF, str) → desenho direto, sem alocação

    LOD integrado: labels invisíveis em zoom distante.
    """

    def __init__(self, layer_name, chunk_id, parent=None):
        super().__init__(parent)
        self.layer_name = layer_name
        self.chunk_id = chunk_id

        # Armazena rótulos como tuplas leves — zero objetos Qt por rótulo
        self._labels = []  # [(x, y, texto), ...]
        self._bounding_rect = QRectF()

        # Estilo de texto fixo (reutilizado entre paint calls)
        self._font = QFont("Segoe UI", 7)
        self._color = QColor("#94a3b8")  # Cinza azulado suave

        # Desabilita interação de mouse — labels não são clicáveis
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def add_labels(self, label_data):
        """
        Adiciona rótulos ao chunk de forma incremental.
        label_data: lista de tuplas [(x, y, texto), ...]
        """
        self._labels.extend(label_data)
        self._recalc_bounds()
        self.prepareGeometryChange()

    def _recalc_bounds(self):
        """Recalcula o retângulo delimitador com margem para texto."""
        if not self._labels:
            self._bounding_rect = QRectF()
            return

        xs = [lb[0] for lb in self._labels]
        ys = [lb[1] for lb in self._labels]

        # Margem proporcional ao comprimento máximo do texto
        max_text_len = max((len(str(lb[2])) for lb in self._labels), default=5)
        margin_right = max_text_len * 5.0  # ~5 unidades de cena por caractere
        font_height = 10.0  # Margem vertical generosa

        self._bounding_rect = QRectF(
            min(xs) - 2.0,
            min(ys) - font_height,
            (max(xs) - min(xs)) + margin_right + 4.0,
            (max(ys) - min(ys)) + font_height * 2.0
        )

    def boundingRect(self):
        """Retângulo delimitador usado pelo scene para culling e clipping."""
        return self._bounding_rect

    def paint(self, painter, option, widget=None):
        """
        Renderização manual de texto com LOD.
        Labels aparecem APENAS com zoom suficiente (lod >= 0.3).
        """
        from PyQt6.QtWidgets import QStyleOptionGraphicsItem
        lod = QStyleOptionGraphicsItem.levelOfDetailFromTransform(painter.worldTransform())

        # Labels ocultos em zoom distante — performance é prioridade
        if lod < 0.3:
            return

        painter.setFont(self._font)
        painter.setPen(self._color)

        # Desenho manual: zero alocação por iteração
        for x, y, text in self._labels:
            painter.drawText(QPointF(x, y), str(text))


# ═══════════════════════════════════════════════════════
# Motor Visual Principal (QGraphicsView)
# ═══════════════════════════════════════════════════════

class CADPreviewCanvas(QGraphicsView):
    """
    Viewport gráfica vetorial de alta performance.

    Arquitetura interna:
        layers_items[layer_name] = {
            "geometry": { (chunk_id, geom_type, color) : ChunkGraphicsItem },
            "labels":   { chunk_id : LabelChunkItem }
        }

    O RenderState é a FONTE ÚNICA DE VERDADE para:
        - visibilidade de camadas
        - visibilidade de rótulos
        - seleção de feições
        - modo de interação
    """

    # Sinal emitido quando a seleção de feições muda
    selection_changed = pyqtSignal(set)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Configurações de renderização
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

        # Fundo escuro técnico CAD
        self.setStyleSheet("background-color: #0b0c10; border: none;")

        # ── Estado Central de Renderização ──
        self.state = RenderState()

        # Dicionário de camadas com separação geometria/labels
        self.layers_items = {}

        # Configurações da grade espacial para chunking
        self.grid_cols = 6
        self.grid_rows = 6
        self.grid_width = 1.0
        self.grid_height = 1.0
        self.min_x = 0.0
        self.max_y = 0.0

        # Inicializa grupos físicos e overlay de seleção
        self._init_groups()
        self._init_selection_overlay()

        # Índice espacial (construído uma única vez após carregamento completo)
        self._spatial_index = None
        self._index_handles = []         # Lista paralela de handles para o STRtree
        self._handle_to_feature = {}     # handle → dict da feição original
        self.feature_registry = {}       # handle → dicionário estruturado da feição

        # Rubber band para seleção por caixa
        self._rubber_band = None
        self._rubber_origin = None

    # ──────────────────────────────────────────────
    # Controle da Cena
    # ──────────────────────────────────────────────

    def clear_canvas(self):
        """Reseta completamente a cena e o estado de renderização."""
        self.scene.clear()
        self._init_groups()
        self._init_selection_overlay()  # Recria o overlay pois scene.clear() o destruiu no C++
        self.layers_items.clear()
        self.scene.setSceneRect(QRectF())
        self.state.reset()
        self._spatial_index = None
        self._index_handles.clear()
        self._handle_to_feature.clear()
        self.feature_registry.clear()

    def _init_groups(self):
        """Cria os grupos de renderização separados na cena para geometria e labels."""
        self.geometry_group = QGraphicsRectItem()
        self.geometry_group.setPen(QPen(Qt.PenStyle.NoPen))
        self.geometry_group.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.scene.addItem(self.geometry_group)

        self.label_group = QGraphicsRectItem()
        self.label_group.setPen(QPen(Qt.PenStyle.NoPen))
        self.label_group.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.label_group.setZValue(500)  # Garante que labels fiquem sempre acima de tudo
        self.scene.addItem(self.label_group)

    def _init_selection_overlay(self):
        """Cria e configura o QGraphicsPathItem para o destaque de seleção exclusivo."""
        self._selection_overlay = QGraphicsPathItem()
        highlight_pen = QPen(QColor("#fbbf24"), 3.0, Qt.PenStyle.SolidLine)
        highlight_pen.setCosmetic(True)
        self._selection_overlay.setPen(highlight_pen)
        self._selection_overlay.setBrush(QBrush(QColor(251, 191, 36, 120)))
        self._selection_overlay.setZValue(1000)  # Garante que fica por cima de tudo
        self.scene.addItem(self._selection_overlay)

    def initialize_grid(self, bbox):
        """Inicializa a grade espacial a partir do bounding box do arquivo."""
        min_x, min_y, max_x, max_y = bbox
        self.min_x = min_x
        self.max_y = max_y
        self.grid_width = max(1.0, max_x - min_x)
        self.grid_height = max(1.0, max_y - min_y)
        self.scene.setSceneRect(0, 0, self.grid_width, self.grid_height)
        logger.info(f"Grade Visual inicializada: {self.grid_width:.1f} x {self.grid_height:.1f}")

    def get_chunk_coords(self, pt):
        """Mapeia um ponto para uma célula de grade (col, row)."""
        try:
            if pt and isinstance(pt, (list, tuple)) and isinstance(pt[0], (list, tuple)):
                pt = pt[0]
            x, y = pt[0], pt[1]
            col = int((x / self.grid_width) * self.grid_cols)
            row = int((y / self.grid_height) * self.grid_rows)
            col = max(0, min(col, self.grid_cols - 1))
            row = max(0, min(row, self.grid_rows - 1))
            return col, row
        except Exception as e:
            logger.warning(f"Falha ao mapear coordenadas do chunk: {e}")
            return 0, 0

    def _ensure_layer_structure(self, layer_name):
        """Garante que a estrutura da camada exista no dicionário."""
        if layer_name not in self.layers_items:
            self.layers_items[layer_name] = {
                "geometry": {},
                "labels": {}
            }

    # ──────────────────────────────────────────────
    # Processamento de Geometrias (Mega-Path)
    # ──────────────────────────────────────────────

    def process_incoming_batch(self, layer_name, geom_type, color, translated_coords_list):
        """
        Processa lote de coordenadas geométricas e consolida em mega-paths.
        Labels NÃO são processados aqui — usam process_incoming_labels().
        Executado na thread principal (GUI).
        """
        if not translated_coords_list:
            return

        self._ensure_layer_structure(layer_name)
        chunks = self.layers_items[layer_name]["geometry"]

        # Caminhos temporários por chunk (evita atualizações repetitivas na cena)
        temp_paths = {}

        for polyline in translated_coords_list:
            if not polyline:
                continue

            # Determina célula de grade pelo primeiro vértice
            ref_pt = polyline[0]
            if ref_pt and isinstance(ref_pt, (list, tuple)) and isinstance(ref_pt[0], (list, tuple)):
                ref_pt = ref_pt[0]

            chunk_id = self.get_chunk_coords(ref_pt)

            if chunk_id not in temp_paths:
                temp_paths[chunk_id] = QPainterPath()

            path_obj = temp_paths[chunk_id]

            # Constrói instruções de desenho vetorial
            if geom_type == "Point":
                x, y = polyline[0][0], polyline[0][1]
                r = 1.5
                path_obj.addEllipse(x - r, y - r, 2 * r, 2 * r)

            elif geom_type == "Text":
                # Textos como pontos simples na geometria (rótulos vão separados)
                x, y = polyline[0][0], polyline[0][1]
                r = 1.0
                path_obj.addEllipse(x - r, y - r, 2 * r, 2 * r)

            elif geom_type == "Polygon":
                if isinstance(polyline[0], list) or (
                    isinstance(polyline[0], tuple) and isinstance(polyline[0][0], (list, tuple))
                ):
                    # Casca + furos
                    for ring in polyline:
                        if not ring:
                            continue
                        path_obj.moveTo(ring[0][0], ring[0][1])
                        for pt in ring[1:]:
                            path_obj.lineTo(pt[0], pt[1])
                        path_obj.closeSubpath()
                else:
                    path_obj.moveTo(polyline[0][0], polyline[0][1])
                    for pt in polyline[1:]:
                        path_obj.lineTo(pt[0], pt[1])
                    path_obj.closeSubpath()

            else:  # LineString
                path_obj.moveTo(polyline[0][0], polyline[0][1])
                for pt in polyline[1:]:
                    path_obj.lineTo(pt[0], pt[1])

        # Grava mega-paths nos itens gráficos da cena
        for chunk_id, new_path in temp_paths.items():
            key = (chunk_id, geom_type, color)
            if key in chunks:
                item = chunks[key]
                existing_path = item.path()
                existing_path.addPath(new_path)
                item.setPath(existing_path)
            else:
                item = ChunkGraphicsItem(new_path, layer_name, chunk_id, geom_type, color, parent=self.geometry_group)
                # Visibilidade inicial: consulta o RenderState
                item.setVisible(self.state.is_layer_visible(layer_name))
                chunks[key] = item

    # ──────────────────────────────────────────────
    # Processamento de Rótulos (painter.drawText)
    # ──────────────────────────────────────────────

    def process_incoming_labels(self, layer_name, translated_label_list):
        """
        Processa lote de rótulos de texto e armazena para desenho manual.
        NÃO usa QPainterPath.addText() — usa painter.drawText() em paint().
        Labels iniciam DESLIGADOS por padrão.

        Formato: [(x, y, texto), ...]
        """
        if not translated_label_list:
            return

        self._ensure_layer_structure(layer_name)
        label_chunks = self.layers_items[layer_name]["labels"]

        # Agrupa labels por chunk espacial
        chunk_groups = {}
        for item_data in translated_label_list:
            if not item_data or len(item_data) < 3:
                continue
            x, y, txt = item_data[0], item_data[1], item_data[2]
            if not txt:
                continue
            chunk_id = self.get_chunk_coords((x, y))
            if chunk_id not in chunk_groups:
                chunk_groups[chunk_id] = []
            chunk_groups[chunk_id].append((x, y, txt))

        # Cria ou atualiza LabelChunkItem por chunk
        for chunk_id, labels in chunk_groups.items():
            if chunk_id in label_chunks:
                # Incremental: adiciona ao item existente
                label_chunks[chunk_id].add_labels(labels)
            else:
                item = LabelChunkItem(layer_name, chunk_id, parent=self.label_group)
                item.add_labels(labels)
                # Visibilidade inicial: consulta o RenderState
                item.setVisible(self.state.is_labels_visible(layer_name))
                label_chunks[chunk_id] = item

    # ──────────────────────────────────────────────
    # Visibilidade (via RenderState)
    # ──────────────────────────────────────────────

    def toggle_layer_visibility(self, layer_name, is_visible):
        """Alterna visibilidade dos itens GEOMÉTRICOS de uma camada."""
        self.state.set_layer_visible(layer_name, is_visible)
        if layer_name in self.layers_items:
            for item in self.layers_items[layer_name]["geometry"].values():
                item.setVisible(is_visible)
        self._update_selection_overlay()

    def toggle_layer_labels(self, layer_name, is_visible):
        """Alterna visibilidade dos RÓTULOS de uma camada (independente da geometria)."""
        self.state.set_labels_visible(layer_name, is_visible)
        if layer_name in self.layers_items:
            for item in self.layers_items[layer_name]["labels"].values():
                item.setVisible(is_visible)

    def toggle_all_labels(self, is_visible):
        """Liga ou desliga todos os rótulos de todas as camadas."""
        all_layer_names = list(self.layers_items.keys())
        self.state.set_all_labels_visible(all_layer_names, is_visible)
        for layer_name in all_layer_names:
            for item in self.layers_items[layer_name]["labels"].values():
                item.setVisible(is_visible)

    # ──────────────────────────────────────────────
    # Navegação e Zoom
    # ──────────────────────────────────────────────

    def zoom_to_layer(self, layer_name):
        """Ajusta zoom para os limites de uma camada específica."""
        if layer_name not in self.layers_items:
            return

        geom_items = self.layers_items[layer_name]["geometry"].values()
        if not geom_items:
            return

        bbox = QRectF()
        for item in geom_items:
            if bbox.isEmpty():
                bbox = item.boundingRect()
            else:
                bbox = bbox.united(item.boundingRect())

        if not bbox.isEmpty():
            if bbox.width() < 1.0 or bbox.height() < 1.0:
                bbox = bbox.adjusted(-5.0, -5.0, 5.0, 5.0)
            self.fitInView(bbox, Qt.AspectRatioMode.KeepAspectRatio)

    def fit_scene_to_view(self):
        """Enquadra todo o desenho na tela. Chamado APENAS ao final do carregamento."""
        rect = self.scene.sceneRect()
        if not rect.isEmpty():
            self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        """Zoom suave centralizado na posição do cursor."""
        zoom_factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        mouse_scene_before = self.mapToScene(event.position().toPoint())
        self.scale(zoom_factor, zoom_factor)
        mouse_scene_after = self.mapToScene(event.position().toPoint())
        delta = mouse_scene_after - mouse_scene_before
        self.translate(delta.x(), delta.y())

    # ──────────────────────────────────────────────
    # Modo de Interação
    # ──────────────────────────────────────────────

    def set_selection_mode(self, enabled):
        """Alterna entre modo de navegação e modo de seleção espacial."""
        if enabled:
            self.state.set_mode("selection")
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.state.set_mode("navigation")
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)

    # ──────────────────────────────────────────────
    # Índice Espacial (STRtree — construído uma vez)
    # ──────────────────────────────────────────────

    def build_spatial_index(self, parsed_features):
        """
        Constrói o índice espacial STRtree e o feature_registry a partir das feições parseadas.
        Chamado UMA ÚNICA VEZ ao final do carregamento completo.
        Shapely é usado AQUI e na exportação — NUNCA no loop de paint().
        """
        try:
            from shapely import STRtree
            from gis.geometry_engine import GeometryFactory

            geometries = []
            handles = []
            self.feature_registry.clear()

            for feat in parsed_features:
                handle = feat.get("handle")
                if not handle:
                    continue

                geom_type = feat["geom_type"]
                coords = feat["coords"]
                color = feat["color"]
                layer_name = feat["layer"]

                geom = GeometryFactory.to_shapely(geom_type, coords)
                if geom and not geom.is_empty:
                    geometries.append(geom)
                    handles.append(handle)
                    self._handle_to_feature[handle] = feat

                    # Determina o ChunkGraphicsItem correspondente para o feature_registry
                    graphics_item = None
                    if coords:
                        # Extrai o primeiro ponto para obter o chunk_id
                        if geom_type == "Polygon" and isinstance(coords[0], list) and not isinstance(coords[0][0], (int, float)):
                            pt_orig = coords[0][0]
                        else:
                            pt_orig = coords[0]
                        
                        # Translada para o espaço local de cena
                        pt_translated = (pt_orig[0] - self.min_x, self.max_y - pt_orig[1])
                        chunk_id = self.get_chunk_coords(pt_translated)
                        
                        key = (chunk_id, geom_type, color)
                        graphics_item = self.layers_items.get(layer_name, {}).get("geometry", {}).get(key)

                    # Registra a feição de acordo com a estrutura obrigatória
                    self.feature_registry[handle] = {
                        "geometry": geom,
                        "graphics_item": graphics_item,
                        "layer": layer_name,
                        "entity_type": feat.get("dxftype", geom_type),
                        "attributes": {
                            "handle": handle,
                            "layer": layer_name,
                            "geom_type": geom_type,
                            "dxftype": feat.get("dxftype", ""),
                            "color": color,
                            "texto": feat.get("texto", "") if "texto" in feat else "",
                            "linetype": feat.get("linetype", "BYLAYER"),
                            "lineweight": feat.get("lineweight", -1)
                        }
                    }

            if geometries:
                self._spatial_index = STRtree(geometries)
                self._index_handles = handles
                logger.info(f"Índice espacial STRtree construído: {len(geometries)} geometrias indexadas.")
            else:
                logger.warning("Nenhuma geometria válida para construir índice espacial.")

        except Exception as e:
            logger.error(f"Erro ao construir índice espacial: {e}", exc_info=True)

    def _query_point(self, scene_x, scene_y, tolerance=5.0):
        """Consulta pontual ao índice espacial. Filtra as visíveis e escolhe a mais próxima."""
        if not self._spatial_index:
            return []
        try:
            from shapely.geometry import box, Point

            # Converte coordenadas da cena para coordenadas CAD originais
            orig_x = scene_x + self.min_x
            orig_y = self.max_y - scene_y
            click_pt = Point(orig_x, orig_y)

            query_box = box(
                orig_x - tolerance, orig_y - tolerance,
                orig_x + tolerance, orig_y + tolerance
            )
            candidate_indices = self._spatial_index.query(query_box)

            candidates = []
            for idx in candidate_indices:
                if idx < len(self._index_handles):
                    handle = self._index_handles[idx]
                    feat = self._handle_to_feature.get(handle)
                    # Apenas permite selecionar feições de camadas visíveis
                    if feat and self.state.is_layer_visible(feat["layer"]):
                        reg_feat = self.feature_registry.get(handle)
                        if reg_feat and reg_feat["geometry"]:
                            dist = click_pt.distance(reg_feat["geometry"])
                            candidates.append((handle, dist))

            # Escolhe o handle que tiver a menor distância geométrica ao clique
            if candidates:
                candidates.sort(key=lambda x: x[1])
                return [candidates[0][0]]
            return []
        except Exception as e:
            logger.warning(f"Erro na consulta espacial pontual: {e}")
            return []

    def _query_box(self, scene_rect):
        """Consulta por retângulo ao índice espacial. Filtra apenas as feições visíveis."""
        if not self._spatial_index:
            return []
        try:
            from shapely.geometry import box

            x1 = scene_rect.left() + self.min_x
            y1 = self.max_y - scene_rect.bottom()
            x2 = scene_rect.right() + self.min_x
            y2 = self.max_y - scene_rect.top()

            query_box = box(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            candidate_indices = self._spatial_index.query(query_box)

            visible_handles = []
            for idx in candidate_indices:
                if idx < len(self._index_handles):
                    handle = self._index_handles[idx]
                    feat = self._handle_to_feature.get(handle)
                    if feat and self.state.is_layer_visible(feat["layer"]):
                        visible_handles.append(handle)
            return visible_handles
        except Exception as e:
            logger.warning(f"Erro na consulta espacial por caixa: {e}")
            return []

    # ──────────────────────────────────────────────
    # Seleção Espacial (Incremental)
    # ──────────────────────────────────────────────

    def select_features(self, handles, additive=False):
        """Seleciona feições pelos handles. Destaca estritamente as feições na camada overlay."""
        self.state.select_handles(handles, additive=additive)
        self._update_selection_overlay()
        self.selection_changed.emit(self.state.selected_handles)

    def clear_selection(self):
        """Limpa seleção e remove overlay visual."""
        self.state.clear_selection()
        self._update_selection_overlay()
        self.selection_changed.emit(self.state.selected_handles)

    def _update_selection_overlay(self):
        """Reconstrói o path de overlay destacando estritamente as feições selecionadas e visíveis."""
        if not self.state.selected_handles:
            self._selection_overlay.setPath(QPainterPath())
            return

        overlay_path = QPainterPath()
        
        offset_x = 0.0
        offset_y = 0.0
        if abs(self.grid_width) > 1e-3 and abs(self.grid_height) > 1e-3:
            offset_x = self.min_x
            offset_y = self.max_y

        for handle in self.state.selected_handles:
            feat = self._handle_to_feature.get(handle)
            # Apenas exibe highlight se a feição existir e a camada da feição estiver visível
            if not feat or not self.state.is_layer_visible(feat["layer"]):
                continue
            
            geom_type = feat["geom_type"]
            coords = feat["coords"]
            if not coords:
                continue

            if geom_type in ("Point", "Text"):
                x = coords[0][0] - offset_x
                y = offset_y - coords[0][1]
                r = 2.0
                overlay_path.addEllipse(x - r, y - r, 2 * r, 2 * r)
            elif geom_type == "Polygon":
                if isinstance(coords[0], list) or (isinstance(coords[0], tuple) and isinstance(coords[0][0], (list, tuple))):
                    for ring in coords:
                        if not ring: continue
                        overlay_path.moveTo(ring[0][0] - offset_x, offset_y - ring[0][1])
                        for pt in ring[1:]:
                            overlay_path.lineTo(pt[0] - offset_x, offset_y - pt[1])
                        overlay_path.closeSubpath()
                else:
                    overlay_path.moveTo(coords[0][0] - offset_x, offset_y - coords[0][1])
                    for pt in coords[1:]:
                        overlay_path.lineTo(pt[0] - offset_x, offset_y - pt[1])
                    overlay_path.closeSubpath()
            else:  # LineString
                overlay_path.moveTo(coords[0][0] - offset_x, offset_y - coords[0][1])
                for pt in coords[1:]:
                    overlay_path.lineTo(pt[0] - offset_x, offset_y - pt[1])

        self._selection_overlay.setPath(overlay_path)

    # ──────────────────────────────────────────────
    # Eventos de Mouse (Seleção)
    # ──────────────────────────────────────────────

    def mousePressEvent(self, event):
        """Captura clique para iniciar seleção ou rubber band."""
        if self.state.is_selection_mode() and event.button() == Qt.MouseButton.LeftButton:
            self._rubber_origin = event.position().toPoint()
            if not self._rubber_band:
                self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
            self._rubber_band.setGeometry(
                self._rubber_origin.x(), self._rubber_origin.y(), 0, 0
            )
            self._rubber_band.show()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Atualiza rubber band durante arraste de seleção."""
        if self.state.is_selection_mode() and self._rubber_origin and self._rubber_band:
            from PyQt6.QtCore import QRect
            current = event.position().toPoint()
            rect = QRect(self._rubber_origin, current).normalized()
            self._rubber_band.setGeometry(rect)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Finaliza seleção — clique simples ou caixa."""
        if self.state.is_selection_mode() and event.button() == Qt.MouseButton.LeftButton:
            additive = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)

            if self._rubber_band:
                self._rubber_band.hide()
                rubber_rect = self._rubber_band.geometry()

                if rubber_rect.width() < 10 and rubber_rect.height() < 10:
                    # Clique simples — consulta pontual com maior tolerância (1.5%)
                    scene_pos = self.mapToScene(event.position().toPoint())
                    viewport_rect = self.mapToScene(self.viewport().rect()).boundingRect()
                    tolerance = max(viewport_rect.width(), viewport_rect.height()) * 0.015
                    tolerance = max(2.0, min(tolerance, 150.0))

                    handles = self._query_point(scene_pos.x(), scene_pos.y(), tolerance)
                    if handles:
                        self.select_features(handles, additive=additive)
                    elif not additive:
                        self.clear_selection()
                else:
                    # Seleção por caixa
                    top_left = self.mapToScene(rubber_rect.topLeft())
                    bottom_right = self.mapToScene(rubber_rect.bottomRight())
                    scene_rect = QRectF(top_left, bottom_right).normalized()
                    handles = self._query_box(scene_rect)
                    if handles:
                        self.select_features(handles, additive=additive)
                    elif not additive:
                        self.clear_selection()

            self._rubber_origin = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)
