# @ File(label="Folder with your images", style="directory", description="Input folder") src_dir
# @ File(label="Folder to save your images", style="directory", description="Output folder", required=False) out_dir
# @ String(label="Extension for the images to look for", value="nd2") filename_filter
# @ Integer(label="Channel to use for segmentation", value=1) seg_chnl
# @ Boolean(label="Do channel alignment ?", value=False) do_stackreg
# @ String (label="How to deal with thresholding ?", choices={"Fully automatic", "Manual once and apply to all", "Fully manual"}) thresh_method
# @ RoiManager rm
# ─── IMPORTS ────────────────────────────────────────────────────────────────────

import os
import time
import fnmatch

from ij import IJ
from ij import Prefs
from ij.gui import WaitForUserDialog
from ij.plugin import Duplicator, ImageCalculator

# Bioformats imports
from loci.plugins import BF, LociExporter

from loci.plugins.in import ImporterOptions
from loci.plugins.out import Exporter

from loci.formats.in import MetadataOptions
from loci.formats import ImageReader
from loci.formats import MetadataTools

from java.lang import Double


# ─── FUNCTIONS ──────────────────────────────────────────────────────────────────


def getFileList(directory, filteringString):
    """Get a list of files with the extension

    Parameters
    ----------
    directory : str
        Path of the files to look at
    filteringString : str
        Extension to look for

    Returns
    -------
    list
        List of files with the extension in the folder
    """

    files = []
    for dirpath, dirnames, filenames in os.walk(directory):
        # if out_dir in dirnames: # Ignore destination directory
        # dirnames.remove(OUT_SUBDIR)
        for f in fnmatch.filter(filenames, "*" + filteringString):
            files.append(os.path.join(dirpath, f))
    return files


def BFImport(indivFile):
    """Import using BioFormats

    Parameters
    ----------
    indivFile : str
        Path of the file to open

    Returns
    -------
    imps : ImagePlus
        Image opened via BF
    """
    options = ImporterOptions()
    options.setId(str(indivFile))
    options.setColorMode(ImporterOptions.COLOR_MODE_GRAYSCALE)
    return BF.openImagePlus(options)


def BFExport(imp, savepath):
    """Export using BioFormats

    Parameters
    ----------
    imp : ImagePlus
        ImagePlus of the file to save
    savepath : str
        Path where to save the image

    """
    paramstring = (
        "outfile=["
        + savepath
        + "] windowless=true compression=Uncompressed saveROI=false"
    )

    print("Savepath: ", savepath)
    plugin = LociExporter()
    plugin.arg = paramstring
    exporter = Exporter(plugin, imp)
    exporter.run()


def progress_bar(progress, total, line_number, prefix=""):
    """Progress bar for the IJ log window

    Parameters
    ----------
    progress : int
        Current step of the loop
    total : int
        Total number of steps for the loop
    line_number : int
        Number of the line to be updated
    prefix : str, optional
        Text to use before the progress bar, by default ''
    """

    size = 30
    x = int(size * progress / total)
    IJ.log(
        "\\Update%i:%s\t[%s%s] %i/%i\r"
        % (line_number, prefix, "#" * x, "." * (size - x), progress, total)
    )


def get_series_info_from_ome_metadata(path_to_file):
    """Get the number of series from a file

    Parameters
    ----------
    path_to_file : str
        Path to the file

    Returns
    -------
    int
        Number of series for the file
    """
    reader = ImageReader()
    reader.setFlattenedResolutions(False)
    omeMeta = MetadataTools.createOMEXMLMetadata()
    reader.setMetadataStore(omeMeta)
    reader.setId(path_to_file)
    series_count = reader.getSeriesCount()

    series_index = []
    for i in range(series_count):
        if i == 0:
            resolution_count = 0
            series_index.append(resolution_count)
        else:
            reader.setSeries(i - 1)
            resolution_count += reader.getResolutionCount()
            series_index.append(resolution_count)

    reader.close()

    return series_count, series_index


def open_single_series_with_BF(path_to_file, series_number):
    """Open a single serie for a file using Bio-Formats

    Parameters
    ----------
    path_to_file : str
        Path to the file
    series_number : int
        Number of the serie to open

    Returns
    -------
    ImagePlus
        ImagePlus of the serie
    """
    options = ImporterOptions()
    options.setColorMode(ImporterOptions.COLOR_MODE_COMPOSITE)
    options.setSeriesOn(series_number, True)  # python starts at 0
    # options.setSpecifyRanges(True)
    # options.setCBegin(series_number-1, channel_number-1) # python starts at 0
    # options.setCEnd(series_number-1, channel_number-1)
    # options.setCStep(series_number-1, 1)
    options.setId(path_to_file)
    imps = BF.openImagePlus(options)  # is an array of imp with one entry

    return imps[0]


def check_folder(path):
    """Check if folder exists otherwise creates it

    Parameters
    ----------
    path : str
        Path to check folder or create it
    """
    if not os.path.exists(path):
        os.makedirs(path)


def timed_log(message):
    """Print a log message with a timestamp added

    Parameters
    ----------
    message : str
        Message to print
    """
    IJ.log(time.strftime("%H:%M:%S", time.localtime()) + ": " + message)


