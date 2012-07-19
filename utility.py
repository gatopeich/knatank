#! /usr/bin/env python
# coding=utf-8 *** KatanK by gatopeich 2010

import pygame
from pygame import Rect

def clip255(x): return (x if x >=0 else 0) if x < 256 else 255

### Utility functions ###
def load_image(filename, tint = False):
    try:
        image = pygame.image.load(filename)
    except pygame.error, message:
        print 'Cannot load image:', filename
        raise SystemExit, message
    if tint:
        """ Use 'tint' color as blue in the origin """
        global screen
        tr, tg, tb = tint.r, tint.g, tint.b
        t0 = pygame.time.get_ticks()
        pa = pygame.PixelArray(image)
        for color in set.union(*map(set,pa)):
            r,g,b,a = image.unmap_rgb(color)
            if b > r and b > g:
                pa.replace(color, (clip255(r+tr*b/255), clip255(g+tg*b/255), clip255((r+g)/2+tb*b/255), a))
        print "Took",pygame.time.get_ticks()-t0,"ms to apply tint",tint
    return image.convert_alpha()

def load_multiimage(filename, multi=1, tint=False):
    image = load_image(filename, tint)
    h = image.get_height() / multi
    w = image.get_width()
    return [image.subsurface(Rect(0,h*i,w,h)) for i in xrange(multi)]

def load_sound(filename):
    class Silence:
        def play(self,loops=None): pass
        def set_volume(self,volume=None): pass
        def stop(self): pass
    if not pygame.mixer:
        return Silence()
    try:
        sound = pygame.mixer.Sound(filename)
    except pygame.error, message:
        print 'Cannot load sound:', wav
        raise SystemExit, message
    return sound

# XY-vector class:
class XY(tuple):
    def __add__(self, other): return XY(self[0]+other[0], self[1]+other[1])
    def __sub__(self, other): return XY(self[0]-other[0], self[1]-other[1])
    def __mul__(self, scalar): return XY(xy[0]*scalar, xy[1]*scalar)
    def __div__(self, other): return XY(xy[0]*scalar, xy[1]/scalar)

def int2(a,b): return (int(a),int(b))
