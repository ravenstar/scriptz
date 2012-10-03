#!/usr/bin/python
# Imgur Album Downloader
#
# Now with multithreading!
# Just paste the URL of an Imgur album/gallery/subdomain
# at the prompt, and away you go!
#
# Improved by Duane Sibilly <duane@sibilly.com>
# Improved by nodiscc <nodiscc@gmail.com>
# Original Author unknown. (Sorry!)
# CPU detection function courtesty of phihag <phihag@phihag.de>
 
import sys
import os
import re
import time
import urllib
import threading
import subprocess
import datetime
import Queue
import xml.dom.minidom as minidom
 
class ImgurAlbum(object):
    """ Model object for imgur albums """
 
    def __init__(self, name, imageList):
        if (name == ''): # empty album names suck! Make one up!
            print "No album name detected; please provide one!"
            self.name = raw_input('Album Name: ')
        else:
            self.name = name
        self.imageList = imageList
 
    def enqueueImages(self, queue):
        """ Adds the image list to a queue for dispatching """
 
        # make sure the directory exists
        # before the DownloadThreads take over!
#        dirname = 'imgur/' + self.name.replace(' ', '') + '/'
        dirname = './'
        dir = os.path.dirname(dirname)
        if not os.path.exists(dir):
            os.makedirs(dir)
 
        # enqueue the images into the dispatch queue
        for image in self.imageList:
            queue.put(image)
 
class DownloadThread(threading.Thread):
    """ Threaded image downloader """
 
    def __init__(self, albumName, queue):
        threading.Thread.__init__(self)
        self.queue = queue
        self.albumName = albumName
 
    def run(self):
        while True:
            image = self.queue.get()
            origName = image[image.rfind('/') + 1:]
#            fileName = 'imgur/' + self.albumName.replace(' ', '') + '/' + origName
            fileName = origName
 
            if os.path.exists(fileName) != True:
                try:
                    # open the local file and write the image into it...
                    output = open(fileName, 'wb')
                    imgData = urllib.urlopen(image).read()
                    output.write(imgData)
                    output.close()
 
                    # display a nice progress dot (without print's newline)
                    sys.stdout.write('.')
                    sys.stdout.flush()
                except:
                    print "File read error!"
            else: # File already exists; do not overwrite
                print "File %s exists!" % fileName
 
            # signal the dispatch queue that this task is complete
            self.queue.task_done()
 
class PageParser(object):
    """ Imgur gallery page parser """
 
    def __init__(self, url):
        self.url = url
        self.imageList = []
 
    def parse(self):
        self._parse(self.url)
        return ImgurAlbum(self.imageList[0], self.imageList[1:])
 
    def _parse(self, url):
        page = urllib.urlopen(url).read()
 
        if page.find('subdomain_css') != -1:
            links = self._parseSubdomain(url)
 
            for linkURL in links:
                test = self._parse(linkURL)
 
        elif page.find('album_css') != -1:
            self.imageList.extend(self._parseAlbum(url))
 
        elif page.find('gallery_css') != -1:
            self.imageList.extend(self._parseGallery(url))
 
    def _parseSubdomain(self, url):
        page = urllib.urlopen(url).read()
        links = []
        last = 0
 
        tag = '"cover"'
 
        while 1:
 
            last = page.find(tag, last)
 
            if last == -1:
                break
 
            links.append( "http:"+page[page.find('href=', last)+6:page.find('">', last+9)]+"/all" )
 
            last = last + 9
 
        return links
 
    def _parseAlbum(self, url):
        albumimages = []
        page = urllib.urlopen(url).read()
 
        null=False
 
        titleStart = page.find("data-title")+12
        albumimages.append(page[titleStart:page.find('"',titleStart)])
        # print "parsing album"
 
        start = page.find("images:", page.find("ImgurAlbum"))+8
        rawAlbumdata = page[start: page.find("]}", start)+2]
 
        albumdata = eval(rawAlbumdata)
 
        for i in albumdata["items"]:
            albumimages.append( "http://i.imgur.com/"+i["hash"]+i["ext"] )
 
        return albumimages
 
    def _parseGallery(self, url):
        gallery = urllib.urlopen(url).read()
        maxpage = gallery.find("maxPage:")
        pagecount = gallery[maxpage+8:gallery.find(",", maxpage)].replace(' ','')
        baseUrl = gallery.find("baseURL:")
        url = "http://www.imgur.com"+gallery[baseUrl+8:gallery.find(",", baseUrl)].replace(' ','').replace("'",'')
        galleryname = gallery[baseUrl+8:gallery.find(",", baseUrl)].replace(' ','').replace('/','').replace("'",'')
        galleryimages = [galleryname]
 
        for page in range(eval(pagecount)):
            if url[-1:] == "/":
                xmlurl = url + "hot/page/"+str(page)+".xml"
            else:
                xmlurl = url + "/hot/page/"+str(page)+".xml"
 
            xml = urllib.urlopen(xmlurl).read()
 
            print "Page %s" % page
 
            last = 0
 
            xml.count("/hash")
 
            while 1:
                hash = xml.find("<hash>", last)
 
                if hash == -1:
                    break
 
                link =  xml[ hash+6: xml.find("</", hash) ]
 
                extPos = xml.find("<ext>", hash)
                ext = xml[ extPos+5 : xml.find("</", extPos) ]
 
                galleryimages.append( "http://i.imgur.com/"+link+ext )
 
                last = hash+1
 
        return galleryimages
 