# ─── Variables ────────────────────────────────────────────────────────────────

blur_radius = 1.5
laplace_radius = 1
back_subtract = 20

min_display = 0
max_display = 3

# ─── MAIN CODE ──────────────────────────────────────────────────────────────────

IJ.log("\\Clear")
timed_log("Script starting")

# Retrieve list of files
src_dir = str(src_dir)

out_dir = str(out_dir)
files = getFileList(src_dir, filename_filter)

pad_number = 0

thresh_value = 0

# # If the list of files is not empty
if files:
    # For each file finishing with the filtered string
    for file_id, file in enumerate(sorted(files)):
        # Get info for the files
        folder = os.path.dirname(file)
        basename = os.path.basename(file)
        basename = os.path.splitext(basename)[0]

        # Import the file with BioFormats
        progress_bar(file_id + 1, len(files), 1, "Processing: " + str(file_id))
        # IJ.log("\\Update3:Currently opening " + basename + "...")

        series_count, series_index = get_series_info_from_ome_metadata(file)
        if not pad_number:
            pad_number = len(str(series_count))

        for series in range(series_count):
            progress_bar(series + 1, series_count, 2, "Opening series : ")

            imp = open_single_series_with_BF(file, series_index[series])
            # imp.show()
            basename = os.path.basename(file)

            if do_stackreg:
                out_ratio = os.path.join(out_dir, basename + "_ratio_chnlaligned.tif")
                IJ.run(imp, "StackReg", "transformation=[Affine]")
            else:
                out_ratio = os.path.join(out_dir, basename + "_ratio.tif")
            out_calibration = os.path.join(out_dir, basename + "_calibration.tif")

            # sys.exit()

            IJ.run(imp, "32-bit", "")
            IJ.run(imp, "Gaussian Blur...", "sigma=" + str(blur_radius) + " stack")

            imp_c1 = Duplicator().run(imp, 1, 1, 1, 1, 1, 1)
            imp_c1.setTitle("C1")
            imp_c2 = Duplicator().run(imp, 2, 2, 1, 1, 1, 1)
            imp_c2.setTitle("C2")

            imp_segment = Duplicator().run(imp, seg_chnl, seg_chnl, 1, 1, 1, 1)

            imp_segment.setTitle("Backsubtract")
            IJ.run(
                imp_segment, "Subtract Background...", "rolling=" + str(back_subtract)
            )

            # imp_laplace = ImageScience.computeLaplacianImage(laplace_radius, imp_segment)
            imp_segment.show()
            IJ.selectWindow(imp_segment.getTitle())
            IJ.run(
                "FeatureJ Laplacian", "compute smoothing=" + str(Double(laplace_radius))
            )
            imp_laplace = IJ.getImage()

            # sys.exit()
            imp_segment.hide()
            imp_laplace.hide()

            if thresh_method == "Fully automatic":
                IJ.setAutoThreshold(imp_laplace, "Moments")
                IJ.run(
                    imp_laplace,
                    "Convert to Mask",
                    "method=" + "Moments  background=Dark black",
                )
            elif thresh_value == 0:
                imp_laplace.show()
                IJ.run("Threshold...")
                WaitForUserDialog("Set manual threshold, then click OK").show()
                thresh_value = imp_laplace.getProcessor().getMaxThreshold()
                min_thresh_value = imp_laplace.getProcessor().getMinThreshold()

                imp_laplace.hide()

            IJ.setThreshold(imp_laplace, min_thresh_value, thresh_value)
            Prefs.blackBackground = False
            IJ.run(imp_laplace, "Convert to Mask", "")

            if thresh_method == "Fully manual":
                thresh_value = 0

            if imp_laplace.isInvertedLut():
                IJ.run(imp_laplace, "Invert LUT", "")

            IJ.run(imp_laplace, "32-bit", "")
            IJ.setAutoThreshold(imp_laplace, "Default dark")

            # sys.exit()
            IJ.run(imp_laplace, "NaN Background", "")
            IJ.run(imp_laplace, "Divide...", "value=255")

            imp_result = ImageCalculator().run("Divide create 32-bit", imp_c1, imp_c2)
            imp_result = ImageCalculator().run(
                "Multiply create 32-bit", imp_result, imp_laplace
            )

            # IJ.run(imp_result, "Green Fire Blue", "")
            IJ.run(imp_result, "Green Fire Blue", "")
            IJ.run(imp_result, "Select None", "")
            imp_result.setDisplayRange(min_display, max_display)
            IJ.run(
                imp_result,
                "Calibration Bar...",
                "location=[Upper Right] fill=White label=Black number=5 decimal=3 font=12 zoom=1 overlay",
            )
            IJ.saveAs(imp_result, "Tiff", out_ratio)
            # imp_result = imp_result.flatten()
            # IJ.saveAs(imp_result, "Tiff", out_calibration)

            imp.close()
            imp_result.close()
            imp_c1.close()
            imp_c2.close()
            imp_laplace.close()
            imp_segment.close()

timed_log("Script finished !")
