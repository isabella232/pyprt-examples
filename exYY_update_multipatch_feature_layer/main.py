import shutil
import tempfile
from pathlib import Path
import getpass

import arcgis.features
import keyring
import requests
from arcgis.gis import GIS
import pyprt
from pyprt.pyprt_arcgis import arcgis_to_pyprt

from gdal import ogr

SCRIPT_DIR = Path(__file__).resolve().parent

TARGET_GDB_TEMPLATE_PATH = SCRIPT_DIR.joinpath('pyprt_update_test_target.gdb')
GDB_DRIVER = ogr.GetDriverByName("FileGDB")

SHAPE_BUFFER_ENCODER_ID = 'com.esri.prt.codecs.ShapeBufferEncoder'
MULTIPATCH_DATA_FILE = "-1_model"  # don't ask ;-)

portal_url = 'https://zurich.maps.arcgis.com/sharing/generateToken'
username = 'simon_zurich'

source_feature_layer_id = 'b5677b032c224d0a87b7034db72b4b74'
target_gdb_id = 'f95d655d60f94a94ba7861039d11c8b0'
target_feature_layer_id = 'abfccb9ee60643fd82fef77c000aa993'


def update_multipatch_feature_layer():
    password = keyring.get_password("zurich.maps.arcgis.com", username)
    gis = GIS(username=username, password=password, verify_cert=False)

    source_feature_layer_collection = gis.content.get(source_feature_layer_id)
    source_feature_layer = source_feature_layer_collection.layers[0]

    source_features = source_feature_layer.query(return_z=True)
    print(f"got {len(source_features)} source feature(s)")

    temp_dir_obj = tempfile.TemporaryDirectory()
    temp_dir = Path(temp_dir_obj.name)
    print(f'temp_dir = {temp_dir}')

    pyprt.initialize_prt()

    attrs = [{'/enc/layerUID': '68dca8be-5b69-41dd-8dee-b09ca571c1a9'}]  # random UUID
    pyprt_shapebuffer_options = {'outputPath': str(temp_dir)}
    rpk = SCRIPT_DIR.joinpath('extrude.rpk')

    temp_filegdb_path = temp_dir.joinpath('temp.gdb')
    shutil.copytree(TARGET_GDB_TEMPLATE_PATH, temp_filegdb_path)

    gdb = GDB_DRIVER.Open(str(temp_filegdb_path), 0)
    multipatch_layer = gdb.GetLayerByName("pyprt_update_test_ProcedurallyGeneratedMultipatches")
    print(multipatch_layer)

    temp_multipatch_data_path = temp_dir.joinpath(MULTIPATCH_DATA_FILE)

    # workaround: generate features one-by-one to avoid overwriting the resulting multipatch data files
    for source_feature in source_features:
        oid = source_feature.get_value('objectid')
        pyprt_initial_shapes = arcgis_to_pyprt(arcgis.features.FeatureSet([source_feature]))
        pyprt_model_generator = pyprt.ModelGenerator(pyprt_initial_shapes)
        pyprt_model_generator.generate_model(attrs, str(rpk), SHAPE_BUFFER_ENCODER_ID, pyprt_shapebuffer_options)

        with open(temp_multipatch_data_path, mode='rb') as multipatch_file:  # b is important -> binary
            multipatch_data = multipatch_file.read()
            print(f"read multipatch: {len(multipatch_data)} bytes")

        gdb_feature = multipatch_layer.GetNextFeature()
        gdb_feature_geo = gdb_feature.GetGeometryRef()
        gdb_feature.SetGeometry(multipatch_data)



    target_feature_layer_collection = gis.content.get(target_feature_layer_id)
    target_feature_layer = target_feature_layer_collection.layers[0]

    #fgdb_upload_id = gis.content.add(data=)
    #target_feature_layer.append(item_id=fgdb_upload_id, upsert=True, update_geometry=True, upload_format='filegdb', upsert_matching_field='objectid', source_table_name="pyprt_tests", return_messages=True)


    pyprt.shutdown_prt()
    temp_dir.cleanup()


if __name__ == '__main__':
    update_multipatch_feature_layer()
