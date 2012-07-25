# -*- coding: utf-8 -*-
"""
KnatanK (c) gatopeich 2011,2012
All rights reserved until I find an adequate license
"""

import pygame, time, math, bisect
from pygame import draw, event, Rect
from utility import load_image, load_multiimage, load_sound, ints

### GLOBALS

# Networking
import socket
SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
PORT = 55555
BROADCAST = '<broadcast>'
BROADCAST_ADDRESS = (BROADCAST, PORT)

# Dimensions
BULLET_HEIGHT = 10
TANK_HEIGHT = 10

# Colors:
BLACK = pygame.Color('black')
GREY = pygame.Color('light grey')
WHITE = pygame.Color('white')
RED = pygame.Color('red')
GREEN = pygame.Color('green')
BLUE = pygame.Color('blue')
YELLOW = pygame.Color('yellow')
PINK = pygame.Color('pink')
ORANGE = pygame.Color('orange')
BROWN = pygame.Color('brown')
COLORS = (BLUE, RED, GREEN, YELLOW, PINK, ORANGE, BROWN, GREY)

# Initialization:
pygame.init()
#pygame.mixer.init(frequency=11025, buffer=128) # TODO: fix sound delay
pygame.display.set_caption("KnatanK")
SCREEN = pygame.display.set_mode((640, 480))

BLIT = SCREEN.blit
FILL = SCREEN.fill

SCREEN_WIDTH, SCREEN_HEIGHT = SCREEN.get_size()
FIELD_WIDTH, FIELD_HEIGHT = SCREEN_WIDTH, SCREEN_HEIGHT*2

FONT_TITLE = pygame.font.Font(None, 100)
FONT_TITLE.set_bold(True)
FONT_TITLE.set_italic(True)
FONT_MENU = pygame.font.Font(None, 30)

# Sounds:
SOUND_WALK = load_sound('WalkingToyLoop.wav')
SOUND_WALK.set_volume(.2)
SOUND_TURN = load_sound('WalkingToyLoop-slow.wav')
SOUND_TURN.set_volume(.2)
SOUND_SHOT = load_sound('shot.wav')
SOUND_SHOT.set_volume(.2)
SOUND_EXPLOSION = load_sound('explosion.wav')
SOUND_EXPLOSION.set_volume(.2)

# Eight directions: N, NE, E, SE, S, SW, W, NW
DIRECTIONS = ((0.0, -2.8), (2.0, -2.0), (2.8, 0.0), (2.0, 2.0)
            , (0.0, 2.8), (-2.0, 2.0), (-2.8, 0.0), (-2.0, -2.0))

def direction(dx, dy):
    if dx >= 0:
        if dy >= 0:
            return 2 if dx>2*dy else 4 if dy>2*dx else 3
        return 2 if dx>-2*dy else 0 if -dy>2*dx else 1
    if dy >= 0:
        return 6 if -dx>2*dy else 4 if dy>-2*dx else 5
    return 6 if -dx>-2*dy else 0 if -dy>-2*dx else 7

# Base class for all that we draw in the SCREEN that cares about Y-order
class Sprite:
    All = []

    def __init__(self, y):
        self.y = y
        bisect.insort(Sprite.All, self)
    def __lt__(self, other):
        return self.y < other.y
    def dissapear(self):
        try: Sprite.All.remove(self)
        except ValueError: pass # Already removed

    def update(self): pass
    def draw(self): pass
    def __repr__(self):
        return self.__class__.__name__+' at Z='+str(self.z)

    @staticmethod
    def updateall():
        for sprite in Sprite.All:
            sprite.update()

    @staticmethod
    def drawall():
        Sprite.All.sort()
        for sprite in Sprite.All:
            sprite.draw()

class Wall(Sprite):
    All = []
    def __init__(self, left, top, width, height):
        Sprite.__init__(self, top+height)
        Wall.All.append(self)
        self.rect = Rect(left, top, width, height)
        self.filltop = ORANGE, Rect(left, top/2-BULLET_HEIGHT, width, height/2)
        self.fillside = BROWN, Rect(left, (top+height)/2-BULLET_HEIGHT, width
            , BULLET_HEIGHT)
    def draw(self):
        global FILL
        FILL(*self.filltop)
        FILL(*self.fillside)
    def dissapear(self):
        Sprite.dissapear(self)
        Wall.All.remove(self)