def numberOfCPUs():
    """ Determines the number of virtual or physical CPUs on this system.
        Function courtesy of phihag <phihag@phihag.de>
        See: http://stackoverflow.com/questions/1006289/how-to-find-out-the-number-of-cpus-in-python
    """
 
    # Python 2.6+
    try:
        import multiprocessing
        return multiprocessing.cpu_count()
    except (ImportError, NotImplementedError):
        pass
 
    # POSIX
    try:
        res = int(os.sysconf('SC_NPROCESSORS_ONLN'))
 
        if res > 0:
            return res
    except (AttributeError, ValueError):
        pass
 
    # Windows (eww...)
    try:
        res = int(os.environ['NUMBER_OF_PROCESSORS'])
        if res > 0:
            return res
    except (KeyError, ValueError):
        pass
 
    # Jython
    try:
        from java.lang import Runtime
        runtime = Runtime.getRuntime()
        res = runtime.availableProcessors()
        if res > 0:
            return res
    except ImportError:
        pass
 
    # BSD
    try:
        sysctl = subprocess.Popen(['sysctl', '-n', 'hw.cpu'], stdout=subprocess.PIPE)
        scStdout = sysctl.communicate()[0]
        res = int(scStdout)
 
        if res > 0:
            return res
    except (OSError, ValueError):
        pass
 
    # Linux
    try:
        res = open('/proc/cpuinfo').read().count('processor\t:')
        if res > 0:
            return res
    except IOError:
        pass
 
    # Solaris
    try:
        pseudoDevices = os.listdir('/devices/pseudo/')
        expr = re.compile('^cpuid@[0-9]+$')
        res = 0
        for device in pseudoDevices:
            if expr.match(device) != None:
                res += 1
 
        if res > 0:
            return res
    except OSError:
        pass
 
    # Other Unices (heuristic)
    try:
        try:
            dmesg = open('/var/run/dmesg.boot').read()
        except IOError:
            dmesgProcess = subprocess.Popen(['dmesg'], stdout=subprocess.PIPE)
            dmesg = dmesgProcess.communicate()[0]
 
        res = 0
        while '\ncpu' + str(res) + ':' in dmesg:
            res += 1
 
        if res > 0:
            return res
    except OSError:
        pass
 
    # If we can't determine the number of CPUs, default to one
    return 1
 
def main():
    """ Core downloader function """
 
    # Dispatch queue
    queue = Queue.Queue()
 
    # Get user input
    url = raw_input('imgur.com gallery URL: ')
 
    # Parse the imgur gallery/album/subdomain page
    # into an ImgurAlbum object
    p = PageParser(url)
    album = p.parse()
 
    # Scale the number of worker threads to the
    # the smaller of (number of images in album, number of CPUs)
    threads = min(len(album.imageList), numberOfCPUs())
 
    start = time.time()
    print "Fetching '%s' (%d images)" % (album.name, len(album.imageList))
    print "Downloading with %d threads..." % threads
 
    # Spin up the desired number of worker threads
    for i in range(threads):
        dt = DownloadThread(album.name, queue)
        dt.setDaemon(True)
        dt.start()
 
    # Pour the images into the dispatch queue
    # to start our work...
    album.enqueueImages(queue)
 
    # block until queue is empty
    queue.join()
    print "\n"
    print "DONE! Elapsed time: %.2f seconds" % (time.time() - start)
 
if __name__ == "__main__":
    main()
