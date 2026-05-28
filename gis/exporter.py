import os
import re
import logging
import geopandas as gpd
from collections import defaultdict
from gis.geometry_engine import GeometryFactory

logger = logging.getLogger("geocad_bridge.gis.exporter")

def clean_existing_shapefile(base_path):
    """
    Remove todos os arquivos associados a um Shapefile existente (.shp, .shx, .dbf, etc.)
    para evitar conflitos de gravação.
    """
    root, _ = os.path.splitext(base_path)
    extensions = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".qpj", ".sbx", ".sbn"]
    for ext in extensions:
        file_path = root + ext
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.debug(f"Não foi possível remover arquivo residual {file_path}: {e}")

def re_sub_special_chars(name):
    """
    Limpa o nome da camada substituindo caracteres especiais e espaços por underscores.
    """
    # Substitui caracteres não alfanuméricos por underscore
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    # Remove underscores duplicados consecutivos
    clean = re.sub(r"__+", "_", clean)
    return clean.strip("_")

def export_features_to_shapefiles(features, output_directory, crs_code=None):
    """
    Exporta uma lista de feições brutas obtidas do CAD para arquivos ESRI Shapefile (.shp).
    Cria automaticamente uma pasta chamada 'DWG_Shp' no diretório selecionado.
    Separa os dados por camada do desenho e tipo de geometria (_point, _line, _polygon).
    """
    if not features:
        logger.warning("Nenhuma feição encontrada para exportar.")
        return False

    # 1. Define e cria a pasta destino 'DWG_Shp'
    dwg_shp_dir = os.path.join(output_directory, "DWG_Shp")
    os.makedirs(dwg_shp_dir, exist_ok=True)
    logger.info(f"Diretório de exportação de Shapefiles: {dwg_shp_dir}")

    # 2. Agrupa feições por camada e tipo geométrico
    # groups[(layer, geom_type)] = [feature_dict, ...]
    groups = defaultdict(list)
    for feat in features:
        geom_type = feat.get("geom_type")
        layer = feat.get("layer", "0")
        if geom_type and geom_type != "Unknown":
            groups[(layer, geom_type)].append(feat)

    if not groups:
        logger.warning("Nenhuma geometria válida pôde ser agrupada para exportação.")
        return False

    # Sufixos geométricos padrão conforme exigido
    suffix_map = {
        "Point": "_point.shp",
        "Text": "_text.shp",
        "LineString": "_line.shp",
        "Polygon": "_polygon.shp"
    }

    success_count = 0
    
    for (layer_name, geom_type), feat_list in groups.items():
        try:
            geometries = []
            handles = []
            dxftypes = []
            colors = []
            textos = []
            has_textos = any("texto" in f for f in feat_list)
            
            # Converte coordenadas CAD brutas em objetos Shape/Geom do Shapely
            for f in feat_list:
                geom = GeometryFactory.to_shapely(f["geom_type"], f["coords"])
                if geom:
                    geometries.append(geom)
                    # Shapefile DBF possui limite rígido de 10 caracteres por nome de coluna.
                    # As colunas 'handle', 'dxftype' e 'color' respeitam essa regra perfeitamente.
                    handles.append(f.get("handle", ""))
                    dxftypes.append(f.get("dxftype", ""))
                    colors.append(f.get("color", "#ffffff"))
                    if has_textos:
                        textos.append(f.get("texto", ""))

            if not geometries:
                continue

            # Constrói o GeoDataFrame com a projeção indicada
            data = {
                "handle": handles,
                "dxftype": dxftypes,
                "color": colors
            }
            if has_textos:
                data["texto"] = textos
            
            gdf = gpd.GeoDataFrame(data, geometry=geometries, crs=crs_code)
            
            # Nome do shapefile limpo e em minúsculas
            clean_name = re_sub_special_chars(layer_name).lower()
            filename = f"{clean_name}{suffix_map[geom_type]}"
            shapefile_path = os.path.join(dwg_shp_dir, filename)
            
            logger.info(f"Gravando Shapefile '{filename}' com {len(gdf)} feições...")
            
            # Limpa arquivos residuais antigos do mesmo Shapefile antes de gravar
            clean_existing_shapefile(shapefile_path)

            # Grava no formato ESRI Shapefile usando a engine pyogrio
            gdf.to_file(
                shapefile_path,
                driver="ESRI Shapefile",
                engine="pyogrio"
            )
            success_count += 1
            
        except Exception as e:
            logger.error(f"Falha ao exportar camada Shapefile '{layer_name}' ({geom_type}): {e}", exc_info=True)
            raise

    logger.info(f"Exportação para Shapefiles concluída. {success_count} arquivos gerados em: {dwg_shp_dir}")
    return True
