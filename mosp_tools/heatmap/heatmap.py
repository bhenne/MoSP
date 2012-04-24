"""Heatmap generation based in simulation logs and a background map

inspired by http://www.jjguy.com/heatmap/ which based on http://code.google.com/p/gheat/

"""

import sys
sys.path.append("../..")
from mosp.geo.utm import long_to_zone, latlong_to_utm

from math import sqrt
from os import spawnvp, P_WAIT
from PIL import Image, ImageChops, ImageEnhance, ImageDraw, ImageFont, ImageColor

from logfilereader import accumulated_read
import colorschemes

__author__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "MIT license"


class Heatmap(object):
    """A generator for heatmap images based on simulation log data.
    @author: B. Henne
    """

    def __init__(self, mapfilename, minlon, maxlon, minlat, maxlat, dotsize=30):
        """Initialize the heatmap generation object."""
        # map(ping) configuration
        self.mapfile = mapfilename     #: filename of underlay map from osm export
        self.minlon = minlon           #: min longitude from osm png export
        self.maxlon = maxlon           #: max longitude from osm png export
        self.minlat = minlat           #: min latitude from osm png export
        self.maxlat = maxlat           #: max latitude from osm png export
        # calculate values
        self.x_min, self.y_min = latlong_to_utm(self.minlon, self.minlat)
        self.x_max, self.y_max = latlong_to_utm(self.maxlon, self.maxlat)
        self.width = abs(self.x_max - self.x_min)
        self.height = abs(self.y_max - self.y_min)
        # setup fonts
        font_path = "/usr/share/fonts/"
        self.sans18 = ImageFont.truetype (font_path+'dejavu/DejaVuSansMono-Bold.ttf', 18)
        self.sans12 = ImageFont.truetype (font_path+'dejavu/DejaVuSansMono-Bold.ttf', 12)
        # setup images: dot
        self.dotsize = dotsize
        self.dot = self.__dotImage(self.dotsize)
        # setup images: backgroud map
        self.map = Image.open(self.mapfile)
        self.mapsize = self.map.size
        if self.map.mode != 'RGBA':
            self.map = self.map.convert('RGBA')
        draw = ImageDraw.Draw(self.map)
        draw.text((self.mapsize[0]-300, self.mapsize[1]-30), 
                  '(c) OpenStreetMap contributors, CC-BY-SA', 
                  font=self.sans12, fill=ImageColor.colormap['darkgrey'])
        draw.rectangle([(16,10),(80,30)], fill=ImageColor.colormap['lightgray'])
        del draw
        
    def _colorize(self, img, colors, opacity):
        """Use the colorscheme selected to color the image densities.
        
        heatmap.py v1.0 20091004. from http://www.jjguy.com/heatmap/"""
        finalVals = {}
        w,h = img.size
        for x in range(w):
            for y in range(h):
                pix = img.getpixel((x,y))
                rgba = list(colors[pix[0]][:3])  #trim off alpha, if it's there.
                if pix[0] <= 254: 
                    alpha = opacity
                else:
                    alpha = 0 
                rgba.append(alpha) 
                img.putpixel((x,y), tuple(rgba))

    def __dotImage(self, size):
        """Returns a image of the dot that is used for drawing heatmap."""
        dotimg = Image.new("RGB", (size,size), 'white')
        md = 0.5*sqrt( (size/2.0)**2 + (size/2.0)**2 )
        for x in range(size):
            for y in range(size):
                d = sqrt( (x - size/2.0)**2 + (y - size/2.0)**2 )
                rgbVal = int(200*d/md + 50)
                rgb = (rgbVal, rgbVal, rgbVal)
                dotimg.putpixel((x,y), rgb)
        return dotimg

    def __translate(self, xy):
        """Translates x,y coordinates into pixel offsets of a map."""
        # translation
        _x = float(xy[0]) - self.x_min
        _y = float(xy[1]) - self.y_min
        # scaling
        _x = int(_x / self.width * self.mapsize[0])
        _y = self.mapsize[1] - int(_y / self.height * self.mapsize[1])
        # translation for dot size
        _x = _x - self.dotsize / 2
        _y = _y - self.dotsize / 2
        return (_x,_y)

    def generate(self, logfilename, delimiter, t, x, y, t_start, t_end, step, reset_dotlayer_every_step=False):
        """Generates the heapmap PNG image files.
        
        @param logfilename: name of csv-formated log file
        @param delimiter: delimiter between columns in csv log file
        @param t: number of log file's column containing time
        @param x: number of log file's column containing x-value
        @param y: number of log file's column containing y-value
        @param t_start: start of output time interval
        @param t_end: end of output time interval
        @param step: size/length of a log accumulation step
        @param reset_dotlayer_every_step: draw second heatmap over first one etc. or clear for each image
        """
        dotlayer = Image.new('RGBA', self.mapsize, 'white')
        for timestep, timestepdata in accumulated_read(logfilename, delimiter, t, x, y, t_start, t_end, step=step):
            for xy in timestepdata:
                dot = Image.new('RGBA', self.mapsize, 'white')
                dot.paste(self.dot, self.__translate(xy))
                dotlayer = ImageChops.multiply(dotlayer, dot)
                
            heatmask_color = dotlayer.copy()
            self._colorize(heatmask_color, colorschemes.schemes['fire'], 200)
            draw = ImageDraw.Draw(heatmask_color)
            draw.text((10,10), str('% 4d' % timestep), font=self.sans18, fill=ImageColor.colormap['black'])
            del draw
            #img.save('/tmp/heatmap-overlay-%4s' % timestep)
            Image.composite(heatmask_color, self.map, heatmask_color).save('/tmp/demo-heatmap1-%05d.png' % timestep)
            if reset_dotlayer_every_step == True:
                dotlayer = Image.new('RGBA', self.mapsize, 'white')
            
    def mencode_video(self, location, files, filetype, videofile):
        """[Bad Video Quality] Encodes a set of image files to a video file using mencoder.
        
        Better use:
            1. mencoder mf://PNG/heatmap1*.png -mf type=png:w=780:h=600:fps=30 -o /dev/null -ovc x264 -x264encopts pass=1:bitrate=1200:bframes=1:me=umh:partitions=all:trellis=1:qp_step=4:qcomp=0.7:direct_pred=auto:keyint=300 -vf crop=768:576:0:0
            2. mencoder mf://PNG/heatmap1*.png -mf type=png:w=780:h=600:fps=30 -o heatmap1.avi -ovc x264 -x264encopts pass=2:bitrate=1200:bframes=1:me=umh:partitions=all:trellis=1:qp_step=4:qcomp=0.7:direct_pred=auto:keyint=300 -vf crop=768:576:0:0"""
        command = ('mencoder',
           'mf://%s%s' % (location, files),
           '-mf',
           'type=%s:w=%s:h=%s:fps=30' % (filetype, self.mapsize[0], self.mapsize[1]),
           '-ovc',
           'lavc',
           '-lavcopts',
           'vcodec=mpeg4',
           '-oac',
           'copy',
           '-o',
           '%s%s' % (location, videofile))
        spawnvp(P_WAIT, 'mencoder', command)
    

if __name__ == '__main__':
    print 'Initializing heatmap.'
    h = Heatmap('data/demo-heatmap_map.png', -87.6405, -87.60125, 41.866258, 41.88875, dotsize=10)
    print 'Generating image files.'
    h.generate('data/demo-heatmap.log', ' ', 1, 3, 4, 42000, 42048, step=12, reset_dotlayer_every_step=True)
    # print 'Generating video.'
    # h.mencode_video('/tmp/', 'demo-heatmap1*.png', 'png', 'demo-heatmap1.avi')

