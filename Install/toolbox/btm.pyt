# -*- coding: utf-8 -*-

import os
import math
import string
import sys
import re

import arcpy
from arcpy.sa import *

import xml.etree.cElementTree as et
import glob

# import our local directory so we can import internal modules
local_path = os.path.dirname(__file__)
sys.path.insert(0, local_path)

# status messages
MSG_INVALID_GRID = "ESRI GRIDs must >= 13 characters and contain only " \
                   "letters, numbers and the underscore ('_') character."
MSG_INVALID_RADIUS = "Outer radius must exceed inner radius."

def raster_is_grid(raster_path):
    is_grid = False
    ext = os.path.splitext(raster_path)[1]
    # if the file has a GRID-like name but exists within a GDB, its a-ok
    if ext == "" and raster_path.lower().find(".gdb") == -1:
        is_grid = True
    return is_grid

# Validate ESRI GRID filenames. The file doesn't exist, so use naming to 
# validate a potential name.
def valid_grid_name(raster_path):
    valid = True
    # GRIDs are the default for any file without a trailing extension.
    if raster_is_grid(raster_path):
        if len(raster_path) > 128:
            valid = False
        else:
            grid_name = os.path.basename(raster_path)
            """
            Encode all the rules into a regular expression:
             - no longer than 13 characters
             - must start with a letter
             - only letters, numbers, and underscores.
            """
            grid_regex = '^[A-Za-z]{1}[A-Za-z0-9_]{0,12}$'
            if re.match(grid_regex, grid_name) is None:
                valid = False

    return valid

# get rid of problematical tags for revision control.
def metadata(update=True):
    if not update:
        try:
            pyt_xmls = glob.glob(os.path.join(local_path, "*.pyt.xml"))
            for xml_path in pyt_xmls:
                tree = et.parse(xml_path)
                esri = tree.find('Esri')
                mod_date = esri.find('ModDate')
                mod_time = esri.find('ModTime')
                if mod_date is not None:
                    esri.remove(mod_date)
                if mod_time is not None:
                    esri.remove(mod_time)
                tree.write(xml_path)
        except Exception as e:
            pass

# Check out any necessary licenses
arcpy.CheckOutExtension("Spatial")

class Toolbox(object):
    def __init__(self):
        self.label = u'Benthic Terrain Modeler'
        self.alias = ''
        self.tools = [broadscalebpi, finescalebpi, standardizebpi, btmslope, zoneclassification, terrainruggedness, depthstatistics]

# tools below this section, one class per tool.

