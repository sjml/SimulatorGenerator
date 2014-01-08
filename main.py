import os
import ConfigParser
import requests
from xml.dom import minidom
import json
import random
import mimetypes
import datetime
import subprocess

creds = ConfigParser.ConfigParser()
creds.read("credentials.ini")

def getJobTitle():
    # TODO: store off the category, don't repeat job titles, rotate categories
    #   http://api.careerbuilder.com/CategoryCodes.aspx

    cb_apiKey = creds.get("careerbuilder", "apikey")
    params = {
        "DeveloperKey" : cb_apiKey,
        "HostSite" : "US",
        "OrderBy" : "Date",
    }
    cb_URL = "http://api.careerbuilder.com/v1/jobsearch?"
    for key, value in params.iteritems():
        cb_URL += "%s=%s&" % (key, value)
    cb_URL = cb_URL[:-1]

    response = requests.get(cb_URL)
    dom = minidom.parseString(response.content)
    # dom = minidom.parse(open("sample_jobsearch.xml"))
    jobs = []
    for node in dom.getElementsByTagName("JobTitle"):
        jobs.append(node.firstChild.nodeValue)
    return random.choice(jobs)

def getImageFor(searchTerm):
    is_params = {"v":"1.0", "q":searchTerm, "imgType":"photo"}
    headers = {"Referer" : "https://twitter.com/SimGenerator"}
    is_URL = "https://ajax.googleapis.com/ajax/services/search/images"

    imageResults = requests.get(is_URL, params=is_params).json()
    # imageResults = json.load(open("sample_imagesearch.json"))
    imageData = []
    for image in imageResults['responseData']['results']:
        imageData.append(
            {
                "url" : image['url'], 
                "h" : int(image['height']), 
                "w" : int(image['width']), 
                "size" : int(image['width']) * int(image['height'])
            }
        )
    imageData.sort(reverse=True, key=lambda img: img['size'])

    mimetypes.init()
    for img in imageData:
        r = requests.head(img['url'])
        if not r.ok:
            # can't download for whatever reason
            continue

        extension = mimetypes.guess_extension(r.headers['Content-Type'])
        if (extension == ".jpe") : extension = ".jpg"

        localFileName = "tmp/base_image-%s%s" % (datetime.datetime.now().strftime("%Y-%m-%d-%H%M"), extension)
        baseFile = open(localFileName, 'wb')
        imgResponse = requests.get(img['url'])
        baseFile.write(imgResponse.content)
        baseFile.close()

        # check our work
        cmdLine = ['identify', '-format', '%[fx:w]x%[fx:h]', localFileName]
        dimensionString = subprocess.Popen(cmdLine, stdout=subprocess.PIPE).communicate()[0]
        dimensions = dimensionString.split("x")
        print dimensions
        if (int(dimensions[0]) == img['w'] and int(dimensions[1]) == img['h']):
            return localFileName

def createBoxArt(jobTitle, localImgFile):
    outputFile = "output-%s.png" % (datetime.datetime.now().strftime("%Y-%m-%d-%H%M"))

    options = [
        ("-size", "%w%h"),
        ("-font", "'./helvetica-ultra-compressed.ttf'"),
        ("-pointsize", "100"),
        ("-fill", "white"),
        ("-interline-spacing", "15"),
        ("-stroke", "gray",),
        ("-gravity", random.choice(("NorthWest", "NorthEast", "SouthWest", "SouthEast"))),
        ("-annotate", "0x10+20+20 '%s\nSimulator 2014'" % (jobTitle))
    ]

    exeLine = "convert %s %s %s" % (localImgFile, ''.join('%s %s ' % o for o in options), outputFile)
    print(exeLine)
    os.system(exeLine)
    os.system("rm %s" % (localImgFile))

job = getJobTitle()
image = getImageFor(job)
createBoxArt(job, image)
