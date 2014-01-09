import os
import random
import datetime
import subprocess

jobTitle = "Very Long Impressive Job Title"
localImgFile = "tmp/long_image_sample.jpg"
outputFile = "output-%s.png" % (datetime.datetime.now().strftime("%Y-%m-%d-%H%M"))

def main():

    cmdLine = ['identify', '-format', '%[fx:w]x%[fx:h]', localImgFile]
    dimensionString = subprocess.Popen(cmdLine, stdout=subprocess.PIPE).communicate()[0]
    dimensions = dimensionString.split("x")
    
    options = [
        ("-size", dimensionString),
        ("xc:none", ""),
        ("-font", "./helvetica-ultra-compressed.ttf"),
        ("-pointsize", "100"),
        ("-fill", "black"),
        ("-interline-spacing", "15"),
        ("-stroke", "gray",),
        ("-gravity", "SouthEast"),
        ("-annotate", "0x10+30+30 \"Even Longer Impressive Job Title\\n2014\"")
    ]
    exeLine = "convert %s %s" % (''.join('%s %s ' % o for o in options), outputFile)
    print exeLine
    os.system(exeLine)
    return

    options = [
        ("-size", "%w%h"),
        ("-font", "./helvetica-ultra-compressed.ttf"),
        ("-pointsize", "100"),
        ("-fill", "white"),
        ("-interline-spacing", "15"),
        ("-stroke", "gray",),
    ]
    grav = random.choice(("NorthWest", "NorthEast", "SouthWest", "SouthEast"))
    options.append(("-gravity", grav))

    if (grav == "NorthWest"):
        offset = "+40+20"
    elif (grav == "SouthWest"):
        offset = "+10+30"
    elif (grav == "SouthEast"):
        offset = "+30+30"
    else: # NorthEast
        offset = "+10+10"

    options.append( ("-annotate", "0x10%s \"%s\\nSimulator 2014\"" % (offset, jobTitle)) )

    exeLine = "convert %s %s %s" % (localImgFile, ''.join('%s %s ' % o for o in options), outputFile)
    print(exeLine)
    os.system(exeLine)

if __name__ == '__main__':
    main()