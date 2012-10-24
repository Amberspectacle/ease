#!/usr/bin/env python
"""
Send some test programs to an xserver.

For each dir in the current directory, send the contents of payload.xml and each
of the answer*.py, right*.py and wrong*.py files.
"""

import argparse
import glob
import json
import os
import os.path
from path import path
import requests
import sys
import time

xserver = 'http://127.0.0.1:3031/'

def send(payload, answer):
    """
    Send a grading request to the xserver
    """

    body = {'grader_payload': payload,
            'student_response': answer}

    data = {'xqueue_body': json.dumps(body),
            'xqueue_files': ''}

    start = time.time()
    r = requests.post(xserver, data=json.dumps(data))
    end = time.time()
    print "Request took %.03f sec" % (end - start)

    if r.status_code != requests.codes.ok:
        print "Request error:{0}".format(r.headers)

    print "Text: ", r.text
    return r.text


def check_contains(string, substr):
    if not substr in string:
        print "ERROR: Expected '{0}' in '{1}'".format(substr, string)

def check_not_contains(string, substr):
    if substr in string:
        print "ERROR: Expected '{0}' not to be in '{1}'".format(substr, string)

def check_right(string):
    check_contains(string, '\"correct\": true')

def check_wrong(string):
    check_contains(string, '\"correct\": false')

def globs(dirname, *patterns):
    """
    Produce a sequence of all the files matching any of our patterns in dirname.
    """
    for pat in patterns:
        for fname in glob.glob(os.path.join(dirname, pat)):
            yield fname

def contents(fname):
    """
    Return the contents of the file `fname`.
    """
    with open(fname) as f:
        return f.read()

def check(dirname):
    """
    Look for payload.json, answer*.py, right*.py, wrong*.py, run tests.
    """
    payload_file = os.path.join(dirname, 'payload.json')
    if os.path.isfile(payload_file):
        payload = contents(payload_file)
        print("found payload: " + payload)
    else:
        graders = list(globs(dirname, 'grade*.py'))
        if not graders:
            #print "No payload.json or grade*.py in {0}".format(dirname)
            return
        if len(graders) > 1:
            print "More than one grader in {0}".format(dirname)
            return
        payload = json.dumps({'grader': os.path.abspath(graders[0])})

    for name in globs(dirname, 'answer*.txt', 'right*.py'):
        print "Checking correct response from {0}".format(name)
        answer = contents(name)
        check_right(send(payload, answer))

    for name in globs(dirname, 'wrong*.txt'):
        print "Checking wrong response from {0}".format(name)
        answer = contents(name)
        check_wrong(send(payload, answer))

def main(argv):
    global xserver

    #parser = argparse.ArgumentParser(description="Send dummy requests to a qserver")
    #parser.add_argument('server')
    #parser.add_argument('root', nargs='?')

    #args = parser.parse_args(argv)

    #xserver = args.server
    if not xserver.endswith('/'):
        xserver += '/'

    #root = args.root or '.'
    root=os.path.dirname( os.path.abspath(__file__ ))
    for dirpath, _, _ in os.walk(root):
        print("checking" + dirpath)
        check(dirpath)

if __name__=="__main__":
    main(sys.argv[1:])
