"""Loads OSM tiles from the Web"""

import os
import asyncore
import threading

import asynchttp

import pyglet.image as pygletimage

__author__ = "P. Tute"
__maintainer__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


PORT = 80
METHOD = 'GET'

LAYERS = {"tah": ["cassini.toolserver.org:8080", "/http://a.tile.openstreetmap.org/+http://toolserver.org/~cmarqu/hill/"],
          "oam": ["oam1.hypercube.telascience.org", "/tiles/1.0.0/openaerialmap-900913/"],
          "mapnik": ["a.tile.openstreetmap.org", "/"]
}

class TileLoader(asynchttp.AsyncHTTPConnection):
    """This class uses asynchttp to download OSM-tiles in an asynchronous manner.
    @author: P. Tute"""
    def __init__(self, player, x, y, z, layer='mapnik'):
        """player is an instance of the player that uses the tiles.
        layer is one of 'tah', 'oam', and 'mapnik' (default)."""
        host = LAYERS[layer][0]
        self.layer = layer
        asynchttp.AsyncHTTPConnection.__init__(self, host, PORT)

        self.base_url_extension = LAYERS[layer][1]
        #self.file_extension = '.' + self.tileLayerExt(layer)
        self.file_extension = '.jpg' if layer == 'oam' else '.png'

        self.player = player
        self.x, self.y, self.z = x, y, z
        self.loading_image = pygletimage.load(os.path.join(self.player.data_dir, 'loading.png'))
        self.player.tiles[(self.x, self.y, self.z)] = self.loading_image
        
        self.connect()

    def get_tile(self):
        """Builds a response and tries to download the right tile from x, y, andd zoom-values."""
        url = self.base_url_extension + str(self.z) + '/' + str(self.x) + '/' + str(self.y) + self.file_extension
        self.putrequest('GET', url)
        self.endheaders()
        self.getresponse()

    def handle_connect(self):
        asynchttp.AsyncHTTPConnection.handle_connect(self)
        self.get_tile()

    def handle_response(self):
        if '<html>' in self.response.body:
            # something went wrong...mostlikely a 404 error
            return
        elements = [self.player.cache_dir, self.layer, str(self.z), str(self.x)]
        path = ''
        for element in elements:
            path = os.path.join(path, element)
            try:
                os.mkdir(path)
            except OSError:
                #folder exists, no need to create
                pass
        path = os.path.join(path, str(self.y) + self.file_extension)
        image_file = open(path, 'wb')
        image_file.write(self.response.body)
        image_file.flush()
        image_file.close()
        image = pygletimage.load(path)
        image.anchor_x = image.width / 2
        image.anchor_y = image.height / 2
        self.player.tiles[(self.x, self.y, self.z)] = image


if __name__ == '__main__':
    player = Player(52.382463, 9.717836, width=800, height=600, resizable=True)
    tl = TileLoader(player, 34, 43, 16)
    tl.start()
