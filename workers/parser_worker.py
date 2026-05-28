import os
import logging
import time
from PyQt6.QtCore import QObject, pyqtSignal
from cad.converter import convert_dwg_to_dxf
from cad.parser import stream_dxf_entities
from gis.geometry_engine import detect_crs_heuristically

logger = logging.getLogger("geocad_bridge.workers.parser_worker")

class CADGeometryWorker(QObject):
    """
    Controlador de execução do Worker em segundo plano (QThread).
    Gerencia a conversão de arquivos DWG e o fluxo incremental de parsing DXF.

    Emite sinais separados para geometrias e rótulos de texto,
    garantindo desacoplamento entre rendering geométrico e labels.
    """
    progress_changed = pyqtSignal(int)
    status_msg = pyqtSignal(str)
    grid_initialized = pyqtSignal(tuple)   # Emite (min_x, min_y, max_x, max_y)
    crs_detected = pyqtSignal(str, str)    # Emite (status_level, mensagem_formatada)
    layer_found = pyqtSignal(str, str, int)  # Emite (nome_camada, tipo_geometrico, contagem)
    layers_found = pyqtSignal(list)        # Emite a lista consolidada [(nome_camada, tipo_geometrico, contagem), ...]

    # Emite lotes de geometrias: (nome_camada, tipo_geometrico, cor_hex, lista_coordenadas_transladadas)
    batch_ready = pyqtSignal(str, str, str, list)

    # Emite lotes de rótulos de texto (separado das geometrias):
    # (nome_camada, lista_de_tuplas [(x, y, texto)])
    labels_ready = pyqtSignal(str, list)

    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, file_path, converter_path=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.converter_path = converter_path
        self._is_cancelled = False
        self.success = False

        # Lista contendo feições com coordenadas originais para a exportação final em SHP
        self.parsed_features = []

        # Caminho do DXF temporário gerado para exclusão automática ao final
        self.converted_dxf_path = None

    def cancel(self):
        """Sinaliza a interrupção das operações do worker."""
        self._is_cancelled = True
        logger.info("Solicitação de cancelamento recebida pelo Worker.")

    def run(self):
        """Método de processamento principal executado na thread secundária."""
        try:
            self.status_msg.emit("Iniciando processamento...")
            self.progress_changed.emit(5)
            self.success = False

            target_path = self.file_path
            _, ext = os.path.splitext(self.file_path.lower())

            # 1. Converte DWG para DXF se o arquivo for DWG
            if ext == ".dwg":
                self.status_msg.emit("Convertendo DWG para DXF silenciosamente via LibreDWG...")
                try:
                    self.converted_dxf_path = convert_dwg_to_dxf(self.file_path, self.converter_path)
                    target_path = self.converted_dxf_path
                except Exception as e:
                    logger.error(f"Erro na conversão automática via LibreDWG: {e}")
                    self.error_occurred.emit(f"Falha na conversão de DWG: {str(e)}")
                    return

            if self._is_cancelled:
                return

            self.status_msg.emit("Lendo dados vetoriais do arquivo DXF...")
            self.progress_changed.emit(25)

            # 2. Executa a varredura progressiva (streaming)
            # Buffer de transmissão para agrupamento de sinais de geometrias
            # coord_buffers[(camada, tipo, cor)] = [coordenadas_transladadas, ...]
            coord_buffers = {}
            buffer_feature_count = 0
            max_buffer_size = 1500  # Envia lotes a cada 1500 geometrias para aliviar a UI

            # Buffer separado para rótulos de texto
            # label_buffers[camada] = [(x, y, texto), ...]
            label_buffers = {}
            label_buffer_count = 0
            max_label_buffer_size = 500  # Labels são mais leves, buffer menor

            # Estatísticas das camadas
            layer_counts = {}
            layer_types = {}

            bbox = None
            offset_x = 0.0
            offset_y = 0.0
            total_entities = 0

            # Consome o gerador do parser DXF
            generator = stream_dxf_entities(target_path)

            for item in generator:
                if self._is_cancelled:
                    logger.info("Processamento interrompido pelo usuário.")
                    break

                meta = item.get("meta")

                if meta == "total_count":
                    total_entities = item["count"]

                elif meta == "header_bbox":
                    bbox = item["bbox"]
                    min_x, min_y, max_x, max_y = bbox

                    # Trata bboxes nulos ou corrompidos
                    if abs(max_x - min_x) < 1e-3 or abs(max_y - min_y) < 1e-3:
                        offset_x = 0.0
                        offset_y = 0.0
                        bbox = (0, 0, 1000, 1000)
                    else:
                        offset_x = min_x
                        offset_y = max_y

                    self.grid_initialized.emit(bbox)

                elif meta == "geodata_crs":
                    crs_str = item["crs"]
                    if bbox:
                        status, epsg, msg, alternates = detect_crs_heuristically(bbox, crs_str)
                        self.crs_detected.emit(status, msg)

                elif meta == "progress":
                    idx = item["index"]
                    if total_entities > 0:
                        percent = int(25 + (idx / total_entities) * 70)
                        self.progress_changed.emit(min(95, percent))
                        self.status_msg.emit(f"Processando entidades CAD: {idx}/{total_entities}")

                elif meta == "summary":
                    sucesso = item["sucesso"]
                    ignoradas = item["entidades_ignoradas"]
                    blocos_ignorados = item["blocos_ignorados"]
                    correcoes = item["correcoes_dxf"]
                    self.status_msg.emit(
                        f"Resumo: {sucesso} lidas com sucesso, {ignoradas} ignoradas, "
                        f"{blocos_ignorados} blocos pulados, {correcoes} correções estruturais."
                    )
                    logger.info(
                        f"Resumo do parsing: sucesso={sucesso}, ignoradas={ignoradas}, "
                        f"blocos_ignorados={blocos_ignorados}, correcoes_dxf={correcoes}"
                    )

                elif meta == "completed":
                    self.status_msg.emit("Varredura vetorial concluída!")
                    self.progress_changed.emit(95)

                elif not meta:
                    # Feição vetorial válida
                    # Guarda a feição com coordenadas originais para futura gravação em Shapefile
                    self.parsed_features.append(item)

                    layer_name = item["layer"]
                    geom_type = item["geom_type"]
                    color = item["color"]
                    raw_coords = item["coords"]

                    # Atualiza estatísticas da camada
                    layer_counts[layer_name] = layer_counts.get(layer_name, 0) + 1
                    layer_types[layer_name] = geom_type

                    # Translada as coordenadas locais para evitar estouro numérico no Canvas Qt
                    translated_coords = []

                    if geom_type == "Text":
                        # Textos: preserva o string da entidade na terceira posição
                        translated_coords = [(pt[0] - offset_x, offset_y - pt[1], pt[2]) for pt in raw_coords]

                        # EMISSÃO DUAL: geometria como ponto + rótulo como texto separado
                        # 1. Buffer de geometrias (ponto simples para o marcador)
                        geom_key = (layer_name, geom_type, color)
                        if geom_key not in coord_buffers:
                            coord_buffers[geom_key] = []
                        coord_buffers[geom_key].append(translated_coords)
                        buffer_feature_count += 1

                        # 2. Buffer de labels (texto visual independente)
                        if layer_name not in label_buffers:
                            label_buffers[layer_name] = []
                        label_buffers[layer_name].extend(translated_coords)
                        label_buffer_count += 1

                    elif geom_type == "Polygon" and isinstance(raw_coords[0], list) and not isinstance(raw_coords[0][0], (int, float)):
                        # Polígonos de Hachuras estruturados em múltiplos anéis (casca + furos)
                        for ring in raw_coords:
                            translated_ring = [(pt[0] - offset_x, offset_y - pt[1]) for pt in ring]
                            translated_coords.append(translated_ring)

                        geom_key = (layer_name, geom_type, color)
                        if geom_key not in coord_buffers:
                            coord_buffers[geom_key] = []
                        coord_buffers[geom_key].append(translated_coords)
                        buffer_feature_count += 1

                    else:
                        # Pontos e polilinhas lineares padrão
                        translated_coords = [(pt[0] - offset_x, offset_y - pt[1]) for pt in raw_coords]

                        geom_key = (layer_name, geom_type, color)
                        if geom_key not in coord_buffers:
                            coord_buffers[geom_key] = []
                        coord_buffers[geom_key].append(translated_coords)
                        buffer_feature_count += 1

                    # Transmite lote acumulado caso atinja o limite de throttling
                    if buffer_feature_count >= max_buffer_size:
                        self._emit_geometry_buffers(coord_buffers)
                        buffer_feature_count = 0
                        time.sleep(0.005)  # Pausa rápida para liberar CPU para a thread principal

                    # Transmite lote de labels acumulado
                    if label_buffer_count >= max_label_buffer_size:
                        self._emit_label_buffers(label_buffers)
                        label_buffer_count = 0

            # Transmite dados residuais nos buffers
            if buffer_feature_count > 0:
                self._emit_geometry_buffers(coord_buffers)

            if label_buffer_count > 0:
                self._emit_label_buffers(label_buffers)

            # Informa a lista final de camadas consolidadas à interface em um único lote
            layer_geom_counts = {}
            for item in self.parsed_features:
                layer_name = item.get("layer")
                geom_type = item.get("geom_type")
                if layer_name and geom_type:
                    layer_geom_counts[(layer_name, geom_type)] = layer_geom_counts.get((layer_name, geom_type), 0) + 1

            layers_data = [(layer, geom, count) for (layer, geom), count in layer_geom_counts.items()]
            self.layers_found.emit(layers_data)

            self.progress_changed.emit(100)
            self.status_msg.emit("Processamento concluído com sucesso!")
            self.success = True

        except Exception as e:
            self.success = False
            logger.error(f"Erro crítico no processamento de background: {e}", exc_info=True)
            self.error_occurred.emit(f"Erro interno de processamento: {str(e)}")
        finally:
            self.cleanup()
            self.finished.emit()

    def _emit_geometry_buffers(self, coord_buffers):
        """Envia os dados de desenho geométrico acumulados para o Canvas."""
        for (layer, geom_type, color), coords_list in list(coord_buffers.items()):
            if coords_list:
                self.batch_ready.emit(layer, geom_type, color, coords_list)
        coord_buffers.clear()

    def _emit_label_buffers(self, label_buffers):
        """Envia os dados de rótulos de texto acumulados para o Canvas."""
        for layer_name, label_list in list(label_buffers.items()):
            if label_list:
                self.labels_ready.emit(layer_name, label_list)
        label_buffers.clear()

    def cleanup(self):
        """Remove arquivos temporários criados para a importação de forma condicional."""
        if self.converted_dxf_path and os.path.exists(self.converted_dxf_path):
            if self.success:
                try:
                    os.remove(self.converted_dxf_path)
                    logger.info(f"Removido DXF temporário gerado pela conversão: {self.converted_dxf_path}")
                except Exception as e:
                    logger.warning(f"Não foi possível remover arquivo temporário DXF: {e}")
            else:
                logger.warning(f"DXF temporário preservado para análise: {self.converted_dxf_path}")
            self.converted_dxf_path = None
