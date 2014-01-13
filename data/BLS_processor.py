import os
import sys
from collections import OrderedDict

with open("bls_rawlist.txt", "r") as jobFile:
    rawJobs = map(str.rstrip, jobFile.readlines())
    rawJobsUnique = OrderedDict.fromkeys(rawJobs).keys()

def analyze():
    commacount = 0
    flscount = 0
    inccount = 0
    for job in rawJobsUnique:
        if ", " in job:
            commacount += 1
        if "First-Line Supervisors" in job:
            flscount += 1
        if "Including" in job:
            inccount += 1

    print "%i jobs with commas." % (commacount)
    print "%i jobs with fls." % (flscount)
    print "%i jobs with including." % (inccount)

def findInList(needle, haystack):
    count = 0
    for searchString in haystack:
        if needle in searchString:
            return count
        count += 1
    return None

jobs = []
lastMods = {}
for job in rawJobsUnique:
    # split on commas
    jobSplit = map(str.strip, job.split(","))
    if len(jobSplit) == 1:
        jobs.append(job)
        continue

    # <sigh> there are typos in this list
    jobSplit = filter(lambda x: len(x) > 0, jobSplit)

    # if any elements have "except", remove them and everything after
    index = findInList("Except", jobSplit)
    if index != None:
        jobSplit = jobSplit[:index]

    # if last element is "all other" or "first-line supervisor", discard
    if jobSplit[-1] == "All Other":
        jobSplit.pop(-1)
    if jobSplit[-1] == "First-Line Supervisors":
        jobSplit.pop(-1)

    # if last element starts with "and" -- break into separate jobs
    if jobSplit[-1].startswith("and "):
        jobSplit[-1] = jobSplit[-1][len("and "):]
        for j in jobSplit:
            jobs.append(j)
        continue

    # if last element is modifier that doesn't make sense to invert, drop it
    for badmod in ["Hand", "Miscellaneous", "Other", "General", ]:
        if jobSplit[-1] == badmod:
            jobSplit.pop(-1)

    modifiers = []
    # if any element contains "including" -- break into separate jobs
    index = findInList("Including", jobSplit)
    if index != None:
        modifiers = jobSplit[index:]
        modifiers[0] = modifiers[0][len("Including "):]
        jobSplit = jobSplit[:index]

    # invert remainder
    if (len(jobSplit) <= 2):
        if len(modifiers) > 0:
            for mod in modifiers:
                jobs.append("%s (%s)" % (' '.join(jobSplit), mod))
        else:
            jobs.append(' '.join(jobSplit))
        continue

    # special cases
    if (jobSplit[-1] == "Postsecondary"):
        jobSplit.pop(-1)
        if (jobSplit[-1].endswith("Teachers") and jobSplit[-1].startswith("and ")):
            jobSplit[-1] = jobSplit[-1][:-len(" Teachers")]
            jobSplit.insert(0, "Teachers")

        jobTitle = jobSplit[0]
        jobSplit.pop(0)
        jobString = "%s %s %s" % (
            "Postsecondary",
            ' '.join(jobSplit),
            "Teachers",
        )

        jobs.append(jobString)
        continue

    materials = ("Metal and Plastic", "Synthetic and Glass Fibers", "Wood")
    matIndex = findInList(jobSplit[-1], materials)
    if (matIndex != None):
        material = materials[matIndex]
        setIndex = findInList("Setters", jobSplit)
        opIndex = findInList("Operators", jobSplit)
        tendIndex = findInList("and Tenders", jobSplit)
        if (setIndex != None and opIndex != None and tendIndex != None):
            jobSplit[setIndex] = jobSplit[setIndex][:-len(" Setters")]
            jobSplit.pop(tendIndex)
            jobSplit.pop(opIndex)

            # oddball
            remainingSetIndex = findInList("Setters", jobSplit)
            if remainingSetIndex != None:
                jobSplit[remainingSetIndex] = jobSplit[remainingSetIndex][:-len(" Setters")]
            jobSplit = filter(lambda x: len(x) > 0, jobSplit)

            jobSplit.pop(-1)
            for jobTitle in ("Setters", "Operators", "Tenders"):
                jobString = "%s %s %s" % (
                    material,
                    ', '.join(jobSplit),
                    jobTitle
                )
                jobs.append(jobString)
            continue

        jobSplit.pop(-1)
        jobSplit.insert(0, jobSplit.pop(-1))
        jobSplit.insert(0, material)
        jobString = ' '.join(jobSplit)
        jobs.append(jobString)
        continue

    if (jobSplit[0] == "Operators"):
        jobSplit.pop(0)
        jobSplit.insert(0, jobSplit.pop(-1))
        jobSplit.append("Operators")
        jobString = ' '.join(jobSplit)
        jobs.append(jobString)
        continue

    if (jobSplit[0] == "Repairers"):
        jobSplit.pop(0)
        if jobSplit[0] == "Electronic Equipment":
            jobSplit.insert(1, "for")
        jobSplit.append("Repairers")
        jobString = ' '.join(jobSplit)
        jobs.append(jobString)
        continue

    if (jobSplit[0] == "Installers"):
        jobSplit.pop(0)
        if jobSplit[0] == "Electronic Equipment":
            jobSplit.insert(1, "for")
        jobSplit.append("Installers")
        jobString = ' '.join(jobSplit)
        jobs.append(jobString)
        continue

    if (jobSplit[0] == "Teachers"):
        jobSplit.pop(0)
        if (jobSplit[0] == "Career/Technical Education" or 
            jobSplit[0] == "Special Education"):
            jobSplit.insert(0, jobSplit.pop(-1))
        jobSplit.append("Teachers")
        jobString = ' '.join(jobSplit)
        jobs.append(jobString)
        continue

    if (jobSplit[0] == "Drivers"):
        jobSplit.pop(0)
        jobSplit.insert(0, jobSplit.pop(1))
        jobSplit.append("Drivers")
        jobString = ' '.join(jobSplit)
        jobs.append(jobString)
        continue


    if (jobSplit[-1].startswith("and ")):
        print jobSplit
        titles = []
        modifiers = []
        lastTitle = jobSplit[-1].split()[-1]
        jobSplit[-1] = ' '.join(jobSplit[-1].split()[:-1])
        # print lastTitle, jobSplit
        # print jobSplit
        # titles.append(lastTitle)
        # modifiers.append(jobSplit[-1][len("and "):].split()[0])
        # print modifiers, jobSplit

    # print jobSplit
    if (jobSplit[0] not in lastMods):
        lastMods[jobSplit[0]] = 0
    lastMods[jobSplit[0]] += 1


