#! /usr/bin/env python
# coding=utf-8

## KnatanK (c) gatopeich 2011
## All rights reserved until I find an adequate license ###

## TODO:
# Assure bullet does not hit own tank while shooting.
# Extra collision detection for bullets or improve it somehow.
# Remote-observed game: client+server.
# Remote-controlled tanks.
# Collisionable subclass of Sprite.
# Round, square and 'line' collision patterns.
# Explosions can collide too.
# Better looks for walls.
# AI tanks. Like in Wii: static, moving, aggressive, miner...
# Maps.
# Bouncing bullets.
# Mines.

## DONE:
# Color transformation by extracting a set then transforming it then applying.
# Visual height of explosions.
# FIX Multiple collision -> ValueError: All.remove(x): x not in All.

import pygame, time, math, bisect
from pygame import draw
from utility import *

### INITIALIZATION AND GLOBALS

pygame.init()
screen = pygame.display.set_mode((640, 480))
pygame.display.set_caption("KnatanK")
screen_width, screen_height = screen.get_size()
field_width, field_height = screen_width, screen_height*2

# Dimensions
BULLET_HEIGHT = 10
TANK_HEIGHT = 10

# Colors:
black = pygame.Color('black')
red = pygame.Color('red')
green = pygame.Color('green')
blue = pygame.Color('blue')
pink = pygame.Color('pink')
white = pygame.Color('white')
grey = pygame.Color('light grey')

# Mute all:
pygame.mixer = False

# Sounds:
sound_walk = load_sound('WalkingToyLoop.wav')
sound_walk.set_volume(.2)
sound_turn = load_sound('WalkingToyLoop-slow.wav')
sound_turn.set_volume(.2)
sound_shot = load_sound('shot.wav')
sound_shot.set_volume(.2)
sound_explosion = load_sound('explosion.wav')
sound_explosion.set_volume(.2)

# Eight directions: N, NE, E, SE, S, SW, W, NW
directions = ((0.0, -2.8), (2.0, -2.0), (2.8, 0.0), (2.0, 2.0), (0.0, 2.8), (-2.0, 2.0), (-2.8, 0.0), (-2.0, -2.0))

def facing8(dx, dy):
    if dx >= 0:
        if dy >= 0:
            return 2 if dx>2*dy else 4 if dy>2*dx else 3
        return 2 if dx>-2*dy else 0 if -dy>2*dx else 1
    if dy >= 0:
        return 6 if -dx>2*dy else 4 if dy>-2*dx else 5
    return 6 if -dx>-2*dy else 0 if -dy>-2*dx else 7

# Base class for all that we draw in the screen that cares about Y-order
class Sprite:
    All = []
    
    def __init__(self):
        self.y = self.y
        bisect.insort(Sprite.All, self)
    def __lt__(self, other):
        return self.y < other.y
    def dissapear(self):
        try: Sprite.All.remove(self)
        except ValueError: pass # Already removed

    def update(self): pass
    def draw(self): pass
    def __str__(self):
        return self.__class__.__name__

    @staticmethod
    def updateall():
        for sprite in Sprite.All:
            sprite.update()

    @staticmethod
    def drawall():
        Sprite.All.sort()
        for sprite in Sprite.All:
            sprite.draw()

class Physical(Sprite):
    All = []   
    def __init__(self, bounds):
        self.bounds = bounds
        bisect.insort(Physical.All, self)
        Sprite.__init__(self)
    def dissapear(self):
        try: Physical.All.remove(self)            
        except ValueError: pass # Already removed
        Sprite.dissapear(self)

    def collision(self, other): pass

    @staticmethod
    def collideall():
        objects = (o for o in Physical.All)
        for o1 in objects:
            for o2 in objects:
                if o1 != o2 and o1.bounds.colliderect(o2.bounds):
                    #~ print o1, "hit", o2
                    o1.collision(o2)
    def __str__(self):
        return self.__class__.__name__+' at '+str(self.bounds.center)

class Wall(Physical):
    def __init__(self, left, top, width, height):
        self.y = top+height
        self.screenrect = pygame.Rect(left, top/2, width, height/2)
        Physical.__init__(self, pygame.Rect(left, top, width, height))
    def draw(self):
        draw.rect(screen, black, self.screenrect, 1)

