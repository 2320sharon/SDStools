
## Downloads topobathy data using https://github.com/NeptuneProjects/BathyReq
## and makes a pretty plot
## written by Dr Daniel Buscombe, April 26-30, 2024

## Example usage, from cmd:
## python download_topobathymap.py -f "ak_example.geojson" -s "AK"
## python download_topobathymap.py -f "longisland_example.geojson" -s "longisland"

import bathyreq
import argparse
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.colors
import rasterio
from rasterio.transform import from_origin
from rasterio.transform import Affine
import geopandas as gpd

class FixPointNormalize(matplotlib.colors.Normalize):
    """ 
    Inspired by https://stackoverflow.com/questions/20144529/shifted-colorbar-matplotlib
    Subclassing Normalize to obtain a colormap with a fixpoint 
    somewhere in the middle of the colormap.

    This may be useful for a `terrain` map, to set the "sea level" 
    to a color in the blue/turquise range. 
    """
    def __init__(self, vmin=None, vmax=None, sealevel=0, col_val = 0.21875, clip=False):
        # sealevel is the fix point of the colormap (in data units)
        self.sealevel = sealevel
        # col_val is the color value in the range [0,1] that should represent the sealevel.
        self.col_val = col_val
        matplotlib.colors.Normalize.__init__(self, vmin, vmax, clip)

    def __call__(self, value, clip=None):
        x, y = [self.vmin, self.sealevel, self.vmax], [0, self.col_val, 1]
        return np.ma.masked_array(np.interp(value, x, y))


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments for the topobathy data download script.
    Arguments and their defaults are defined within the function.
    Returns:
    - argparse.Namespace: A namespace containing the script's command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Script to download topobathy data in any ROI")

    parser.add_argument(
        "-f",
        "-F",
        dest="geofile",
        type=str,
        required=True,
        help="Set the name of the geoJSON file.",
    )

    parser.add_argument(
        "-S",
        "-s",
        dest="site",
        type=str,
        required=True,
        help="Set the name of the site.",
    )
    return parser.parse_args()


##==========================================
def main():
    args = parse_arguments()
    site = args.site
    geofile = args.geofile

    # load a region grid
    grid = gpd.read_file(geofile)
    minlon, minlat, maxlon, maxlat = grid.geometry.values.bounds[0]

    req = bathyreq.BathyRequest()
    data, lonvec, latvec = req.get_area(
        longitude=[minlon, maxlon], latitude=[minlat, maxlat] )

    # Combine the lower and upper range of the terrain colormap with a gap in the middle
    # to let the coastline appear more prominently.
    # inspired by https://stackoverflow.com/questions/31051488/combining-two-matplotlib-colormaps
    colors_undersea = plt.cm.terrain(np.linspace(0, 0.17, 56))
    colors_land = plt.cm.terrain(np.linspace(0.25, 1, 200))
    # combine them and build a new colormap
    colors = np.vstack((colors_undersea, colors_land))
    cut_terrain_map = matplotlib.colors.LinearSegmentedColormap.from_list('cut_terrain', colors)
    norm = FixPointNormalize(sealevel=0, vmax=100)

    plt.pcolormesh(lonvec,latvec,data,cmap=cut_terrain_map, norm=norm) 
    plt.colorbar(extend='both')
    # plt.show()
    plt.savefig(f'{site}_topobathy_{minlon}_{maxlon}_{minlat}_{maxlat}.png', dpi=300, bbox_inches='tight')
    plt.close()

    xres = (maxlon - minlon) / data.shape[0]
    yres = (maxlat - minlat) / data.shape[1]

    transform = Affine.translation(minlon - xres / 2, minlat - yres / 2) * Affine.scale(xres, yres)
    # transform = Affine.translation(minlat - yres / 2, minlon - xres / 2) * Affine.scale(yres, xres)

    # data = np.rot90(data.T)
    # data = np.flipud(data)
    # data = np.fliplr(data)

    with rasterio.open(
            f"{site}_method1.tif",
            mode="w",
            driver="GTiff",
            height=data.shape[0],
            width=data.shape[1],
            count=1,
            dtype=data.dtype,
            crs="+proj=latlong  +ellps=WGS84 +datum=WGS84 +no_defs",
            transform=transform,
    ) as new_dataset:
            new_dataset.write(data, 1)

    # transform = from_origin(minlon, minlat, data.shape[0]/(maxlon-minlon), data.shape[1]/(maxlat-minlat))

    # data = np.flipud(data)
    # new_dataset = rasterio.open(f'{site}_method2.tif', 'w', driver='GTiff',
    #                             height = data.shape[0], width = data.shape[1],
    #                             count=1, dtype=str(data.dtype), 
    #                             crs='+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs',
    #                             transform=transform)

    # new_dataset.write(data, indexes=1)
    # new_dataset.close()


if __name__ == "__main__":
    main()