# import pprint
# pprint.pprint(lastMods)

## invert
# Accountants, Certified Public

## split out
# Actors, Producers, and Directors

## remove post except
# Administrative Assistants, Except Legal, Medical, and Executive

## remove All Other
# Administrative Support Workers, All Other

## remove FLS
# Administrative Support Workers, First-Line Supervisors

## just to make sure this double-and doesn't trip us up
# Agents and Business Managers of Artists, Performers, and Athletes

## remove except, THEN invert
# Agents, Purchasing, Except Wholesale, Retail, and Farm Products

## separate categories?
# Artists, Fine, Including Painters, Sculptors, and Illustrators

## wtf why -- ah, simple invert
# Boring Machine Tool Operators, Metal and Plastic
# Buffing Machine Tool Operators, Metal and Plastic
# Buffing Machine Tool Setters, Metal and Plastic
# Buffing Machine Tool Tenders, Metal and Plastic

### got down to Digitizers, Apparel Embroidery


# Handlers, Pesticide, Vegetation
# Drivers, Bus, Intercity
# Drivers, Bus, School or Special Client
# Drivers, Bus, Transit

# Repairers, Electronics, Powerhouse

# Representatives, Sales, Wholesale and Manufacturing, Except Technical and Scientific Products
# Representatives, Sales, Wholesale and Manufacturing, Technical and Scientific Products
