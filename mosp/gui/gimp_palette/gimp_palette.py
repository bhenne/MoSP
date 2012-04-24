"""Access to GIMP color palettes to be used within simulation/player"""

import os
from re import sub as regexp_replace

__author__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class GimpPalette:
    """Represents a GIMP color palette read from file.
    
    Colors can be accessed via their names."""
    
    def __init__(self, filename='Default.gpl'):
        """Loads a GIMP palette from a palette file."""
        f = open(os.path.abspath(filename), 'rt')
        self.name = 'unnamed'
        self.color = {}
        counter = 2
        for row in f:
            if row.startswith('GIMP'):
                continue
            if row.startswith('Name: '):
                self.name = regexp_replace(r'Name:\s+', '', row)
                continue
            if row.startswith('#'):
                continue
            splitted = regexp_replace(r'\s+', ' ', row).strip().split(' ', 3)
            if 3 <= len(splitted) <= 4:
                if len(splitted) == 3:
                    splitted.append('unnamed')
                c = (int(splitted[0])/255.0, int(splitted[1])/255.0, int(splitted[2])/255.0)
                name = splitted[3].lower()
                if name in self.color:
                    if self.color[name] == c:
                        continue
                    else:
                        self.color['color%s' % counter] = c
                        counter += 1
                else:
                    self.color[name] = c
    
    def __str__(self):
        """Returns full palette of colors as <r g b name> seperated by newlines."""
        s = ''
        for name in self.color.keys():
            r, g, b = self.color[name]
            s += '%.2f %.2f %.2f %s\n' % (r,g,b,name)
        return s
    
    def rgb(self, colorname):
        """Returns rgb triple of color from palette specified by its name.
        
        First looks for exact match, then for first startswith match, 
        then for first substring match, finally raises KeyError."""
        if colorname in self.color:
            return self.color[colorname]
        else:
            for k in self.color.keys():
                if k.startswith(colorname):
                    self.color[colorname] = self.color[k]
                    return self.color[colorname]
            for k in self.color.keys():
                if k.count(colorname) > 0:
                    self.color[colorname] = self.color[k]
                    return self.color[colorname]
        raise KeyError(colorname)

    def rgba(self, colorname, alpha=1.0):
        """Returns rgba quadruple of color from rgb palette specified by its name.
        
        First looks for exact match, then for first startswith match, 
        then for first substring match, finally raises KeyError.
        Alpha defaults to 1.0, if not set by user."""
        return self.rgb(colorname) + (alpha,)


if __name__ == '__main__':
    demopalette = 'Visibone.gpl'
    democolor = 'medium faded blue'
    demo = GimpPalette(demopalette)
    print demo
    print '%s (RGB) = %s' % (democolor, demo.rgb(democolor))
    print '%s (RGBA) = %s' % (democolor, demo.rgba(democolor))
    print '%s (RGBA), alpha:50%% = %s' % (democolor, demo.rgba(democolor, 0.5))