class LocalControl:
    Instance = None
    def __init__(self, tn, tank, keymap = (pygame.K_UP, pygame.K_RIGHT
            , pygame.K_DOWN, pygame.K_LEFT)):
        self.tn = tn
        self.tank = tank
        self.keymap = keymap
        global LOCAL_CONTROL
        LocalControl.Instance = self
    def update(self):
        pressed = pygame.key.get_pressed()
        uprightdownleft = tuple(pressed[key] for key in self.keymap)
        if sum(uprightdownleft):
            up, right, down, left = uprightdownleft
            self.tank.headto = direction(right-left, down-up)
        else:
            self.tank.headto = None

        self.tank.targetx, self.tank.targety = pygame.mouse.get_pos()
        self.tank.targety += BULLET_HEIGHT
        self.tank.targety *= 2 # Perspective
        self.tank.fire = pygame.mouse.get_pressed()[0]

        from pickle import dumps
        packet = dumps((TURN, self.tn, self.tank.headto, self.tank.targetx
            , self.tank.targety, self.tank.fire))
#        print "=>",repr((TURN, self.tn, self.tank.headto, self.tank.targetx
#            , self.tank.targety, self.tank.fire))
        return packet

class RemoteControl:
    All = {}
    Parsed = {}
    def __init__(self, tn, tank):
        RemoteControl.All[tn] = self
        RemoteControl.Parsed[tn] = None
        self.tank = tank
    def update(self, headto, targetx, targety, fire):
        self.tank.headto = headto
        self.tank.targetx, self.tank.targety = targetx, targety
        self.tank.fire = fire
    @staticmethod
    def parse(packet):
        from pickle import loads
        turn, tn, headto, targetx, targety, fire = loads(packet)
#        print "<=", repr(loads(packet))
        if LocalControl.Instance.tn==tn or TURN!=turn or RemoteControl.Parsed[tn]==turn:
            return False
        RemoteControl.All[tn].update(headto, targetx, targety, fire)
        RemoteControl.Parsed[tn] = turn
        for t in RemoteControl.Parsed.itervalues():
            if t != TURN:
                return False
        return True # Done parsing

class Trail(Sprite):
    def __init__(self, color, x, y):
        self.color = color
        self.x, self.y = x, y
        Sprite.__init__(self, y)
    def draw(self):
        draw.circle(SCREEN, self.color, ints(self.x, self.y/2-BULLET_HEIGHT), 3, 1)
        draw.line(SCREEN, BLACK, (self.x-1, self.y/2), (self.x+1, self.y/2))

class Tank(Sprite):
    All = []
    def __init__(self, color, x, y):
        Sprite.__init__(self, y)
        Tank.All.append(self)
        self.bodies = load_multiimage('tank_body.png', 8, color)
        self.turrets = load_multiimage('tank_turret.png', 8, color)
        self.sx, self.sy = self.bodies[0].get_size()
        w = self.sx
        self.rect = Rect(x-w/2, y-w/2, w, w).inflate(-8,-8)
        self.x, self.y = x, y
        self.color = color
        self.heading = 2 # SE
        self.sound = None
        #self.trail = tuple(Trail(self.color, x, y) for i in xrange(7))
        self.readyamo = 5
        self.reloading = 0
        self.facing = None
        # Controls:
        self.headto, self.fire, self.targetx, self.targety = None, 0, x, y

    def dissapear(self):
        Sprite.dissapear(self)
        Tank.All.remove(self)
        #for t in self.trail: t.dissapear()

    def noise(self, sound):
        if self.sound != sound:
            if self.sound:
                self.sound.stop()
            self.sound = sound
            if self.sound:
                self.sound.play(-1)

    def update(self):
        if self.headto == self.heading:
            self.noise(SOUND_WALK)
            newxy = ( self.x + DIRECTIONS[self.heading][0]
                    , self.y + DIRECTIONS[self.heading][1] )
            self.rect.center = newxy
            # Check for obstacles:
            if self.rect.collidelist(Wall.All) != -1 or 1<len(self.rect.collidelistall(Tank.All)):
                self.rect.center = self.x, self.y
            else:
                self.x, self.y = newxy
        elif self.headto != None:
            self.noise(SOUND_TURN)
            if (self.headto+8-self.heading)&7 <= 4:
                self.heading += 1
            else:
                self.heading -= 1
            self.heading &= 7
        else:
            self.noise(None)

        dx = self.targetx - self.x
        dy = self.targety - self.y
        self.facing = direction(dx, dy)
        #for i in xrange(7):
        #    self.trail[i].x = ((i+1)*self.targetx+(7-i)*self.x)/8
        #    self.trail[i].y = ((i+1)*self.targety+(7-i)*self.y)/8

        # Reload one bullet every 10 ticks:
        if self.reloading:
            self.reloading -= 1
            if not self.reloading:
                self.readyamo += 1
                if self.readyamo < 5:
                    self.reloading = 10

        if self.readyamo and self.fire:
            self.readyamo -= 1
            self.reloading = 10
            distance = math.hypot(dx, dy)
            vx, vy = 10.0*dx/distance, 10.0*dy/distance
            Bullet(self.x+4*vx, self.y+4*vy, vx, vy)

    def draw(self):
        xy = self.x-self.sx/2, (self.y-self.sy-TANK_HEIGHT)/2
        #draw.line(SCREEN, BLACK, (self.x-30, self.y/2), (self.x+30, self.y/2))
        #draw.line(SCREEN, BLACK, (self.x, self.y/2-20), (self.x, self.y/2+20))
        BLIT(self.bodies[self.heading], xy)
        BLIT(self.turrets[self.facing], xy)

    def explode(self):
        Explosion(self.sx, self.rect.center)
        self.dissapear()

