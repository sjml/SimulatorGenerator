#!/usr/bin/env python

# built-ins
import os
import sys
import mimetypes
import datetime
import subprocess
import random
import tempfile

# site-packages
import requests

# global constants
BASE_PATH = os.path.dirname(os.path.abspath( __file__ ))

# local
sys.path.insert(0, os.path.join(BASE_PATH, "lib"))
import titlecase


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


def getImageFor(searchTerm, safeSearchLevel="moderate", referer=None):
    is_params = {
        "v" : "1.0", 
        "q" : searchTerm, 
        "imgType" : "photo",
        "imgsz" : "small|medium|large|xlarge|xxlarge|huge",
        "rsz": 8,
        "safe" : safeSearchLevel
    }
    is_headers = {}
    if referer:
        is_headers["Referer"] = referer
    is_URL = "https://ajax.googleapis.com/ajax/services/search/images"

    imageResults = requests.get(is_URL, params=is_params, headers=is_headers).json()

    if (imageResults == None or 'responseData' not in imageResults or imageResults['responseData'] == None):
        sys.stderr.write("No response data in image search for %s. JSON:\n%s\n" % (searchTerm, imageResults))
        return None

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
    # find the largest image
    # imageData.sort(reverse=True, key=lambda img: img['size'])
    # just pick a random one
    random.shuffle(imageData)

    mimetypes.init()
    for img in imageData:
        try:
            r = requests.head(img['url'])
            if not r.ok:
                # can't download for whatever reason
                continue
        except:
            # requests library puked
            continue

        try:
            extension = mimetypes.guess_extension(r.headers['Content-Type'])
        except KeyError, e:
            sys.stderr.write("Couldn't find content-type header: %s" % str(r.headers))
            extension = ""
        if (extension == ".jpe") : extension = ".jpg"

        localFileName = "base_image-%s%s" % (datetime.datetime.now().strftime("%Y-%m-%d-%H%M.%f"), extension)
        localFileName = os.path.join(tempfile.gettempdir(), localFileName)
        imgResponse = requests.get(img['url'])
        with open(localFileName, 'wb') as baseFile:
            baseFile.write(imgResponse.content)

        # check our work
        cmdLine = ['identify', '-format', '%wx%h', localFileName]
        dimensionString = subprocess.Popen(cmdLine, stdout=subprocess.PIPE).communicate()[0]
        dimensions = dimensionString.split("x")
        if (int(dimensions[0]) == img['w'] and int(dimensions[1]) == img['h']):
            return localFileName

    return None


def createBoxArt(jobTitle, year, inputFile, outputFile, maxSize=None, textPosition=None, deleteInputFile=False, log=False):
    if   textPosition == "TopRight": grav = "NorthEast"
    elif textPosition == "TopLeft": grav = "NorthWest"
    elif textPosition == "BottomRight": grav = "SouthEast"
    elif textPosition == "BottomLeft": grav = "SouthWest"
    else: 
        grav = random.choice(("NorthWest", "NorthEast", "SouthWest", "SouthEast"))

    if grav[-4:] == "West":
        align = "West"
    else:
        align = "East"

    jobTitle = titlecase.titlecase(jobTitle)
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

    # newlines to deal with the font overruning its rendering bounds; 
    #   we trim the canvas in imagemagick anyway
    jobTitle = "\n%sSimulator %i\n" % (jobTitle, year)

    cmdLine = ['identify', '-format', '%wx%h', inputFile]
    try:
        dimensionString = subprocess.Popen(cmdLine, stdout=subprocess.PIPE).communicate()[0]
    except TypeError, e:
        sys.stderr.write("Couldn't get dimensions for %s\n" % inputFile)
        return None
    dimensions = map(int, dimensionString.split("x"))

    if (dimensions[0] > dimensions[1]):
        widthMultiplier = 0.65
    else:
        widthMultiplier = 0.95

    offset = "+%i+%i" % (cap(dimensions[0] * .05, 20), cap(dimensions[1] * .05, 20))
    command = [
        "convert",

        # generate large text that we'll scale down to fit the target image later
        "-background", "none", 
        "-fill", "white",
        "-stroke", "gray",
        "-strokewidth", "3",
        "-kerning", "-5",
        "-font", "./data/helvetica-ultra-compressed.ttf",
        "-pointsize", "300",
        "-gravity", align,
        "-interline-spacing", "75",
        ("label:%s" % jobTitle).encode("utf8"),
        "-shear", "10x0", # since this font doesn't have true oblique / italics
        "-trim", # remove the extra space added by the newline wrapping

        # bring its size down so it can be overlaid into the base image
        "-resize", "%ix%i" % (dimensions[0] * widthMultiplier, dimensions[1] * .95),

        inputFile, "+swap", # take everything we just created and make it
                            #  the thing that we're overlaying. inputFile
                            #  becomes the target
        "-gravity", grav,
        "-geometry", offset,
        "-composite",
        outputFile
    ]

    if maxSize:
        command.insert(-1, "-resize")
        command.insert(-1, "%sx%s>" % maxSize)

    if (log):
        print("ImageMagick command: %s" % " ".join(command))
    subprocess.call(command)

    if (deleteInputFile):
        print "Deleting", inputFile
        os.remove(inputFile)
    
    return outputFile



