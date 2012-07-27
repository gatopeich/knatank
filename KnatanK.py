#! /usr/bin/env python
# coding=utf-8
"""
KnatanK (c) gatopeich 2011
All rights reserved until I find an adequate license

TODO:
* Assure bullet does not hit own tank while shooting.
* Extra collision detection for bullets or improve it somehow.
* Remote-observed game: client+server.
* Remote-controlled tanks.
* Collisionable subclass of Sprite.
* Round, square and 'line' collision patterns.
* Explosions can collide too.
* Better looks for walls.
* AI tanks. Like in Wii: static, moving, aggressive, miner...
* Maps.
* Bouncing bullets.
* Mines.

DONE:
* Color transformation by extracting a set then transforming it then applying.
* Visual height of explosions.
* FIX Multiple collision -> ValueError: All.remove(x): x not in All.
"""

import pygame, time, bisect
from pygame import event, Rect
from utility import XY
import game
from game import RED, YELLOW, WHITE, BLACK, FONT_TITLE, FONT_MENU, TANKS
from game import SCREEN_HEIGHT, SCREEN_WIDTH, FILL, BLIT, Game
from game import SOCKET, PORT, BROADCAST_ADDRESS

import signal
def signal_handler(signal, frame):
    pygame.quit()
    exit
signal.signal(signal.SIGINT, signal_handler)

def Lobby():
    # Start network connections
    import socket
    SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    SOCKET.bind(('', PORT))
    SOCKET.settimeout(0.100)
    #SOCKET.connect(BROADCAST_ADDRESS) # TODO: connect to broadcast port?!

    players = []
    import uuid
    my_id = uuid.uuid4().hex
    info = "Waiting for players..."

    title = FONT_TITLE.render('KnatanK', True, RED, YELLOW)
    start_button = FONT_TITLE.render(' Start! ', True, WHITE, RED)
    start_button = ( start_button
        , Rect(60, SCREEN_HEIGHT-60-FONT_TITLE.get_height()
            , *start_button.get_size()))

    event.set_allowed((pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN, pygame.QUIT))
    event.clear()
    ready_to_start = False
    while not ready_to_start:
        for e in event.get():
            if((e.type == pygame.MOUSEBUTTONDOWN
                 and start_button[1].collidepoint(e.pos))
            or (e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE) ):
                ready_to_start = True
                SOCKET.sendto('START', BROADCAST_ADDRESS)
            elif( e.type == pygame.QUIT
            or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE) ):
                print "User quit."
                pygame.quit()
                return

        try:
            SOCKET.sendto(my_id, BROADCAST_ADDRESS) #SOCKET.send(my_id)
            msg, address = SOCKET.recvfrom(100)
            if msg == 'START':
                break
            if msg not in players:
                bisect.insort(players, msg)
                info = str(len(players)) + ' players connected.'
                print "New player from", address, ":", msg, ".", info
        except socket.timeout: pass

        FILL(YELLOW, Rect(40, 40, SCREEN_WIDTH-80, SCREEN_HEIGHT-80))
        xy = XY(50, 50)
        BLIT(title, xy)
        xy = xy + XY(0, FONT_TITLE.get_linesize())
        BLIT(FONT_MENU.render(info, True, BLACK, YELLOW), xy)
        xy = xy + XY(0, FONT_MENU.get_linesize())
        for i in xrange(len(players)):
            tank = TANKS[i]
            BLIT(tank.bodies[3], xy)
            BLIT(tank.turrets[3], xy)
            BLIT(FONT_MENU.render("Player " + str(i+1)
                + (" (you!)" if players[i] == my_id else "")
                , True, BLACK, YELLOW)
                , xy + XY(tank.sx+10, (tank.sy-FONT_MENU.get_height())/2))
            xy += XY(0, tank.sy)
        BLIT(*start_button)

        pygame.display.flip()
        time.sleep(1)

    global NPLAYERS
    NPLAYERS = len(players)
    for i in xrange(NPLAYERS):
        if players[i] == my_id:
            game.LocalControl(i, TANKS[i])
        else:
            game.RemoteControl(i, TANKS[i])

    Game(TANKS[:len(players)])
    print "Game Over."

Lobby()
