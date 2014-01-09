import os
import ConfigParser
import requests
from xml.dom import minidom
import json
import random
import mimetypes
import datetime
import subprocess
import twitter

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
        if (int(dimensions[0]) == img['w'] and int(dimensions[1]) == img['h']):
            return localFileName

def cap(value, maxVal):
    if (value < maxVal):
        return value
    else:
        return maxVal

def wpl(totalwords, current=None):
    if (current == None):
        current = []

    if (totalwords == 0):
        return current
    if (totalwords == 1):
        current.append(1)
        return current
    if (totalwords % 3 == 0):
        return current + [3]*(totalwords/3)
    current.append(2)
    return wpl(totalwords-2, current)

def createBoxArt(jobTitle, localImgFile, year):
    grav = random.choice(("NorthWest", "NorthEast", "SouthWest", "SouthEast"))
    if grav[-4:] == "West":
        align = "West"
    else:
        align = "East"

    wordlist = jobTitle.split()
    wordsPerLine = wpl(len(wordlist))
    jobTitle = ""
    indent = " "
    for wordCount in wordsPerLine:
        while wordCount > 0:
            jobTitle += wordlist.pop(0) + " "
            wordCount -= 1
        jobTitle += "\n"
        if (align == "West"):
            jobTitle += indent
            indent += " "
    jobTitle = "'%sSimulator %i\n'" % (jobTitle, year)

    cmdLine = ['identify', '-format', '%[fx:w]x%[fx:h]', localImgFile]
    dimensionString = subprocess.Popen(cmdLine, stdout=subprocess.PIPE).communicate()[0]
    dimensions = map(int, dimensionString.split("x"))

    if (dimensions[0] > dimensions[1]):
        widthMultiplier = 0.65
    else:
        widthMultiplier = 0.95

    options = [
        ("-background", "none"),
        ("-fill", "white"),
        ("-stroke", "gray"),
        ("-strokewidth", "3"),
        ("-kerning", "-5"),
        ("-font", "./helvetica-ultra-compressed.ttf"),
        ("-pointsize", "300"),
        ("-gravity", align),
        ("-interline-spacing", "75"),
        ("label:%s" % jobTitle, ""),
        ("-shear", "10x0"),
        ("-trim", ""),
        ("-resize", "%ix%i" % (dimensions[0] * widthMultiplier, dimensions[1] * .95)),
        (localImgFile, "+swap"),
    ]
    options.append(("-gravity", grav))
    
    offset = "+%i+%i" % (cap(dimensions[0] * .05, 20), cap(dimensions[1] * .05, 20))

    options.append(("-geometry", offset))
    options.append(("-composite", ""))

    exeLine = "convert %s %s" % (''.join('%s %s ' % o for o in options), "output.png")
    os.system(exeLine)
    os.system("rm %s" % (localImgFile))

def tweet(job, year):
    if (os.path.exists("output.png")):
        consumer_key = creds.get("twitter", "consumerkey")
        consumer_secret = creds.get("twitter", "consumersecret")
        access_token = creds.get("twitter", "accesstoken")
        access_token_secret = creds.get("twitter", "accesstokensecret")
        api = twitter.Api(consumer_key, consumer_secret, access_token, access_token_secret)
        api.PostMedia("%s Simulator %i" % (job, year), "output.png")
        # os.remove("output.png")
    else:
        pass # do nothing; something's wrong. 

random.seed()
job = getJobTitle()
image = getImageFor(job)
year = random.randint(2007, datetime.date.today().year)
createBoxArt(job, image, year)
tweet(job, year)
