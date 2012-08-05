# -*- coding: utf-8 -*-
"""
KnatanK (c) gatopeich 2011,2012
All rights reserved until I find an adequate license
"""

import pygame, time, math, bisect
from pygame import draw, event, Rect
from utility import load_image, load_multiimage, load_sound, ints, XY
from networking import SEND, RECEIVE

### GLOBALS
MAXFPS = 40
MAX_BULLETS = 3
RELOAD_TIME = MAXFPS

# Dimensions
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
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
pygame.mixer.pre_init(frequency=22050, buffer=256) # low latency settings
pygame.init()
pygame.display.set_caption("KnatanK")
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.mouse.set_cursor(*pygame.cursors.broken_x)
BACKGROUND = SCREEN.copy()

# Global methods:
def TicksMs(): return time.time()*1000
BLIT = SCREEN.blit
FILL = SCREEN.fill

SCREEN_WIDTH, SCREEN_HEIGHT = SCREEN.get_size()
FIELD_WIDTH, FIELD_HEIGHT = SCREEN_WIDTH, SCREEN_HEIGHT*2

FONT = pygame.font.Font(None, 24)
FONT_MENU = pygame.font.Font(None, 30)
FONT_TITLE = pygame.font.Font(None, 100)
FONT_TITLE.set_bold(True)
FONT_TITLE.set_italic(True)

# Sounds:
SOUND_WALK = load_sound('WalkingToyLoop.wav')
SOUND_WALK.set_volume(.2)
SOUND_TURN = load_sound('WalkingToyLoop-slow.wav')
SOUND_TURN.set_volume(.2)
SOUND_SHOT = load_sound('shot.wav')
SOUND_SHOT.set_volume(.2)
SOUND_BOUNCE = load_sound('bounce.wav')
SOUND_BOUNCE.set_volume(.2)
SOUND_RELOAD = load_sound('reload.wav')
SOUND_RELOAD.set_volume(.2)
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
        Sprite.All.remove(self)

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
        Wall.All.remove(self)
        Sprite.dissapear(self)

class LocalControl:
    Instance = None
    def __init__(self, tn, tank):
        self.tn = tn
        self.tank = tank
        self.keymap = (pygame.K_w, pygame.K_d, pygame.K_s, pygame.K_a)
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
        self.tank.fire = min(self.tank.readyamo, self.tank.fire +
             sum(e.button == 1 for e in event.get(pygame.MOUSEBUTTONDOWN)))

        from cPickle import dumps
        packet = dumps((TURN, self.tn, self.tank.headto, self.tank.targetx
            , self.tank.targety, self.tank.fire),1)
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
        if len(RemoteControl.All) == 0: return True
        if packet[0] == '(':
            from cPickle import loads
            turn, tn, headto, targetx, targety, fire = loads(packet)
            #print "<=", repr(loads(packet))
            if LocalControl.Instance.tn==tn or TURN!=turn or RemoteControl.Parsed[tn]==turn:
                return False
            RemoteControl.All[tn].update(headto, targetx, targety, fire)
            RemoteControl.Parsed[tn] = turn
        for t in RemoteControl.Parsed.itervalues():
            if t != TURN:
                return False
        return True # Done parsing current turn

class Mire(Sprite):
    def __init__(self, color, x, y):
        Sprite.__init__(self, y)
        self.color = color
        self.aim(x,y)
    def aim(self, x, y):
        self.x, self.y = x, y-30
    def draw(self):
        x,y = ints(self.x,(self.y+30)/2)
        draw.circle(SCREEN, self.color, (x,y+1), 3, 0)
        draw.line(SCREEN, self.color, (x-8, y-4), (x+10, y+5), 2)
        draw.line(SCREEN, self.color, (x-10, y+5), (x+8, y-4), 2)

