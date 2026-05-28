import os
import logging
import ezdxf
from ezdxf import path
from ezdxf.colors import aci2rgb

logger = logging.getLogger("geocad_bridge.cad.parser")

# Monkeypatch ezdxf SortEntsTable.load_table para evitar DXFStructureError em arquivos corrompidos
try:
    from ezdxf.entities.dxfobj import SortEntsTable
    from ezdxf.tools import take2
    from ezdxf.lldxf.const import DXFStructureError

    def safe_load_table(self, tags) -> None:
        try:
            for handle, sort_handle in take2(tags):
                if handle.code == 331 and sort_handle.code == 5:
                    self.table[handle.value] = sort_handle.value
                else:
                    logger.warning(
                        f"SORTENTSTABLE: Ignorando tags de ordenação inconsistentes (handle: {handle.code}, sort: {sort_handle.code})"
                    )
        except Exception as e:
            logger.warning(f"Erro ao recuperar e ler a tabela SORTENTSTABLE: {e}")

    SortEntsTable.load_table = safe_load_table
except Exception as e:
    logger.error(f"Não foi possível aplicar monkeypatch em ezdxf.SortEntsTable: {e}")

# Tipos de entidades CAD que serão ignoradas durante a importação
IGNORE_TYPES = {"DIMENSION"}

def get_entity_color(entity, doc):
    """
    Extrai o código de cor em formato HEX para uma entidade, resolvendo BYLAYER e BYBLOCK.
    """
    try:
        # ACI padrão é ByLayer (256)
        aci = entity.dxf.color
    except Exception:
        aci = 256
        
    if aci == 256:  # BYLAYER (Herda a cor da camada)
        try:
            layer_name = entity.dxf.layer
            layer = doc.layers.get(layer_name)
            aci = layer.color
        except Exception:
            aci = 7  # Padrão branco/preto
    elif aci == 0:  # BYBLOCK (Herda a cor do bloco)
        aci = 7

    # Conversão de ACI para RGB
    try:
        rgb = aci2rgb(aci)
        return f"#{rgb.r:02x}{rgb.g:02x}{rgb.b:02x}"
    except Exception:
        # Se o índice ACI falhar, tenta verificar cores verdadeiras (True Color)
        try:
            rgb = entity.rgb
            if rgb:
                return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        except Exception:
            pass
        return "#ffffff"

def parse_entity_geometry(entity, sagitta=0.01):
    """
    Processa a geometria de uma entidade CAD individual, retornando a lista de coordenadas e o tipo geométrico GIS.
    """
    dxftype = entity.dxftype()

    if dxftype == "POINT":
        loc = entity.dxf.location
        return [(loc.x, loc.y)], "Point"

    elif dxftype == "LINE":
        start = entity.dxf.start
        end = entity.dxf.end
        return [(start.x, start.y), (end.x, end.y)], "LineString"

    elif dxftype in ("LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE", "ELLIPSE", "SPLINE"):
        try:
            p = path.make_path(entity)
            vertices = list(p.flattening(sagitta))
            coords = [(v.x, v.y) for v in vertices]
            if not coords:
                return [], "LineString"
                
            # Círculos e elipses são sempre fechados.
            # Polilinhas podem ser abertas ou fechadas.
            is_closed = p.is_closed or getattr(entity, "is_closed", False)
            geom_type = "Polygon" if is_closed else "LineString"
            return coords, geom_type
        except Exception as e:
            logger.warning(f"Falha ao extrair caminho geométrico para {dxftype} (handle: {entity.dxf.handle}): {e}")
            # Fallback para polilinhas caso make_path falhe
            if dxftype in ("LWPOLYLINE", "POLYLINE"):
                try:
                    coords = [(v[0], v[1]) for v in entity.vertices()]
                    is_closed = entity.is_closed
                    geom_type = "Polygon" if is_closed else "LineString"
                    return coords, geom_type
                except Exception:
                    pass
            return [], "LineString"

    elif dxftype == "HATCH":
        try:
            # Extrai os caminhos de contorno da hachura
            hatch_paths = path.from_hatch(entity)
            all_coords = []
            for p in hatch_paths:
                vertices = list(p.flattening(sagitta))
                coords = [(v.x, v.y) for v in vertices]
                if coords:
                    all_coords.append(coords)
            # Hachuras representam áreas preenchidas (Polígonos)
            return all_coords, "Polygon"
        except Exception as e:
            logger.warning(f"Falha ao extrair contorno de hachura HATCH (handle: {entity.dxf.handle}): {e}")
            return [], "Polygon"

    elif dxftype in ("TEXT", "MTEXT"):
        try:
            loc = entity.dxf.insert
            txt = ""
            if dxftype == "TEXT":
                txt = entity.dxf.text
            elif dxftype == "MTEXT":
                txt = entity.text
            # Retorna as coordenadas e o tipo geométrico "Text"
            return [(loc.x, loc.y, txt)], "Text"
        except Exception as e:
            logger.warning(f"Falha ao extrair coordenadas do texto {dxftype} (handle: {entity.dxf.handle}): {e}")
            return [], "Text"

    return [], "Unknown"