class Tank(Physical):
    def __init__(self, color=blue, x=field_width/2, y=field_height/2):
        self.x, self.y = x, y
        self.bodies = load_multiimage('tank_body.png', 8, color)
        self.turrets = load_multiimage('tank_turret.png', 8, color)
        self.sx, self.sy = self.bodies[0].get_size()
        self.color = color
        self.heading = 0
        self.targetx, self.targety = None, None
        self.sound = None
        self.trail = tuple(Trail(self.color, x, y) for i in xrange(7))
        self.readyamo = 5
        self.reloading = 0
        self.controlkeys = pygame.K_UP, pygame.K_RIGHT, pygame.K_DOWN, pygame.K_LEFT
        self.facing = None
        self.bullet = None
        w = self.sx
        Physical.__init__(self, pygame.Rect(x-w/2, y-w/2, w, w))

    def noise(self, sound):
        if self.sound != sound:
            if self.sound:
                self.sound.stop()
            self.sound = sound
            if self.sound:
                self.sound.play(-1)

    def update(self):
        """ Must be called every tick."""
        pressed = pygame.key.get_pressed()
        #uprightdownleft = map(pressed.__getitem__, self.controlkeys)
        uprightdownleft = tuple(pressed[key] for key in self.controlkeys)
        if sum(uprightdownleft):
            up, right, down, left = uprightdownleft
            headto = facing8(right-left, down-up)
        else:
            headto = None

        if headto == self.heading:
            self.noise(sound_walk)
            self.x += directions[headto][0]
            self.y += directions[headto][1]
            self.bounds.center = self.x, self.y
        elif headto != None:
            self.noise(sound_turn)
            if (headto+8-self.heading)&7 <= 4:
                self.heading += 1
            else:
                self.heading -= 1
            self.heading &= 7
        else:
            self.noise(None)

        self.targetx, self.targety = pygame.mouse.get_pos()
        self.targety += BULLET_HEIGHT
        self.targety *= 2 # Perspective
        dx = self.targetx - self.x
        dy = self.targety - self.y
        self.facing = facing8(dx, dy)
        for i in xrange(1, 8):
            self.trail[i-1].x = (i*self.targetx+(8-i)*self.x)/8
            self.trail[i-1].y = (i*self.targety+(8-i)*self.y)/8

        if self.reloading:
            self.reloading -= 1
            if not self.reloading:
                self.readyamo += 1
                self.reloading = 10
                
        if self.readyamo and pygame.mouse.get_pressed()[0]:
            self.readyamo -= 1
            self.reloading = 10
            distance = math.hypot(dx, dy)
            vx, vy = 10.0*dx/distance, 10.0*dy/distance
            self.bullet = Bullet(self.x+4*vx, self.y+4*vy, vx, vy)

    def draw(self):
        xy = self.x-self.sx/2, (self.y-self.sy-TANK_HEIGHT)/2
        draw.line(screen, black, (self.x-30, self.y/2), (self.x+30, self.y/2))
        draw.line(screen, black, (self.x, self.y/2-20), (self.x, self.y/2+20))
        screen.blit(self.bodies[self.heading], xy)
        screen.blit(self.turrets[self.facing], xy)

class Trail(Sprite):
    def __init__(self, color, x, y):
        self.color = color
        self.x, self.y = x, y
        Sprite.__init__(self)
    def draw(self):
        draw.circle(screen, self.color, int2(self.x, self.y/2-BULLET_HEIGHT) , 3, 1)
        draw.line(screen, black, (self.x-1, self.y/2), (self.x+1, self.y/2))

class Explosion(Sprite):
    def __init__(self, size, center):
        sound_explosion.play()
        self.size = size
        self.x, self.y = center
        Sprite.__init__(self)
    def draw(self):
        draw.circle(screen, red, int2(self.x, self.y/2-BULLET_HEIGHT), self.size)
        self.size -= 5
        if 2 > self.size:
            self.dissapear()

class Bullet(Sprite):
    def __init__(self, x, y, vx, vy):
        sound_shot.play()
        # Some fixed point magic:
        self.fx, self.fy = int(256*x), int(256*y)
        self.y = int(self.fy>>8)
        self.vx, self.vy = int(256*vx), int(256*vy)
        self.bounces = 1
        self.bounds = pygame.Rect(x-1, y-1, 3, 3)
        Sprite.__init__(self)
    def update(self):
        self.fx += self.vx
        self.fy += self.vy
        self.y = int(self.fy>>8)
        self.bounds.center = int(self.fx>>8), self.y
    def collision(self, other):
        Explosion(10, self.bounds.center)
        self.dissapear()
    def draw(self):
        draw.circle(screen, white, ((self.fx-self.vx/3)>>8, ((self.fy-self.vy/3)>>9)-10), 2)
        draw.circle(screen, white, (self.fx>>8, (self.fy>>9)-BULLET_HEIGHT), 2)
        draw.line(screen, black, ((self.fx>>8)-1, self.fy>>9), ((self.fx>>8)+1, self.fy>>9))

def game():
    tanks = ( Tank(blue, field_width/3, field_height/3), 
              Tank(pink, field_width*2/3, field_height/3), 
              Tank(red, field_width/3, field_height*2/3), 
              Tank(green, field_width*2/3, field_height*2/3) )
    WallN = Wall(-100, -100, field_width+200, 110)
    WallE = Wall(field_width-10, 11, 110, field_height-22)
    WallS = Wall(-100, field_height-10, field_width+200, 110)
    WallW = Wall(-100, 11, 110, field_height-22)

    #~ background = screen.copy()
    tile = load_image('ground.png')
    tile_width, tile_height = tile.get_size()

    font = pygame.font.Font(None, 24)

    background = screen.copy()
    for x in xrange(1+screen_width/tile_width):
        for y in xrange(1+screen_height/tile_height):
            background.blit(tile, (x*tile_width, y*tile_height))

    clock = pygame.time.Clock()
    infoline = ''
    while True:
        clock.tick(10) # Ticks per second
        cycletimer = time.time() # pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

        Sprite.updateall()
        Physical.collideall()

        screen.blit(background, (0, 0))
        Sprite.drawall()

        screen.blit(font.render(infoline, True, white), (7, 7))
        pygame.display.flip()

        infoline = 'FPS: %0.1f' % (clock.get_fps())
        infoline += ', cycle takes: %.1f ms.' %((time.time()-cycletimer)*1000)
        dx, dy = tanks[0].targetx - tanks[0].x, tanks[0].targety - tanks[0].y
        infoline += ', dx=%d, dy=%d' %(dx, dy)

game()
