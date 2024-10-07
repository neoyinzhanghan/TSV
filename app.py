from flask import Flask, send_file, jsonify, request
import io
import numpy as np
from PIL import Image
import h5py
import base64
import os

# Existing tile reading code with modifications to integrate with Flask
class H5TileReader:
    def __init__(self, h5_path: str):
        self.h5_path = h5_path
        self.f = h5py.File(h5_path, "r")

    def retrieve_tile_h5(self, level, row, col):
        if self.f is None:
            raise ValueError("File is not open. Call open() method first")
        else:
            try:
                jpeg_string = self.f[str(level)][row, col]
                jpeg_string = base64.b64decode(jpeg_string)
                image = Image.open(io.BytesIO(jpeg_string))
                return image
            except Exception as e:
                print(
                    f"Error: {e} occurred while retrieving tile at level: {level}, row: {row}, col: {col} from {self.h5_path}"
                )
                raise e

# Create the Flask app
app = Flask(__name__)

# Create an instance of the H5TileReader
h5_path = "/dmpisilon_tools/HemeLabel/media/slides/6825083.h5"
h5_reader = H5TileReader(h5_path)

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
    width, height = h5_reader.get_slide_dimensions()
    num_levels = h5_reader.get_num_levels()
    tile_size = h5_reader.get_patch_size()
    
    return jsonify({
        'width': width,
        'height': height,
        'tile_size': tile_size,
        'num_levels': num_levels
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
