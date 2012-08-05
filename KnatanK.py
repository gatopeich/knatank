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

import pygame, time
from pygame import event, Rect
from utility import XY
import game
from game import RED, YELLOW, WHITE, BLACK, FONT_TITLE, FONT_MENU, TANKS
from game import SCREEN_HEIGHT, SCREEN_WIDTH, FILL, BLIT, Game
from networking import SEND, RECVFROM

import signal
def signal_handler(signal, frame):
    pygame.quit()
    exit
signal.signal(signal.SIGINT, signal_handler)

def Lobby():
    title = FONT_TITLE.render('KnatanK', True, RED, YELLOW)
    start_button = FONT_TITLE.render(' Start! ', True, WHITE, RED)
    start_button = ( start_button
        , Rect(60, SCREEN_HEIGHT-60-FONT_TITLE.get_height()
            , *start_button.get_size()))

    info = "Waiting for players..."

    event.set_allowed((pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN, pygame.QUIT))
    event.clear()

    players = {}
    import uuid
    my_id = uuid.uuid4().get_hex()
    I_am_ready = False
    all_ready = False
    while not all_ready:
        for e in event.get():
            if((e.type == pygame.MOUSEBUTTONDOWN
                 and start_button[1].collidepoint(e.pos))
            or (e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE) ):
                I_am_ready = True
            elif( e.type == pygame.QUIT
            or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE) ):
                print "User quit."
                pygame.quit()
                exit()

        from cPickle import dumps, loads
        SEND(b'KL' + dumps((my_id, I_am_ready)))
        for msg, address in RECVFROM():
            if msg.startswith(b'KL'):
                player = loads(msg[2:])
                players[player[0]] = player
                info = str(len(players)) + ' players connected.'
                if player[0] not in players:
                    print "New player from", address, ":", player, ".", info
                    print players

        FILL(YELLOW, Rect(40, 40, SCREEN_WIDTH-80, SCREEN_HEIGHT-80))
        xy = XY(50, 50)
        BLIT(title, xy)
        xy = xy + XY(0, FONT_TITLE.get_linesize())
        BLIT(FONT_MENU.render(info, True, BLACK, YELLOW), xy)
        xy = xy + XY(0, FONT_MENU.get_height()*2)

        # Brief up all players:
        playerlist = sorted(players.itervalues())
        for p, tank, player in zip(xrange(1,99), TANKS, playerlist):
            tank.render(xy)
            BLIT(FONT_MENU.render("Player " + str(p)
                + (" (you!)" if player[0] == my_id else "")
                + (" READY!" if player[1] else "")
                , True, BLACK, YELLOW)
                , xy + XY(tank.sx+10, (tank.sy-FONT_MENU.get_height())/2))
            xy += XY(0, tank.sy)
        BLIT(*start_button)

        all_ready = players and all(p[1] for p in playerlist)

        pygame.display.flip()
        time.sleep(1)

    nplayers = len(playerlist)
    for tn, tank in enumerate(TANKS,1):
        if tn > nplayers:
            game.AIControl(tn, tank)
        elif playerlist[tn-1][0] == my_id:
            game.LocalControl(tn, tank)
        else:
            game.RemoteControl(tn, tank)

    Game(nplayers)
    print "Game Over."

try:
    Lobby()
except (KeyboardInterrupt, SystemExit):
    print "Shutting down..."
    pygame.quit()
