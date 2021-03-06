#!/usr/bin/env python
'''
    Created Dec 1, 2009
    Main driver for application
    Author: Sam Gleske
'''

import socket,sys,os.path,eventlet,binascii,urllib2,re
from lib import *
from time import sleep
from time import ctime
from sys import exit

proxyRegEx=re.compile("([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\:[0-9]{1,5})") #general ip:proxy regular expression
TAB = "\t"
NEW_LINE = "\n"
wpad=GenerateWPAD()

'''
    make configuration adjustments based on given arguments 
'''
try:
    config=SwitchParser(sys.argv)
    print "Proxytester v0.8"
    print "Generate wpad.dat:", str(config.WPAD)
    if config.Threads > 1:
        print "Multi-Threading: Enabled"
    else:
        print "Multi-Threading: Disabled"
    if config.simulateConnect :
        print "Simulate Working Proxies: On"
    else:
        print "Simulate Working Proxies: Off"
    if config.excludeFile == None :
        print "Exclude certain proxies: False"
    else:
        print "Exclude certain proxies: False"
    print "Testing URL:", config.restrictedURL
    print "Check proxy response against:",config.responseFile
    print "Proxy Timeout:", str(config.Timeout)
    print "Unique List:", str(config.unique)

    #remove duplicate file entries
    if len(config.fileList) != 0 :
        config.fileList=UniqueList(config.fileList).unique
    else:
        print "Must specify at least one proxy list file."
        config.syntaxErr()

    #test to make sure all files exist
    for filename in config.fileList:
        if not os.path.isfile(filename) and proxyRegEx.match(filename) == None:
            print ""
            print "All files in fileList must exist!"
            print "All proxies in fileList must be x.x.x.x:port format"
            config.syntaxErr()
        elif filename == config.outFile:
            print "One of your fileList files are the same as your outFile"
            config.syntaxErr()
    if not config.quietMode :
        if config.outFile != None :
            if os.path.isfile(config.outFile) :
                answer=raw_input("It appears your outFile already exists!" + NEW_LINE + "Do you want to overwrite (Y/N)?: ")
                if answer.upper() not in ('Y','YE','YES') :
                    print "User aborted command!"
                    exit()

    #generate a crc32 on the URL if there is no response specified...
    if config.Response == None :
        config.Response = binascii.crc32(urllib2.urlopen(config.restrictedURL).read())
except KeyboardInterrupt:
    print ""
    print "Process aborted by user!"
    exit()

#testing swich accuracy only
# print proxyRegEx.match("192.168.1.1:3125")
# print proxyRegEx.match("192.168.1.1")
# print "config.Response: " + str(config.Response)
# print "config.outFile: " + str(config.outFile)
# print "config.fileList: " + str(config.fileList)
# print "config.WPAD: " + str(config.WPAD)
# print "config.Threads: " + str(config.Threads)
# print "config.quietMode: " + str(config.quietMode)
# print "config.restrictedURL: " + config.restrictedURL
# print "config.Timeout: " + str(config.Timeout)
# print "config.unique:", str(config.unique)
# exit()

'''
    checkProxy function!
    the status will be True if the proxy is good for use!
'''
def checkProxy(pip):
    status=-1
    if config.simulateConnect :
        if pip != "" :
            print pip, "is working"
            status = True
        else :
            status = False
        return (pip, status)
    try:
        proxy_handler = urllib2.ProxyHandler({'http': pip})
        opener = urllib2.build_opener(proxy_handler)
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        urllib2.install_opener(opener)
        req = urllib2.Request(config.restrictedURL)
        sock = urllib2.urlopen(req)
        if config.Response != None:
            response = sock.read();
            crc32 = binascii.crc32(response)
            if crc32 != config.Response:
                status = False
        if not status :
            print "ERROR: Response test failed"
            print "Bad Proxy", pip
    except urllib2.HTTPError, e:
        print 'Error code: ', e.code
        print "Bad Proxy", pip
        status = False
    except Exception, detail:
        print "ERROR:", detail
        print "Bad Proxy", pip
        status = False
    finally:
        if status == -1:
            print pip, "is working"
            status = True
    return (pip, status)

'''
    Beginning of proxytester checking
    Enough properties have been set up.
'''

started = ctime()
try:
    # read the list of proxy IPs in proxyList
    proxyList=[]
    for filepath in config.fileList:
        #determine if file or proxy
        if proxyRegEx.match(filepath) == None :
            f=open(filepath, 'r')
            fileContents = f.read()
            contentsList = fileContents.split(NEW_LINE)
            f.close()
            for line in contentsList:
                proxyList.append(line)
        else:
            proxyList.append(filepath)
    if config.unique :
        proxyList=UniqueList(proxyList).unique

    if config.WPAD:
        #test for wpad overwrite
        if not config.quietMode :
            if os.path.isfile('wpad.dat') :
                answer=raw_input("It appears your wpad.dat file already exists!" + NEW_LINE + "Do you want to overwrite (Y/N)?: ")
                if answer.upper() not in ('Y','YE','YES') :
                    print "User aborted command!"
                    exit()

        f = open('wpad.dat', 'w')

        #write the wpad header
        for line in wpad.head:
            f.write(line)

    if config.outFile != None :
        n = open(config.outFile, 'w')

except KeyboardInterrupt:
    print ""
    print "Process aborted by user!"
    exit()

'''
    Eventlet code!
    Create a new thread for each proxy to be checked.
    If the proxy works then populate a new list comprising of working proxies.
'''
try:
    print ""
    print "Results:"
    from eventlet.green import urllib2
    socket.setdefaulttimeout(config.Timeout)
    pool = eventlet.GreenPool(size = config.Threads)
    tested_proxies = []
    for line in proxyList:
        if line in config.excludeServers :
            proxyList.remove(line)
    for result in pool.imap(checkProxy,proxyList):
        if result[1] and result[0] != "" and result[0] != None :
            tested_proxies.append(result[0])
except KeyboardInterrupt:
    print ""
    print "Process aborted by user!"
    print "Processing tested proxies."
# End of eventlet code!

'''
    Process results of tested proxies
'''
try:
    firstline = False
    for item in tested_proxies:
        item=str(item)
        if config.outFile != None :
            n.write(item + NEW_LINE)
        if config.WPAD:
            if not firstline:
                f.write('"' + item + '"')
                firstline = True
            else:
                f.write(',' + NEW_LINE + TAB + TAB + TAB + '"' + item + '"')

    #write the wpad footer
    if config.WPAD:
        for line in wpad.foot:
            f.write(line)
    if config.outFile != None :
        n.close()
    if config.WPAD:
        f.close()
    ended = ctime()
    print ""
    print "Process Started:", started
    print "Process Ended:", ended
    tsplit=str(ended).split(" ")[3].split(":")
    ended=int(tsplit[0]) * 3600 + int(tsplit[1]) * 60 + int(tsplit[2])
    tsplit=str(started).split(" ")[3].split(":")
    started=int(tsplit[0]) * 3600 + int(tsplit[1]) * 60 + int(tsplit[2])
    secs=ended-started
    #Print the runtime in # hrs # mins # secs
    print "Runtime:",secs/3600,"hrs",secs/60 - secs/3600*60,"mins",60*(secs%60)/100,"secs",NEW_LINE
except KeyboardInterrupt:
    print ""
    print "Process aborted by user!"
    exit()
exit(0)