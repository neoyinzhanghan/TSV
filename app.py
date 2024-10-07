from flask import Flask, send_file, jsonify, request
import io
import numpy as np
from PIL import Image
import h5py
import base64

# Helper functions
def jpeg_string_to_image(jpeg_string):
    buffer = io.BytesIO(jpeg_string)
    image = Image.open(buffer)
    image.load()
    return image

def decode_image_from_base64(encoded_string):
    return base64.b64decode(encoded_string)

# H5TileReader class to manage the HDF5 file
class H5TileReader:
    """A reader for the dzsave_h5 output to keep the file open and retrieve tiles efficiently."""

    def __init__(self, h5_path: str):
        self.h5_path = h5_path
        self.f = None
        self.open()

    def open(self):
        """Open the HDF5 file if it is not already open."""
        if self.f is None:
            self.f = h5py.File(self.h5_path, "r")
        else:
            print("File is already open")

    def close(self):
        """Close the HDF5 file if it is currently open."""
        if self.f is not None:
            self.f.close()
            self.f = None
        else:
            print("File is already closed")

    def __del__(self):
        """Ensure the HDF5 file is closed upon deletion of the object."""
        self.close()

    def retrieve_tile_h5(self, level, row, col):
        """Retrieve a tile from the HDF5 file at a specified level, row, and column."""
        if self.f is None:
            raise ValueError("File is not open. Call open() method first")
        else:
            try:
                jpeg_string = self.f[str(level)][row, col]
                jpeg_string = decode_image_from_base64(jpeg_string)
                image = jpeg_string_to_image(jpeg_string)
                return image
            except Exception as e:
                print(
                    f"Error: {e} occurred while retrieving tile at level: {level}, row: {row}, col: {col} from {self.h5_path}"
                )
                raise e

    def get_slide_dimensions(self):
        """Return the width and height of the slide at level 0."""
        if self.f is None:
            raise ValueError("File is not open. Call open() method first")
        else:
            width = self.f["level_0_width"][0]
            height = self.f["level_0_height"][0]
            return width, height

    def get_patch_size(self):
        """Return the patch size of the slide."""
        if self.f is None:
            raise ValueError("File is not open. Call open() method first")
        else:
            return self.f["patch_size"][0]

    def get_num_levels(self):
        """Return the number of levels of the slide."""
        if self.f is None:
            raise ValueError("File is not open. Call open() method first")
        else:
            return self.f["num_levels"][0]

# Create the Flask app
app = Flask(__name__)

# Path to the HDF5 file
h5_path = "/dmpisilon_tools/HemeLabel/media/slides/6825083.h5"

# Create an instance of the H5TileReader
h5_reader = H5TileReader(h5_path)

@app.route('/')
def index():
    """Serve the OpenSeadragon viewer."""
    return send_file('index.html')

@app.route('/tile', methods=['GET'])
def get_tile():
    """Serve a tile based on level, row, and col parameters."""
    level = int(request.args.get('level'))
    row = int(request.args.get('x'))
    col = int(request.args.get('y'))

    try:
        tile = h5_reader.retrieve_tile_h5(level, row, col)
        img_io = io.BytesIO()
        tile.save(img_io, 'JPEG')
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/metadata', methods=['GET'])
def get_metadata():
    """Serve basic metadata needed for OpenSeadragon initialization."""
    try:
        width, height = h5_reader.get_slide_dimensions()
        num_levels = h5_reader.get_num_levels()
        tile_size = h5_reader.get_patch_size()
        
        return jsonify({
            'width': width,
            'height': height,
            'tile_size': tile_size,
            'num_levels': num_levels
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
