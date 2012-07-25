#! /usr/bin/env python
# coding=utf-8 *** KatanK by gatopeich 2010
"""
KnatanK (c) gatopeich 2011,2012
All rights reserved until I find an adequate license

Utility code
"""

import pygame
from pygame import Rect

def clip255(x): return (x if x >=0 else 0) if x < 256 else 255

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
        for color in set.union(*(set(row) for row in pa)):
            r,g,b,a = image.unmap_rgb(color)
            if b > r and b > g:
                pa.replace(color, (clip255(r+tr*b/255), clip255(g+tg*b/255), clip255((r+g)/2+tb*b/255), a))
        print "Took", pygame.time.get_ticks()-t0, "ms to apply tint", tint
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
        print 'Cannot load sound:', filename
        raise SystemExit, message
    return sound

# XY-vector class:
class XY(tuple):
    def __init__(self, x, y): pass
    def __new__(cls, x, y): return tuple.__new__(cls, (x, y))
    def __add__(self, rhs): return XY(self[0]+rhs[0], self[1]+rhs[1])
    def __sub__(self, rhs): return XY(self[0]-rhs[0], self[1]-rhs[1])
    def __mul__(self, rhs): return XY(rhs*self[0], rhs*self[1])
    def __div__(self, rhs): return XY(self[0]*rhs, self[1]/rhs)

def ints(*numbers): return tuple(int(n) for n in numbers)


if __name__ == '__main__':
    pygame.display.set_mode((640, 480))
    load_image('tank_body.png', pygame.Color('red'))
    pygame.display.quit()