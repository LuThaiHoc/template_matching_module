import rasterio
from rasterio.transform import from_origin
from pyproj import Transformer
from rasterio.errors import RasterioError
import os

def pixel_to_latlon(tiff_path, x, y):
    """
    Convert pixel coordinates to geographic coordinates (latitude, longitude) using a TIFF file.

    Parameters:
    - tiff_path (str): Path to the TIFF file.
    - x (int): Pixel x-coordinate.
    - y (int): Pixel y-coordinate.

    Returns:
    - tuple: (latitude, longitude) coordinates, or (None, None) if there is an error.
    """
    if not os.path.exists(tiff_path):
        return None, None
    
    try:
        with rasterio.open(tiff_path) as dataset:
            # Read the affine transform and CRS
            transform = dataset.transform
            crs = dataset.crs
            
            # Ensure CRS is defined
            if crs is None:
                print("Pixel to latlon: Not crs data")
                return None, None
            
            # Convert pixel coordinates to geographic coordinates
            lon, lat = rasterio.transform.xy(transform, y, x)
            
            # Create a transformer to convert from the dataset's CRS to WGS84 (lat/lon)
            transformer = Transformer.from_crs(crs, 'EPSG:4326', always_xy=True)
            
            # Transform the coordinates
            lon, lat = transformer.transform(lon, lat)
            
            return lat, lon

    except (RasterioError, ValueError) as e:
        print(f"Pixel to latlon: Error reading TIFF file or processing coordinates: {e}")
        return None, None
    except Exception as e:
        print(f"Pixel to latlon: An unexpected error occurred: {e}")
        return None, None
    
def polygon_to_latlon(tiff_path, polygon):
    latlon_polygon = []
    if polygon is None:
        return latlon_polygon
    for point in polygon:
        x, y = point[0]
        lat, lon = pixel_to_latlon(tiff_path, x, y)
        if lat is None:
            continue
        latlon_polygon.append([lat, lon])
    return latlon_polygon

import logging

# Basic configuration without StreamHandler
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log')  # Only log to file
    ]
)

# Create a logger
logger = logging.getLogger('OBJECT-FINDER-MODULE')

# Set the logging level for the logger
logger.setLevel(logging.DEBUG)

# Create a handler (console in this case)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG) 

# Create a formatter and set it for the handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(console_handler)