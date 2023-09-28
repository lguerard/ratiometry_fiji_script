[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.8387238.svg)](https://doi.org/10.5281/zenodo.8387238)

# ratiometry_fiji_script

Improved version of the ratiometry script used in [this
paper|https://doi.org/10.1073/pnas.1613499114]

The script has now been rewritten in Python for Fiji (Jython) allowing for more
up-to-date scripting and call of the different commands.

Simply drag and drop the .py file in Fiji and click on the **RUN** button at the
bottom to start the script. Multiple inputs will then be asked:
* Folder with your images: this is where the images you want to analyze are
* Folder to save results: folder where the result images will be saved
* Extension of the input images: Only files with this extension will be processed
* Channel for segmentation
* Channel alignment: in case your channels aren't aligned, this will use
  [StackReg|http://bigwww.epfl.ch/thevenaz/stackreg/] with the *Affine*
  algorithm
* Dealing with thresholding:
  * Fully automatic: Script will try to find the best threshold using the
    *Moments* algorithm
  * Manual once: User input will be required for the 1st image and be then used
    for the other images
  * Fully manual: User input will be required for each images

