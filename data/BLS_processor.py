import os
import sys
import re
from collections import OrderedDict

with open("bls_rawlist.txt", "r") as jobFile:
    rawJobs = map(str.rstrip, jobFile.readlines())
    rawJobsUnique = OrderedDict.fromkeys(rawJobs).keys()


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

    # <sigh> there are typos in this list
    jobSplit = filter(lambda x: len(x) > 0, jobSplit)

    # no commas! this one is easy
    if len(jobSplit) == 1:
        jobs.append(job)
        continue

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

    materials = (
        "Metal and Plastic", 
        "Synthetic and Glass Fibers", 
        "Wood", 
        "Plastics", 
        "Food and Tobacco"
    )
    matIndex = findInList(jobSplit[-1], materials)
    if (matIndex != None):
        jobSplit = map(lambda x: re.sub("Operator$", "Operators", x), jobSplit)
        material = materials[matIndex]
        setIndex = findInList("Setters", jobSplit)
        opIndex = findInList("Operators", jobSplit)
        tendIndex = findInList("and Tenders", jobSplit)
        if (opIndex != None and opIndex == tendIndex):
            jobSplit.insert(0, jobSplit.pop(-1))
            jobString = ', '.join(jobSplit)
            jobs.append(jobString)
            continue
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
        jobString = ', '.join(jobSplit)
        jobs.append(jobString)
        continue

    if jobSplit[0] == "Sales Representatives":
        jobSplit.pop(0)
        jobSplit.insert(0, "Sales")
        jobSplit.insert(0, "Representatives")

    if jobSplit[0] == "Representatives":
        selling = []
        if len(jobSplit) > 3:
            selling = jobSplit[3:]
            jobSplit = jobSplit[:3]
        jobSplit.reverse()
        if len(selling) > 0:
            jobSplit.append("for")
            jobSplit.append(' '.join(selling))
        jobString = ' '.join(jobSplit)
        jobs.append(jobString)
        continue

    # hmmm, this feels someone defending a very specific job...
    if jobSplit[-1].endswith("Enhanced Operators/Maintainers"):
        jobSplit[-1] = jobSplit[-1][:-len(" Enhanced Operators/Maintainers")]
        jobString = "%s for %s" % (
            "Enhanced Operators/Maintainers",
            ', '.join(jobSplit)
        )
        jobs.append(jobString)
        continue

    # if there's still an "and" in the last element, assume an Oxford comma was dropped
    #  and pick it up
    if " and " in jobSplit[-1]:
        last = jobSplit.pop(-1)
        jobSplit = jobSplit + map(str.strip, last.split(" and "))
        for j in jobSplit:
            jobs.append(j)
        continue

    # if there's an "and" in the penultimate slot, the last word is a modifier
    if jobSplit[-2].startswith("and "):
        mod = jobSplit.pop(-1)
        jobSplit[-1] = jobSplit[-1][len("and "):]
        firstSplit = jobSplit[0].split()
        if len(firstSplit) > 1:
            mod += " " + firstSplit[0]
            jobSplit[0] = ' '.join(firstSplit[1:])
        for j in jobSplit:
            jobString = "%s %s" % (mod, j)
            jobs.append(jobString)
        continue

    # finally down to some simple inversions
    jobSplit.reverse()
    jobString = ' '.join(jobSplit)
    jobs.append(jobString)


# unique-ify
jobs = list(set(jobs))
jobs.sort()

with open("bls_normalized.txt", "w") as normalizedFile:
    normalizedFile.write('\n'.join(jobs))
