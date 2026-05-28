import logging
import re
from shapely.geometry import Point, LineString, Polygon
from shapely.validation import make_valid
from shapely.ops import linemerge, unary_union

logger = logging.getLogger("geocad_bridge.gis.geometry_engine")

class GeometryFactory:
    """
    Classe utilitária para conversão, correção, simplificação e validação 
    de geometrias CAD para geometrias Shapely compatíveis com GIS.
    """
    
    @staticmethod
    def to_shapely(geom_type, coords):
        """
        Converte listas de coordenadas brutas do CAD em geometrias Shapely válidas.
        Suporta pontos, linhas e polígonos complexos (como hachuras com furos).
        """
        if not coords:
            return None

        try:
            if geom_type in ("Point", "Text"):
                # coords: lista contendo uma única tupla de coordenadas [(x, y)] ou [(x, y, texto)]
                p = Point(coords[0][0], coords[0][1])
                return p if p.geom_type == "Point" else None
                
            elif geom_type == "LineString":
                # coords: lista de vértices [(x1, y1), (x2, y2), ...]
                if len(coords) < 2:
                    return None
                line = LineString(coords)
                valid_line = make_valid(line)
                if valid_line.geom_type == "GeometryCollection":
                    lines = [g for g in valid_line.geoms if g.geom_type in ("LineString", "MultiLineString")]
                    if not lines:
                        return None
                    elif len(lines) == 1:
                        return lines[0]
                    else:
                        return unary_union(lines)
                elif valid_line.geom_type not in ("LineString", "MultiLineString"):
                    return None
                return valid_line
                
            elif geom_type == "Polygon":
                # Hachuras (HATCH) podem retornar lista de listas de vértices:
                # [ [contorno_externo], [furo_1], [furo_2], ... ]
                if isinstance(coords[0], list) or isinstance(coords[0], tuple) and isinstance(coords[0][0], (list, tuple)):
                    if not coords[0] or len(coords[0]) < 3:
                        return None
                    shell = coords[0]
                    # Garante que o contorno seja fechado
                    if shell[0] != shell[-1]:
                        shell = list(shell) + [shell[0]]
                    
                    holes = []
                    for h in coords[1:]:
                        if len(h) >= 3:
                            closed_h = list(h) + [h[0]] if h[0] != h[-1] else h
                            holes.append(closed_h)
                            
                    poly = Polygon(shell=shell, holes=holes)
                else:
                    # Polilinha fechada simples
                    if len(coords) < 3:
                        return None
                    shell = coords
                    if shell[0] != shell[-1]:
                        shell = list(shell) + [shell[0]]
                    poly = Polygon(shell)
                
                # Executa a limpeza topológica automática (corrige auto-interseções)
                valid_poly = make_valid(poly)
                if valid_poly.geom_type == "GeometryCollection":
                    polys = [g for g in valid_poly.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
                    if not polys:
                        return None
                    elif len(polys) == 1:
                        return polys[0]
                    else:
                        return unary_union(polys)
                elif valid_poly.geom_type not in ("Polygon", "MultiPolygon"):
                    return None
                return valid_poly
                
        except Exception as e:
            logger.error(f"Erro ao converter coordenadas para objeto Shapely {geom_type}: {e}")
            return None

    @staticmethod
    def clean_topology(geometries):
        """
        Executa a união e validação de geometrias para resolver sobreposições e problemas de desenho.
        """
        try:
            valid_geoms = [geom for geom in geometries if geom and geom.is_valid]
            if not valid_geoms:
                return []
            
            union_geom = unary_union(valid_geoms)
            if union_geom.is_empty:
                return []
            
            if hasattr(union_geom, "geoms"):
                return list(union_geom.geoms)
            return [union_geom]
        except Exception as e:
            logger.error(f"Erro ao limpar topologia das geometrias: {e}")
            return geometries

    @staticmethod
    def merge_lines(linestrings):
        """
        Une segmentos de linhas contíguos em polilinhas mais longas.
        """
        try:
            valid_lines = [line for line in linestrings if isinstance(line, LineString)]
            if not valid_lines:
                return []
            merged = linemerge(valid_lines)
            if hasattr(merged, "geoms"):
                return list(merged.geoms)
            return [merged]
        except Exception as e:
            logger.error(f"Erro ao mesclar segmentos de linhas: {e}")
            return linestrings


def detect_crs_heuristically(bbox, geodata_crs_str=None):
    """
    Analisa os limites geográficos (bounding box) e tenta inferir o sistema de coordenadas (CRS).
    Retorna: (Status_do_CRS, EPSG_Principal, Mensagem, CRS_Alternativos)
    """
    # 1. Tenta extrair a partir da string GEODATA do cabeçalho CAD se disponível
    if geodata_crs_str:
        match = re.search(r"EPSG:?\s*(\d+)", geodata_crs_str, re.IGNORECASE)
        if match:
            epsg = f"EPSG:{match.group(1)}"
            logger.info(f"CRS extraído da seção GEODATA: {epsg}")
            return "SUCCESS", epsg, f"GEODATA: {epsg}", []
            
        if "31982" in geodata_crs_str or "22S" in geodata_crs_str:
            return "SUCCESS", "EPSG:31982", "SIRGAS 2000 / UTM zone 22S (via GEODATA)", ["EPSG:31981", "EPSG:31983"]
        if "31981" in geodata_crs_str or "21S" in geodata_crs_str:
            return "SUCCESS", "EPSG:31981", "SIRGAS 2000 / UTM zone 21S (via GEODATA)", ["EPSG:31982", "EPSG:31983"]
        if "31983" in geodata_crs_str or "23S" in geodata_crs_str:
            return "SUCCESS", "EPSG:31983", "SIRGAS 2000 / UTM zone 23S (via GEODATA)", ["EPSG:31981", "EPSG:31982"]

    # 2. Heurística baseada nas coordenadas do Bounding Box
    min_x, min_y, max_x, max_y = bbox
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    # A. Verificação de Coordenadas Geográficas (Graus Decimais entre -180 e 180 / -90 e 90)
    if -180.0 <= center_x <= 180.0 and -90.0 <= center_y <= 90.0:
        # Se os limites estiverem no Brasil, sugerimos SIRGAS 2000 Geográficas (EPSG:4674)
        if -75.0 <= center_x <= -35.0 and -35.0 <= center_y <= 5.0:
            logger.info("Heurística: Coordenadas Geográficas no Brasil detectadas.")
            return "SUCCESS", "EPSG:4674", "SIRGAS 2000 / Coordenadas Geográficas", ["EPSG:4326"]
        
        logger.info("Heurística: Coordenadas Geográficas Globais (WGS 84) detectadas.")
        return "SUCCESS", "EPSG:4326", "WGS 84 / Coordenadas Geográficas", ["EPSG:4674"]

    # B. Verificação de Coordenadas Projetadas UTM (Faixa do Sul do Brasil)
    # Northing (Y) entre 6.000.000m e 8.500.000m e Easting (X) entre 150.000m e 850.000m
    elif 150000 <= center_x <= 850000 and 6000000 <= center_y <= 8500000:
        logger.info("Heurística: Coordenadas Projetadas UTM (Brasil) detectadas.")
        # Padrão é a zona 22S (PR, SC, RS, SP) - EPSG:31982. Oferecemos 21S e 23S como alternativas.
        return (
            "SUCCESS",
            "EPSG:31982",
            "SIRGAS 2000 / UTM zone 22S (Sul do Brasil)",
            ["EPSG:31981", "EPSG:31983"]
        )

    # C. Verificação de Coordenadas Locais (Valores pequenos perto da origem 0,0)
    elif abs(center_x) < 100000 and abs(center_y) < 100000:
        logger.info("Heurística: Coordenadas Locais (sem georreferenciamento).")
        return (
            "WARNING",
            None,
            "Coordenadas locais ou projeto sem georreferenciamento!",
            []
        )

    # D. Inconsistência ou CRS Indefinido
    logger.warning(f"Heurística: Coordenadas fora de faixas conhecidas. Centro: ({center_x}, {center_y})")
    return (
        "WARNING",
        None,
        "Coordenadas fora da faixa UTM Sul Brasil ou CRS inconsistente!",
        []
    )
