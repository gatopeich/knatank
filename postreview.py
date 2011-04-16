#!/usr/bin/python

import subprocess

def post_to_review():

    args = '-r modsrm@gmail.com,agustin.ferrin@gmail.com,hosny.ahmed@gmail.com,' \
    'kirks@tcd.ie --base_url . --rev .^ --send_mail --private'

    retval = subprocess.call('tools/upload.py ' + args, shell = True)

    assert( retval == 0 )

post_to_review()