def stream_dxf_entities(dxf_path, sagitta=0.01):
    """
    Gerador que realiza a varredura (streaming) do arquivo DXF e retorna registros de geometria compatíveis com GIS.
    Utiliza o modo recover do ezdxf para lidar com arquivos CAD corrompidos e imperfeitos.
    Explode referências de blocos (INSERT) recursivamente com tratamento básico de segurança.
    """
    if not os.path.exists(dxf_path):
        raise FileNotFoundError(f"Arquivo DXF não encontrado: {dxf_path}")

    logger.info(f"Abrindo arquivo DXF no modo de recuperação (Recover Mode): {dxf_path}")
    
    from ezdxf import recover
    
    try:
        doc, auditor = recover.readfile(dxf_path)
    except Exception as e:
        logger.critical(f"Falha irrecuperável ao tentar reconstruir o arquivo DXF: {e}")
        raise

    if auditor.errors:
        logger.warning(f"DXF recuperado com {len(auditor.errors)} inconsistências estruturais. Algumas entidades poderão ser ignoradas.")
        for err in auditor.errors:
            logger.debug(f"Inconsistência corrigida: código {err.code} - {err.message}")

    msp = doc.modelspace()
    total = len(msp)
    logger.info(f"Modelo estruturado com {total} entidades de topo no modelspace.")

    # Retorna o total de entidades de topo para estimativa de progresso
    yield {"meta": "total_count", "count": total}

    # Bounding box heurístico do cabeçalho do arquivo
    extmin = doc.header.get("$EXTMIN", (0.0, 0.0, 0.0))
    extmax = doc.header.get("$EXTMAX", (0.0, 0.0, 0.0))
    bbox = (extmin[0], extmin[1], extmax[0], extmax[1])
    yield {"meta": "header_bbox", "bbox": bbox}

    # Tenta obter sistema de referência espacial configurado na seção GEODATA
    crs_detected = None
    try:
        geodata = msp.get_geodata()
        if geodata:
            crs_desc = geodata.dxf.coordinate_system_definition
            logger.info(f"Sistema de coordenadas localizado via GEODATA: {crs_desc}")
            crs_detected = crs_desc
    except Exception:
        pass
    yield {"meta": "geodata_crs", "crs": crs_detected}

    # Contadores de auditoria local de parsing
    stats = {
        "sucesso": 0,
        "entidades_ignoradas": 0,
        "blocos_ignorados": 0
    }

    # Função interna para processar recursivamente referências de blocos
    def process_recursive(entity, depth=0):
        if depth > 20: # Proteção contra loops de recursão infinita em blocos
            logger.warning(f"Profundidade máxima de bloco atingida. Abortando recursão no elemento: {getattr(entity.dxf, 'handle', 'N/A')}")
            return
            
        try:
            dxftype = entity.dxftype()
        except Exception as e:
            stats["entidades_ignoradas"] += 1
            logger.warning(f"Entidade com cabeçalho inválido ignorada: {e}")
            return

        if dxftype in IGNORE_TYPES:
            return

        if dxftype == "INSERT":
            try:
                # virtual_entities() retorna os sub-elementos com escala/rotação/translação do bloco
                for sub_entity in entity.virtual_entities():
                    yield from process_recursive(sub_entity, depth + 1)
            except Exception as e:
                stats["blocos_ignorados"] += 1
                logger.warning(f"Bloco com erro ignorado (handle: {getattr(entity.dxf, 'handle', 'N/A')}): {e}")
        else:
            try:
                coords, geom_type = parse_entity_geometry(entity, sagitta)
                if coords and geom_type != "Unknown":
                    color = get_entity_color(entity, doc)
                    stats["sucesso"] += 1
                    feat = {
                        "layer": entity.dxf.layer,
                        "dxftype": dxftype,
                        "geom_type": geom_type,
                        "coords": coords,
                        "color": color,
                        "handle": entity.dxf.handle,
                        "linetype": entity.dxf.get("linetype", "BYLAYER"),
                        "lineweight": entity.dxf.get("lineweight", -1)
                    }
                    if dxftype in ("TEXT", "MTEXT") and len(coords[0]) > 2:
                        feat["texto"] = coords[0][2]
                    yield feat
            except Exception as e:
                stats["entidades_ignoradas"] += 1
                logger.warning(f"Falha de processamento de geometria na entidade {dxftype} (handle: {getattr(entity.dxf, 'handle', 'N/A')}): {e}")

    for idx, entity in enumerate(msp):
        # Retorna o progresso a cada lote de leitura
        if idx % 1000 == 0:
            yield {"meta": "progress", "index": idx}
            
        yield from process_recursive(entity)

    # Retorna o resumo de estatísticas do parser
    yield {
        "meta": "summary",
        "sucesso": stats["sucesso"],
        "entidades_ignoradas": stats["entidades_ignoradas"],
        "blocos_ignorados": stats["blocos_ignorados"],
        "correcoes_dxf": len(auditor.errors)
    }
    yield {"meta": "completed"}