class Tank(Sprite):
    All = []
    def __init__(self, color, x, y):
        Sprite.__init__(self, y)
        Tank.All.append(self)
        self.bodies = load_multiimage('tank_body.png', 8, color)
        #self.turrets = load_multiimage('tank_turret.png', 8, color)
        self.turrets = load_multiimage('happy+turret.png', 8, color)
        self.sx, self.sy = self.bodies[0].get_size()
        w = self.sx
        self.rect = Rect(x-w/2, y-w/2, w, w).inflate(-8,-8)
        self.x, self.y = x, y
        self.color = color
        self.heading = self.facing = 3 # SE
        self.sound = None
        self.mire = Mire(self.color, x, y)
        self.readyamo = 3
        self.reloading = 0
        # Controls:
        self.headto, self.fire, self.targetx, self.targety = None, 0, x, y

    def dissapear(self):
        if self.sound: self.sound.stop()
        Sprite.dissapear(self)
        Tank.All.remove(self)
        #for t in self.trail: t.dissapear()

    def noise(self, sound):
        if self.sound != sound:
            if self.sound:
                self.sound.stop()
            self.sound = sound
            if sound:
                sound.play(-1)

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

        self.mire.aim(self.targetx, self.targety)
        dx,dy = self.targetx - self.x, self.targety - self.y
        self.facing = direction(dx, dy)

        if self.fire and self.readyamo:
            self.fire -= 1
            self.readyamo -= 1
            self.reloading = RELOAD_TIME # STRATEGY: Firing restarts reload
            Bullet(self.x, self.y, dx, dy)
        elif self.reloading:
            self.reloading -= 1
            if not self.reloading:
                SOUND_RELOAD.play()
                self.readyamo += 1
                if self.readyamo < MAX_BULLETS:
                    self.reloading = RELOAD_TIME

    def render(self, xy):
        #draw.line(SCREEN, BLACK, (self.x-30, self.y/2), (self.x+30, self.y/2))
        #draw.line(SCREEN, BLACK, (self.x, self.y/2-20), (self.x, self.y/2+20))
        BLIT(self.bodies[self.heading], xy)
        BLIT(self.turrets[self.facing], XY(0,-17)+xy)

    def draw(self):
        self.render((self.x-self.sx/2, (self.y-self.sy-TANK_HEIGHT)/2))

    def hit(self):
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
    All = {}
    def __init__(self, x, y, dx, dy):
        SOUND_SHOT.play()
        self.vx, self.vy = vx, vy = XY(dx, dy)*(10/math.hypot(dx, dy))
        Sprite.__init__(self, y + 4*vy)
        self.x = x + 4*vx
        self.rect = Rect(0,0,5,5)
        self.bounces = 2
        Bullet.All[self] = self
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.rect.center = self.x, self.y
        tankhit = self.rect.collidelist(Tank.All)
        if tankhit >= 0:
            Tank.All[tankhit].hit()
            self.explode()
            return
        if self.rect.collidelist(Wall.All) >= 0:
            if self.bounces:
                self.bounces -= 1
                r = self.rect.copy()
                # Try horizontal bounce...
                bounce_x = self.x-self.vx
                r.centerx = bounce_x
                if r.collidelist(Wall.All) < 0:
                    SOUND_BOUNCE.play()
                    self.vx = -self.vx
                    self.x = bounce_x
                    self.rect = r
                    return
                # Try vertical:
                bounce_y = self.y-self.vy
                r.center = self.x, bounce_y
                if r.collidelist(Wall.All) < 0:
                    self.vy = -self.vy
                    self.y = bounce_y
                    self.rect = r
                    SOUND_BOUNCE.play()
                    return
                # Try both:
                if self.bounces:
                    r.centerx = bounce_x
                    if self.rect.collidelist(Wall.All) < 0:
                        SOUND_BOUNCE.play()
                        self.bounces -= 1
                        self.vx, self.vy = -self.vx, -self.vy
                        self.x, self.y = bounce_x, bounce_y
                        self.rect = r
                        return
            self.explode()
            return
        r = self.rect.copy()
        self.rect.y = -999 # avoid self collision by going OOS
        nearby = r.inflate(10,10).collidedictall(Bullet.All)
        if nearby:
            for aoi in (r, r.move(-self.vx,-self.vy)):
                colliding = aoi.collidedict(dict(nearby))
                if colliding:
                    colliding[0].explode()
                    self.explode()
                    return
        self.rect = r # restore

    def explode(self):
        Explosion(10, (self.x, self.y))
        del Bullet.All[self]
        self.dissapear()
    def draw(self):
        draw.circle(SCREEN, WHITE
            , ints(self.x-self.vx/3, (self.y-self.vy/3)/2-BULLET_HEIGHT), 3)
        draw.circle(SCREEN, WHITE, ints(self.x, self.y/2-BULLET_HEIGHT), 3)
        draw.line(SCREEN, BLACK, (self.x-1, self.y/2), (self.x+1, self.y/2))

def DrawLevel():
    margin = 0
    h = 20
    v = (20+BULLET_HEIGHT)*2
    Wall(-margin,        -margin, FIELD_WIDTH+2*margin, margin+v)
    Wall(-margin, FIELD_HEIGHT-v, FIELD_WIDTH+2*margin, v+margin)
    Wall(-margin,        -margin, margin+h, FIELD_HEIGHT+2*margin)
    Wall(FIELD_WIDTH-h,  -margin, h+margin, FIELD_HEIGHT+2*margin)
    tile = load_image('ground.png')
    tile_width, tile_height = tile.get_size()

    for x in xrange(1+SCREEN_WIDTH/tile_width):
        for y in xrange(1+SCREEN_HEIGHT/tile_height):
            BACKGROUND.blit(tile, (x*tile_width, y*tile_height))

TURN = 0
def Game(nplayers):
    print "Starting game..."
    DrawLevel()

    clock = pygame.time.Clock()
    infoline = ''
    infoxy = (10, SCREEN_HEIGHT - FONT.get_linesize())

    totalnetdelay = 0.0
    totalupdatedelay = 0.0
    lastpacket = '!'
    event.set_allowed(None)
    event.set_allowed((pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN))
    while True:
        global TURN
        TURN += 1
        mypacket = LocalControl.Instance.update()

        netdelay = -TicksMs()
        SEND(mypacket)
        SEND(mypacket) # 2X redundancy

        missing_data = True
        while missing_data:
            # Parse events while packets fly
            for e in event.get((pygame.QUIT, pygame.KEYDOWN)):
                if( e.type == pygame.QUIT or (e.type == pygame.KEYDOWN
                        and e.key == pygame.K_ESCAPE) ):
                    print "User quit."
                    exit()

            for remote_msg in RECEIVE():
                if RemoteControl.parse(remote_msg):
                    missing_data = False
                    break
            if missing_data:
                SEND(lastpacket)
                SEND(mypacket)

        netdelay += TicksMs()

        lastpacket = mypacket
        SEND(lastpacket)

        totalnetdelay += netdelay

        updatedelay = -TicksMs()
        Sprite.updateall()
        BLIT(BACKGROUND, (0, 0))
        Sprite.drawall()
        BLIT(FONT.render(infoline, False, YELLOW), infoxy)
        pygame.display.flip()
        updatedelay += TicksMs()

        totalupdatedelay += updatedelay
        infoline = ( 'FPS: %0.1f' % (clock.get_fps()) + ', network delays %0.1f'
            % netdelay + ' ms (avg=%0.1f' % (totalnetdelay/TURN)
            + '), update takes %0.1f' % updatedelay + ' ms (avg=%0.1f'
            % (totalnetdelay/TURN) + ').')

        clock.tick(MAXFPS) # Throttle: max ticks per second