if __name__ == '__main__':
    random.seed()

    import argparse

    description = """This program makes super rad box art for video games in the 
    exciting job simulation genre. Note that you must install ImageMagick 
    (http://www.imagemagick.org/) and the Python Requests library 
    (http://docs.python-requests.org/en/latest/) for this to work properly."""

    parser = argparse.ArgumentParser(
        description=description, 
        add_help=False
    )

    parser.add_argument("simulatorSubject", help="The topic for which you want to make simulator box art.")
    parser.add_argument("-i", "--input-file", help="The image file to use for the box art. If not specified, we'll do a Google Image Search for the subject.")
    parser.add_argument("-o", "--output-file", help="Path to the image file to store the box art. (defaults: an image named \"boxart-[timestamp].png\" in the current directory)")
    parser.add_argument("-w", "--max-width", help="Maximum width for the ouput image. Output images will be resized if they're wider than this.", type=int)
    parser.add_argument("-h", "--max-height", help="Maximum height for the ouput image. Output images will be resized if they're taller than this.", type=int)
    parser.add_argument("-p", "--text-position", help="Where the text should go on the image. Will pick randomly if not specified.", type=str, choices=["TopRight", "TopLeft", "BottomRight", "BottomLeft"])
    parser.add_argument("-s", "--safe-search", help="The type of SafeSearch to use for Google Image Search. (default: %(default)s)", type=str, choices=["active", "moderate", "off"], default="moderate")
    parser.add_argument("-y", "--year", help="The year to put in the box art. (default: random year)", type=int)
    parser.add_argument("-b", "--min-year", help="The lowest year that will get randomly chosen. (default: %(default)s)", type=int, default=2007)
    parser.add_argument("-t", "--max-year", help="The highest year that will get randomly chosen. (default: current year)", type=int, default=datetime.date.today().year)
    parser.add_argument("-d", "--debug", help="Enables debug output. (default: off)", action="store_true")
    parser.add_argument("--help", action="help", help="show this help message and exit")

    args = parser.parse_args()

    img = args.input_file
    if not img:
        img = getImageFor(args.simulatorSubject)
    output = args.output_file
    if not output:
        output = "boxart-%s.png" % datetime.datetime.now().strftime("%Y-%m-%d-%H%M.%f")
    year = args.year
    if not year:
        year = random.randint(args.min_year, args.max_year)

    if (args.max_width or args.max_height):
        w = str(args.max_width) if args.max_width else "" 
        h = str(args.max_height) if args.max_height else "" 
        max_size = (w, h)
    else:
        max_size = None


    createBoxArt(
        titlecase.titlecase(args.simulatorSubject),
        year,
        img,
        output,
        maxSize=max_size,
        textPosition=args.text_position,
        deleteInputFile=(args.input_file == None), # no input; working from Google Image Search; delete temp file
        log=args.debug
    )