class broadscalebpi(object):
    """c:\data\arcgis\addins\btm\toolbox\BTM.tbx\broadscalebpi"""
    class ToolValidator:
      """Class for validating a tool's parameter values and controlling
      the behavior of the tool's dialog."""
    
      def __init__(self, parameters):
        """Setup arcpy and the list of tool parameters."""
        self.params = parameters
    
      def initializeParameters(self):
        """Refine the properties of a tool's parameters.  This method is
        called when the tool is opened."""
        return
    
      def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parmater
        has been changed."""
        return
         
      def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return
    
    def __init__(self):
        self.label = u'Build Broad Scale BPI'
        self.description = u'The concept of bathymetric position is central to the benthic\r\nterrain classification process that is utilized by the BTM.\r\nBathymetric Position Index (BPI) is a measure of where a\r\nreferenced location is relative to the locations surrounding it.\r\nBPI is derived from an input bathymetric data set and itself is a modification of the topographic position index (TPI) algorithm that is used in the terrestrial environment. The application of TPI to develop terrain classifications was explored and developed by Andrew Weiss during his study of terrestrial watersheds in Central Oregon (Weiss 2001). These\r\napplications can be carried into the benthic environment\r\nthrough BPI.\r\n\r\nA broad-scale BPI data set allows you to identify larger features within the benthic landscape.'
        self.canRunInBackground = False
    def getParameterInfo(self):
        # Input_bathymetric_raster
        input_raster = arcpy.Parameter()
        input_raster.name = u'Input_bathymetric_raster'
        input_raster.displayName = u'Input bathymetric raster'
        input_raster.parameterType = 'Required'
        input_raster.direction = 'Input'
        input_raster.datatype = u'Raster Layer'

        # Inner_radius
        inner_radius = arcpy.Parameter()
        inner_radius.name = u'Inner_radius'
        inner_radius.displayName = u'Inner radius'
        inner_radius.parameterType = 'Required'
        inner_radius.direction = 'Input'
        inner_radius.datatype = u'Long'

        # Outer_radius
        outer_radius = arcpy.Parameter()
        outer_radius.name = u'Outer_radius'
        outer_radius.displayName = u'Outer radius'
        outer_radius.parameterType = 'Required'
        outer_radius.direction = 'Input'
        outer_radius.datatype = u'Long'

        # Scale Factor
        scale_factor = arcpy.Parameter()
        scale_factor.name = 'Scale_factor'
        scale_factor.displayName = 'Scale factor'
        scale_factor.parameterType = 'Optional'
        scale_factor.datatype = 'Long'
        scale_factor.enabled = False

        # Output_raster
        output_raster = arcpy.Parameter()
        output_raster.name = u'Output_raster'
        output_raster.displayName = u'Output raster'
        output_raster.parameterType = 'Required'
        output_raster.direction = 'Output'
        output_raster.datatype = u'Raster Dataset'

        return [input_raster, inner_radius, outer_radius, scale_factor, output_raster]

    def isLicensed(self):
        return True
    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)

        # parameter names
        cols = ['bathy', 'inner', 'outer', 'scale_factor', 'output']
        outer_radius = parameters[cols.index('outer')].valueAsText
        bathy = parameters[cols.index('bathy')].valueAsText

        if outer_radius is not None and bathy is not None:
            raster_desc = arcpy.Describe(bathy)
            # get the cellsize of the input raster; assume same in X & Y
            cellsize = raster_desc.meanCellHeight
            # calculate our 'scale factor':
            scale_factor = math.ceil(float(cellsize) * int(outer_radius) - 0.5)
            # try modifying our scale factor
            parameters[cols.index('scale_factor')].value = scale_factor

        if validator:
            return validator(parameters).updateParameters()

    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        inner_radius = parameters[1].valueAsText
        outer_radius = parameters[2].valueAsText
        output = parameters[4].valueAsText

        if outer_radius is not None and inner_radius is not None:
            inner_rad = int(inner_radius)
            outer_rad = int(outer_radius)
            # test that the outer radius exceeds the inner radius.
            if inner_rad >= outer_rad:
                parameters[2].setErrorMessage(MSG_INVALID_RADIUS)

        # validate the output GRID name
        if output is not None:
            if not valid_grid_name(output):
                parameters[4].setErrorMessage(MSG_INVALID_GRID)

        if validator:
            return validator(parameters).updateMessages()
 
    def execute(self, parameters, messages):
        # run related python script with selected input parameters
        from scripts import bpi
        bpi.main(
            bathy=parameters[0].valueAsText,
            inner_radius=parameters[1].valueAsText,
            outer_radius=parameters[2].valueAsText,
            out_raster=parameters[4].valueAsText,
	    bpi_type='broad')

class finescalebpi(object):
    """c:\data\arcgis\addins\btm\toolbox\BTM.tbx\finescalebpi"""
    class ToolValidator:
      """Class for validating a tool's parameter values and controlling
      the behavior of the tool's dialog."""
    
      def __init__(self, parameters):
        """Setup arcpy and the list of tool parameters."""
        self.params = parameters

      def initializeParameters(self):
        """Refine the properties of a tool's parameters.  This method is
        called when the tool is opened."""
        return
    
      def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parmater
        has been changed."""
        return
    
      def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return
    
    def __init__(self):
        self.label = u'Build Fine Scale BPI'
        self.description = u'The concept of bathymetric position is central to the benthic\r\nterrain classification process that is utilized by the BTM.\r\nBathymetric Position Index (BPI) is a measure of where a\r\nreferenced location is relative to the locations surrounding it.\r\nBPI is derived from an input bathymetric data set and itself is a modification of the topographic position index (TPI) algorithm that is used in the terrestrial environment. The application of TPI to develop terrain classifications was explored and developed by Andrew Weiss during his study of terrestrial watersheds in Central Oregon (Weiss 2001). These\r\napplications can be carried into the benthic environment\r\nthrough BPI.\r\n\r\nA fine-scale BPI data set allows you to identify smaller features within the benthic landscape.'
        self.canRunInBackground = False
 
    def getParameterInfo(self):
        # Input_bathymetric_raster
        input_raster = arcpy.Parameter()
        input_raster.name = u'Input_bathymetric_raster'
        input_raster.displayName = u'Input bathymetric raster'
        input_raster.parameterType = 'Required'
        input_raster.direction = 'Input'
        input_raster.datatype = u'Raster Layer'

        # Inner_radius
        inner_radius = arcpy.Parameter()
        inner_radius.name = u'Inner_radius'
        inner_radius.displayName = u'Inner radius'
        inner_radius.parameterType = 'Required'
        inner_radius.direction = 'Input'
        inner_radius.datatype = u'Long'

        # Outer_radius
        outer_radius = arcpy.Parameter()
        outer_radius.name = u'Outer_radius'
        outer_radius.displayName = u'Outer radius'
        outer_radius.parameterType = 'Required'
        outer_radius.direction = 'Input'
        outer_radius.datatype = u'Long'

        # Scale Factor
        scale_factor = arcpy.Parameter()
        scale_factor.name = 'Scale_factor'
        scale_factor.displayName = 'Scale factor'
        scale_factor.parameterType = 'Optional'
        scale_factor.datatype = 'Long'
        scale_factor.enabled = False

        # Output_raster
        output_raster = arcpy.Parameter()
        output_raster.name = u'Output_raster'
        output_raster.displayName = u'Output raster'
        output_raster.parameterType = 'Required'
        output_raster.direction = 'Output'
        output_raster.datatype = u'Raster Dataset'

        # TODO: implement mutlvalue support
        multivalue = arcpy.Parameter()
        multivalue.name = u'Test multi'
        multivalue.displayName = u'Test multi'
        multivalue.parameterType = 'Optional'
        multivalue.direction = 'Input'
        multivalue.datatype = u'Any Value'

        return [input_raster, inner_radius, outer_radius, scale_factor, output_raster]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)

        # parameter names
        cols = ['bathy', 'inner', 'outer', 'scale_factor', 'output']
        outer_radius = parameters[cols.index('outer')].valueAsText
        bathy = parameters[cols.index('bathy')].valueAsText
        if outer_radius is not None and bathy is not None:
            raster_desc = arcpy.Describe(bathy)
            # get the cellsize of the input raster; assume same in X & Y
            cellsize = raster_desc.meanCellHeight
            # calculate our 'scale factor':
            scale_factor = math.ceil(float(cellsize) * int(outer_radius) - 0.5)
            # try modifying our scale factor
            parameters[cols.index('scale_factor')].value = scale_factor

        if validator:
             return validator(parameters).updateParameters()

    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        inner_radius = parameters[1].valueAsText
        outer_radius = parameters[2].valueAsText
        output = parameters[4].valueAsText
        if outer_radius is not None and inner_radius is not None:
            inner_rad = int(inner_radius)
            outer_rad = int(outer_radius)
            # test that the outer radius exceeds the inner radius.
            if inner_rad >= outer_rad:
                parameters[2].setErrorMessage(MSG_INVALID_RADIUS)

        # validate the output GRID name
        if output is not None:
            if not valid_grid_name(output):
                parameters[4].setErrorMessage(MSG_INVALID_GRID)

        if validator:
            return validator(parameters).updateMessages()
 
    def execute(self, parameters, messages):
        # run related python script with selected input parameters
        from scripts import bpi
        bpi.main(
            bathy=parameters[0].valueAsText,
            inner_radius=parameters[1].valueAsText,
            outer_radius=parameters[2].valueAsText,
            out_raster=parameters[4].valueAsText,
	    bpi_type='fine')
    
class standardizebpi(object):
    """c:\data\arcgis\addins\btm\toolbox\BTM.tbx\standardizebpi"""
    def __init__(self):
        self.label = u'Standardize BPIs'
        self.canRunInBackground = False
    def getParameterInfo(self):
        # Input_BPI_raster
        broad_raster = arcpy.Parameter()
        broad_raster.name = u'Broad_BPI_raster'
        broad_raster.displayName = u'Broad BPI raster'
        broad_raster.parameterType = 'Required'
        broad_raster.direction = 'Input'
        broad_raster.datatype = u'Raster Layer'

        # dervied statistics
        broad_mean = arcpy.Parameter()
        broad_mean.name = 'Broad_BPI_Mean'
        broad_mean.displayName = 'Broad BPI Mean'
        broad_mean.parameterType = 'Required'
        broad_mean.datatype = 'Double'
        broad_mean.enabled = False
        broad_mean.value = 0

        broad_stddev = arcpy.Parameter()
        broad_stddev.name = 'Broad_BPI_Standard_deviation'
        broad_stddev.displayName = 'Broad BPI Standard Deviation'
        broad_stddev.parameterType = 'Required'
        broad_stddev.datatype = 'Double'
        broad_stddev.enabled = False
        broad_stddev.value = 0

        # Output_raster
        broad_std_output = arcpy.Parameter()
        broad_std_output.name = u'Output_broad_raster'
        broad_std_output.displayName = u'Output Standardized Broad BPI raster'
        broad_std_output.parameterType = 'Required'
        broad_std_output.direction = 'Output'
        broad_std_output.datatype = u'Raster Dataset'

        # Input_BPI_raster
        fine_raster = arcpy.Parameter()
        fine_raster.name = u'Fine_BPI_raster'
        fine_raster.displayName = u'Fine BPI raster'
        fine_raster.parameterType = 'Required'
        fine_raster.direction = 'Input'
        fine_raster.datatype = u'Raster Layer'

        # dervied statistics
        fine_mean = arcpy.Parameter()
        fine_mean.name = 'Fine_BPI_Mean'
        fine_mean.displayName = 'Fine BPI Mean'
        fine_mean.parameterType = 'Required'
        fine_mean.datatype = 'Double'
        fine_mean.enabled = False
        fine_mean.value = 0

        fine_stddev = arcpy.Parameter()
        fine_stddev.name = 'Fine_BPI_Standard_deviation'
        fine_stddev.displayName = 'Fine BPI Standard Deviation'
        fine_stddev.parameterType = 'Required'
        fine_stddev.datatype = 'Double'
        fine_stddev.enabled = False
        fine_stddev.value = 0

        # Output_raster
        fine_std_output = arcpy.Parameter()
        fine_std_output.name = u'Output_fine_raster'
        fine_std_output.displayName = u'Output Standardized Fine BPI raster'
        fine_std_output.parameterType = 'Required'
        fine_std_output.direction = 'Output'
        fine_std_output.datatype = u'Raster Dataset'

        return [broad_raster, broad_mean, broad_stddev, broad_std_output, fine_raster, fine_mean, fine_stddev, fine_std_output]

    def isLicensed(self):
        return True
    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()
    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)

        # parameter names
        cols = ['broad_input', 'broad_mean', 'broad_stddev', 'broad_output', \
                'fine_input', 'fine_mean', 'fine_stddev', 'fine_output']

        for label in ['broad', 'fine']: 
            input_raster = parameters[cols.index(label + '_input')].valueAsText
            if input_raster is not None:
                (mean, stddev) = self.getRasterStats(input_raster)
                if mean is not None:
                    # try modifying our variables
                    parameters[cols.index(label + '_mean')].value = mean 
                    parameters[cols.index(label + '_stddev')].value = stddev 

            # Validate GRID outputs.
            out_param = cols.index(label + '_output') 
            output_raster = parameters[out_param].valueAsText
            if output_raster is not None:
                if not valid_grid_name(output_raster):
                    parameters[out_param].setErrorMessage(MSG_INVALID_GRID)

        if validator:
             return validator(parameters).updateMessages()

    def getRasterStats(self, input_raster = None):
        # What kinds of inputs can we expect to compute statistics on?
        VALID_RASTER_TYPES = ['RasterDataset', 'RasterLayer']

        result = (None, None)
        if input_raster is not None:
            try:
                raster_desc = arcpy.Describe(input_raster)
                if raster_desc.dataType in VALID_RASTER_TYPES: 
                    mean_res = arcpy.GetRasterProperties_management(input_raster, "MEAN")
                    mean = float(mean_res.getOutput(0))
                    stddev_res = arcpy.GetRasterProperties_management(input_raster, "STD")
                    stddev = float(stddev_res.getOutput(0))
                    result = (mean, stddev)
            except:
                # check for raster existence, when running as a model the 'result'
                # may be set, but not actually exist, causing these steps to fail.
                pass
        return result

    def execute(self, parameters, messages):
        # run related python script with selected input parameters
        from scripts import standardize_bpi_grids
        # run for broad raster...
        standardize_bpi_grids.main(
            bpi_raster=parameters[0].valueAsText,
            out_raster=parameters[3].valueAsText)
        #  ...and again for fine raster.
        standardize_bpi_grids.main(
            bpi_raster=parameters[4].valueAsText,
            out_raster=parameters[7].valueAsText)
 
class btmslope(object):
    """c:\data\arcgis\addins\btm\toolbox\BTM.tbx\slope"""
    def __init__(self):
        self.label = u'Calculate Slope'
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Input_bathymetric_raster
        input_raster = arcpy.Parameter()
        input_raster.name = u'Input_bathymetric_raster'
        input_raster.displayName = u'Input bathymetric raster'
        input_raster.parameterType = 'Required'
        input_raster.direction = 'Input'
        input_raster.datatype = u'Raster Layer'

        # Output_raster
        output_raster = arcpy.Parameter()
        output_raster.name = u'Output_raster'
        output_raster.displayName = u'Output raster'
        output_raster.parameterType = 'Required'
        output_raster.direction = 'Output'
        output_raster.datatype = u'Raster Dataset'

        return [input_raster, output_raster]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()

    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)

        output = parameters[1].valueAsText
        # validate the output GRID name
        if output is not None:
            if not valid_grid_name(output):
                parameters[1].setErrorMessage(MSG_INVALID_GRID)

        if validator:
             return validator(parameters).updateMessages()

    def execute(self, parameters, messages):
        # run related python script with selected input parameters
        from scripts import slope
        slope.main(
            bathy=parameters[0].valueAsText,
            out_raster=parameters[1].valueAsText)

class zoneclassification(object):
    """c:\data\arcgis\addins\btm\toolbox\BTM.tbx\zoneclassification"""
    def __init__(self):
        self.label = u'Zone Classification Builder'
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Classification Dictionary
        class_dict = arcpy.Parameter()
        class_dict.name = u'Classification_dictionary'
        class_dict.displayName = u'Classification dictionary'
        class_dict.direction = 'Input'
        class_dict.datatype = u'File'
        class_dict.parameterType = 'Required'

        # classification dictionary must be of the types we parse.
        class_dict.filter.list = ['csv', 'xls', 'xlsx', 'xml']

        # Standardized broad-scale BPI raster
        broad_bpi = arcpy.Parameter()
        broad_bpi.name = u'Standardized_broad-scale_BPI_raster'
        broad_bpi.displayName = u'Standardized broad-scale BPI raster'
        broad_bpi.parameterType = 'Required'
        broad_bpi.direction = 'Input'
        broad_bpi.datatype = u'Raster Layer'

        # Standardized fine-scale BPI raster
        fine_bpi = arcpy.Parameter()
        fine_bpi.name = u'Standardized_fine-scale_BPI_raster'
        fine_bpi.displayName = u'Standardized fine-scale BPI raster'
        fine_bpi.parameterType = 'Required'
        fine_bpi.direction = 'Input'
        fine_bpi.datatype = u'Raster Layer'

        # Slope_raster
        slope = arcpy.Parameter()
        slope.name = u'Slope_raster'
        slope.displayName = u'Slope raster'
        slope.parameterType = 'Required'
        slope.direction = 'Input'
        slope.datatype = u'Raster Layer'

        # Bathymetry raster
        bathy= arcpy.Parameter()
        bathy.name = u'Bathymetry_raster'
        bathy.displayName = u'Bathymetry raster'
        bathy.parameterType = 'Required'
        bathy.direction = 'Input'
        bathy.datatype = u'Raster Layer'

        # Output_raster
        zones_raster= arcpy.Parameter()
        zones_raster.name = u'Output_zones_raster'
        zones_raster.displayName = u'Output Zones Raster'
        zones_raster.parameterType = 'Required'
        zones_raster.direction = 'Output.'
        zones_raster.datatype = u'Raster Dataset'
        return [class_dict, broad_bpi, fine_bpi, slope, bathy, zones_raster]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()

    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        output = parameters[5].valueAsText
        # validate the output GRID name
        if output is not None:
            if not valid_grid_name(output):
                parameters[5].setErrorMessage(MSG_INVALID_GRID)

        if validator:
             return validator(parameters).updateMessages()

    def execute(self, parameters, messages):
        from scripts import classify 
        classify.main(
            classification_file=parameters[0].valueAsText,
            bpi_broad=parameters[1].valueAsText,
            bpi_fine=parameters[2].valueAsText,
            slope=parameters[3].valueAsText,
            bathy=parameters[4].valueAsText,
            out_raster=parameters[5].valueAsText)


class structureclassification(object):
    """c:\data\arcgis\addins\btm\toolbox\BTM.tbx\structureclassification"""
    def __init__(self):
        self.label = u'Structure Classification Builder'
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Standardized_broad-scale_BPI_raster
        broad_bpi = arcpy.Parameter()
        broad_bpi.name = u'Standardized_broad-scale_BPI_raster'
        broad_bpi.displayName = u'Standardized broad-scale BPI raster'
        broad_bpi.parameterType = 'Required'
        broad_bpi.direction = 'Input'
        broad_bpi.datatype = u'Raster Layer'

        # Broad-scale_BPI_standard_deviation_break
        broad_stddev = arcpy.Parameter()
        broad_stddev.name = u'Broad-scale_BPI_standard_deviation_break'
        broad_stddev.displayName = u'Broad-scale BPI standard deviation break'
        broad_stddev.parameterType = 'Required'
        broad_stddev.direction = 'Input'
        broad_stddev.datatype = u'Double'

        # Standardized_fine-scale_BPI_raster
        fine_bpi = arcpy.Parameter()
        fine_bpi.name = u'Standardized_fine-scale_BPI_raster'
        fine_bpi.displayName = u'Standardized fine-scale BPI raster'
        fine_bpi.parameterType = 'Required'
        fine_bpi.direction = 'Input'
        fine_bpi.datatype = u'Raster Layer'

        # Fine-scale_BPI_standard_deviation_break
        fine_stddev = arcpy.Parameter()
        fine_stddev.name = u'Fine-scale_BPI_standard_deviation_break'
        fine_stddev.displayName = u'Fine-scale BPI standard deviation break'
        fine_stddev.parameterType = 'Required'
        fine_stddev.direction = 'Input'
        fine_stddev.datatype = u'Double'

        # Slope_raster
        slope = arcpy.Parameter()
        slope.name = u'Slope_raster'
        slope.displayName = u'Slope raster'
        slope.parameterType = 'Required'
        slope.direction = 'Input'
        slope.datatype = u'Raster Layer'

        # Slope_value__in_degrees__indicating_a_gentle_slope
        slope_gentle = arcpy.Parameter()
        slope_gentle.name = u'Slope_value__in_degrees__indicating_a_gentle_slope'
        slope_gentle.displayName = u'Slope value (in degrees) indicating a gentle slope'
        slope_gentle.parameterType = 'Required'
        slope_gentle.direction = 'Input'
        slope_gentle.datatype = u'Double'

        # Slope_value__in_degrees__indicating_a_steep_slope
        slope_steep = arcpy.Parameter()
        slope_steep.name = u'Slope_value__in_degrees__indicating_a_steep_slope'
        slope_steep.displayName = u'Slope value (in degrees) indicating a steep slope'
        slope_steep.parameterType = 'Required'
        slope_steep.direction = 'Input'
        slope_steep.datatype = u'Double'

        # Bathymetric_raster
        bathy = arcpy.Parameter()
        bathy.name = u'Bathymetric_raster'
        bathy.displayName = u'Bathymetric raster'
        bathy.parameterType = 'Required'
        bathy.direction = 'Input'
        bathy.datatype = u'Raster Layer'

        # Depth_indicating_break_between_shelf_and_broad_flat
        broad_vs_flat = arcpy.Parameter()
        broad_vs_flat.name = u'Depth_indicating_break_between_shelf_and_broad_flat'
        broad_vs_flat.displayName = u'Depth indicating break between shelf and broad flat'
        broad_vs_flat.parameterType = 'Required'
        broad_vs_flat.direction = 'Input'
        broad_vs_flat.datatype = u'Double'

        # Output_raster
        output_raster = arcpy.Parameter()
        output_raster.name = u'Output_raster'
        output_raster.displayName = u'Output raster'
        output_raster.parameterType = 'Required'
        output_raster.direction = 'Output'
        output_raster.datatype = u'Raster Dataset'

        return [broad_bpi, broad_stddev, fine_bpi, fine_stddev, slope, slope_gentle, slope_steep, bathy, broad_vs_flat, output_raster]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()

    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateMessages()

    def execute(self, parameters, messages):
        pass

class terrainruggedness(object):
    """c:\data\arcgis\addins\btm\toolbox\BTM.tbx\Ruggedness(VRM)"""
    class ToolValidator:
      """Class for validating a tool's parameter values and controlling
      the behavior of the tool's dialog."""
    
      def __init__(self, parameters):
        """Setup arcpy and the list of tool parameters."""
        self.params = parameters
    
      def initializeParameters(self):
        """Refine the properties of a tool's parameters.  This method is
        called when the tool is opened."""
        return
    
      def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parmater
        has been changed."""
        return
    
      def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return
    
    def __init__(self):
        self.label = u'Terrain Ruggedness (VRM)'
        self.description = 'Measure terrain ruggedness by calculating the vecotr ruggedness measure (VRM), as described in Sappington et al, 2007.'
        self.canRunInBackground = False
    def getParameterInfo(self):
        # Bathymetry_Raster
        input_raster = arcpy.Parameter()
        input_raster.name = u'Bathymetry_Raster'
        input_raster.displayName = u'Bathymetry Raster'
        input_raster.parameterType = 'Required'
        input_raster.direction = 'Input'
        input_raster.datatype = u'Raster Layer'

        # Neighborhood_Size
        neighborhood = arcpy.Parameter()
        neighborhood.name = u'Neighborhood_Size'
        neighborhood.displayName = u'Neighborhood Size'
        neighborhood.parameterType = 'Required'
        neighborhood.direction = 'Input'
        neighborhood.datatype = u'Long'

        # Output_Workspace
        workspace = arcpy.Parameter()
        workspace.name = u'Temporary_Workspace'
        workspace.displayName = u'Temporary Workspace'
        workspace.parameterType = 'Required'
        workspace.direction = 'Input'
        workspace.datatype = u'Workspace'

        # Output_Raster
        output_raster = arcpy.Parameter()
        output_raster.name = u'Output_Raster'
        output_raster.displayName = u'Output Raster'
        output_raster.parameterType = 'Required'
        output_raster.direction = 'Output'
        output_raster.datatype = u'Raster Dataset'

        return [input_raster, neighborhood, workspace, output_raster]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()

    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        output = parameters[3].valueAsText
        # validate the output GRID name
        if output is not None:
            if not valid_grid_name(output):
                parameters[3].setErrorMessage(MSG_INVALID_GRID)
        if validator:
             return validator(parameters).updateMessages()

    def execute(self, parameters, messages):
        # run related python script with selected input parameters
        from scripts import ruggedness
        ruggedness.main(
                InRaster=parameters[0].valueAsText, 
                NeighborhoodSize=parameters[1].valueAsText,
                OutWorkspace=parameters[2].valueAsText,
                OutRaster=parameters[3].valueAsText)
 
class depthstatistics(object):
    """ Depth Statistics computes a suite of summary statistics. This initial
        version works on a fixed window size, but user feedback has indicated 
        a more general version which supported multiple window sizes, 
        including vector-based ones, would be preferable.

        Also, this current version uses focal tools, but could be computed in
        one pass using numpy instead, but memory considerations would need
        to be taken into account, or the algorithm would need to operate on
        blocks within the data. see 'rugosity.py' script an example of this 
        approach, can use NumPyArrayToRaster and vice versa.
    """
       

    class ToolValidator:
      """Class for validating a tool's parameter values and controlling
      the behavior of the tool's dialog."""

      def __init__(self, parameters):
        """Setup arcpy and the list of tool parameters."""
        self.params = parameters

      def initializeParameters(self):
        """Refine the properties of a tool's parameters.  This method is
        called when the tool is opened."""
        return

      def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parmater
        has been changed."""
        return

      def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def __init__(self):
        self.label = u'Depth Statistics'
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Bathymetry_Raster 
        input_raster = arcpy.Parameter()
        input_raster.name = u'Bathymetry_Raster'
        input_raster.displayName = u'Bathymetry Raster'
        input_raster.parameterType = 'Required'
        input_raster.direction = 'Input'
        input_raster.datatype = 'Raster Layer'

        # Neighborhood_Size
        neighborhood = arcpy.Parameter()
        neighborhood.name = u'Neighborhood_Size'
        neighborhood.displayName = u'Neighborhood Size'
        neighborhood.parameterType = 'Required'
        neighborhood.direction = 'Input'
        neighborhood.datatype = 'Long'

        # Output_Workspace
        output_workspace = arcpy.Parameter()
        output_workspace.name = u'Output_Workspace'
        output_workspace.displayName = u'Output Workspace'
        output_workspace.parameterType = 'Required'
        output_workspace.direction = 'Input'
        output_workspace.datatype = 'Workspace'

       # Statistics to Compute
        statistics = arcpy.Parameter()
        statistics.name = u'Statistics_Computed'
        statistics.displayName = u'Statistics to Compute'
        statistics.parameterType = 'Required'
        statistics.direction = 'Input'
        statistics.datatype = 'String'
        statistics.multiValue = True
        statistics.filter.list = ['Mean Depth', 'Variance', 'Standard Deviation']

        return [input_raster, neighborhood, output_workspace, statistics]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()

    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateMessages()

    def execute(self, parameters, messages):
        # run related python script with selected input parameters
        from scripts import depth_statistics
        depth_statistics.main(
                in_raster = parameters[0].valueAsText,
                neighborhood_size = parameters[1].valueAsText,
                out_workspace = parameters[2].valueAsText,
                out_stats_raw = parameters[3].valueAsText)
