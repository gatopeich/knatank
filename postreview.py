#!/usr/bin/python

import subprocess
import sys

def get_reviewers_email():

    email_file = open('tools/reviewers.conf', 'r')
    comma_sep_email_list = ''

    for line in email_file:
        if len(line[:-1]) > 0:
            comma_sep_email_list += line[:-1] + ','

    return comma_sep_email_list[:-1]

def post_to_review():

    args = '-r ' + get_reviewers_email() + ' --base_url . --rev .^ --send_mail --private'

    proc = subprocess.Popen('hg identify -i -b', shell=True, stdout=subprocess.PIPE)

    output = proc.communicate()
    retval = proc.returncode
    assert( retval == 0 )

    if output[0].split(' ')[0].endswith('+'):
        print 'You have uncommitted changes in your working copy!'
        sys.exit(1)

    retval = subprocess.call('tools/upload.py ' + args, shell = True)

    assert( retval == 0 )

post_to_review()
