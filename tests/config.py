# our constants.

import os

local_path = os.path.dirname(__file__)
data_path = os.path.join(local_path, 'data')

base_xml = os.path.abspath(os.path.join(data_path, 'fagatelebay.xml'))
base_csv = os.path.abspath(os.path.join(data_path, 'fagatelebay.csv'))
base_excel = os.path.abspath(os.path.join(data_path, 'fagatelebay.xlsx'))
malformed_csv = os.path.abspath(
        os.path.join(data_path, 'missing_comma_zone.csv'))
zones_excel = os.path.abspath(os.path.join(data_path, 'fagatelebay_zone.xlsx'))
zones_xml = os.path.abspath(os.path.join(data_path, 'fagatelebay_zone.xlsx'))
bathy_raster = os.path.abspath(os.path.join(data_path, 'bathy5m_clip.tif'))

pyt_file = os.path.abspath(
        os.path.join(local_path, '..', 'Install', 'toolbox', 'btm.pyt'))
