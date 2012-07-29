#! /usr/bin/env python
# coding=utf-8 *** KatanK by gatopeich 2010
"""
KnatanK (c) gatopeich 2011,2012
All rights reserved until I find an adequate license

Networking
"""

import socket
SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
PORT = 55555
BROADCAST = '<broadcast>'
BROADCAST_ADDRESS = (BROADCAST, PORT)
SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
SOCKET.bind(('', PORT))
SOCKET.settimeout(0.050)
#SOCKET.connect(BROADCAST_ADDRESS) # TODO: connect to broadcast port?!
MAXLEN = 128

def SEND(packet):
    try: SOCKET.sendto(packet, BROADCAST_ADDRESS)
    except socket.timeout: print "Socket overflow!?"

def RECEIVE():
    try:
        while True: yield SOCKET.recv(MAXLEN)
    except socket.timeout: pass

def RECVFROM():
    try:
        while True: yield SOCKET.recvfrom(MAXLEN)
    except socket.timeout: pass


