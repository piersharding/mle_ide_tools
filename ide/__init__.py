
"""
Python utils for importing IDE CSV format files
"""

import sys
if sys.version < '2.5':
    print 'Wrong Python Version (must be >=2.5) !!!'
    sys.exit(1)

# load the native extensions
import csv
import re
import logging

class CSVException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class csvfile(object):
    """
    Base class used to trigger everything off
    """

    @classmethod
    def read(cls, ide_file):
        csv_file = []

        # preprocess the file to remove blank lines and comments
        f = open(ide_file, 'rb')
        lines = []
        for line in f.readlines():
            # eliminate blank lines
            if re.match('^$', line):
                continue
            # eliminate comment lines
            if re.match('^#', line):
                continue
            # eliminate the timestamp line
            if re.match('^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$', line):
                logging.info("found timestamp: " + str(line))
                continue
            lines.append(line.strip())
    
        # setup the csv processor
        ideReader = csv.reader(lines, delimiter=',', quotechar='"')
    
        # get header row
        fields = ideReader.next() 
    
        # process each csv record into a hash
        for row in ideReader:
            items = zip(fields, row)
            item = {}
            for (name, value) in items:
                item[name] = value.strip()
            csv_file.append(item)
            #print(item)
        
        return csv_file