TANKS = ( Tank(COLORS[0], FIELD_WIDTH/4, FIELD_HEIGHT/4),
          Tank(COLORS[1], FIELD_WIDTH*3/4, FIELD_HEIGHT*3/4),
          Tank(COLORS[2], FIELD_WIDTH*3/4, FIELD_HEIGHT/4),
          Tank(COLORS[3], FIELD_WIDTH/4, FIELD_HEIGHT*3/4),
          Tank(COLORS[4], FIELD_WIDTH/2, FIELD_HEIGHT/2) )

class Explosion(Sprite):
    def __init__(self, size, xy):
        SOUND_EXPLOSION.play()
        self.size = size
        Sprite.__init__(self, xy[1])
        self.xy = ints(xy[0],xy[1]/2-BULLET_HEIGHT)
    def draw(self):
        draw.circle(SCREEN, RED, self.xy, self.size)
        self.size -= 5
        if 2 > self.size:
            self.dissapear()

class Bullet(Sprite):
    def __init__(self, x, y, vx, vy):
        SOUND_SHOT.play()
        # 8-bit fixed point:
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        # TODO: self.bounces = 1
        self.rect = Rect(0,0,3,3)
        Sprite.__init__(self, y)
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.rect.center = self.x, self.y
        tankhit = self.rect.collidelist(Tank.All)
        if tankhit >= 0:
            Tank.All[tankhit].explode()
            self.explode()
        elif self.rect.collidelist(Wall.All) >= 0:
            self.explode()
    def explode(self):
        Explosion(10, self.rect.center)
        self.dissapear()
    def draw(self):
        draw.circle(SCREEN, WHITE
            , ints(self.x-self.vx/3, (self.y-self.vy/3)/2-BULLET_HEIGHT), 3)
        draw.circle(SCREEN, WHITE, ints(self.x, self.y/2-BULLET_HEIGHT), 3)
        draw.line(SCREEN, BLACK, (self.x-1, self.y/2), (self.x+1, self.y/2))

def DrawBorders():
    margin = 0
    h = 20
    v = (20+BULLET_HEIGHT)*2
    Wall(-margin,        -margin, FIELD_WIDTH+2*margin, margin+v)
    Wall(-margin, FIELD_HEIGHT-v, FIELD_WIDTH+2*margin, v+margin)
    Wall(-margin,        -margin, margin+h, FIELD_HEIGHT+2*margin)
    Wall(FIELD_WIDTH-h,  -margin, h+margin, FIELD_HEIGHT+2*margin)

TURN = 0
def Game(tanks):
    print "Starting game..."
    DrawBorders()

    tile = load_image('ground.png')
    tile_width, tile_height = tile.get_size()

    font = pygame.font.Font(None, 24)

    background = SCREEN.copy()
    for x in xrange(1+SCREEN_WIDTH/tile_width):
        for y in xrange(1+SCREEN_HEIGHT/tile_height):
            background.blit(tile, (x*tile_width, y*tile_height))

    clock = pygame.time.Clock()
    infoline = ''
    infoxy = (10, SCREEN_HEIGHT - font.get_linesize())

    global TURN

    event.set_allowed(pygame.QUIT)
    while not event.peek(pygame.QUIT):
        TURN += 1
        cycletimer = time.time() # pygame.time.get_ticks()

        packet = LocalControl.Instance.update()
        while True:
            SOCKET.sendto(packet, BROADCAST_ADDRESS)
            remote = SOCKET.recv(100)
            if remote[0] == '(' and RemoteControl.parse(remote):
                break
            remote = SOCKET.recv(100)
            if remote[0] == '(' and RemoteControl.parse(remote):
                break
            remote = SOCKET.recv(100)
            if remote[0] == '(' and RemoteControl.parse(remote):
                break

        clock.tick(20) # Throttle: max 20 ticks per second

        Sprite.updateall()

        BLIT(background, (0, 0))
        Sprite.drawall()

        BLIT(font.render(infoline, False, YELLOW), infoxy)
        pygame.display.flip()

        infoline = 'FPS: %0.1f' % (clock.get_fps())
        infoline += ', cycle takes: %.1f ms.' %((time.time()-cycletimer)*1000)
        dx, dy = tanks[0].targetx - tanks[0].x, tanks[0].targety - tanks[0].y
        infoline += ', dx=%d, dy=%d' %(dx, dy)
