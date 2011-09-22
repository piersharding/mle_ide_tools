"""
This program is a tool for transforming the IDE CSV file
format into the multiple CSV upload formats that Mahara
uses for user and group management.

SYNOPSIS:

execute import:

  python mahara_ide_to_csv.py --help

  python mahara_ide_to_csv.py --file=ide.csv -u -g



It provides options for user account records, and automatic
updating of groups based on the mlepRole and mlepGroupMembership
fields in the IDE CSV format.

The IDE (Identity Data Extract) is a CSV file format that SMS vendors in 
New Zealand generate to describe users for synchronisation to the school
user directory.  This program extends the usefulness of this export format
for the purpose of automatic provisioning of Mahara ePortfolio accounts.

Further information can be found at http://www.iam.school.nz/ and the original 
user directory initiative is at: https://gitorious.org/pla-udi/pages/Home

Details on Mahara Web Services can be found at:
https://gitorious.org/mahara-contrib/artefact-webservice

Copyright (C) Piers Harding 2011 and beyond, All rights reserved

mahara_ide_to_csv.py is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

"""

from __future__ import print_function
import os, sys, re, time, random
import ide
import csv
from optparse import OptionParser, SUPPRESS_HELP
import logging

def get_csv_file(ide_file):
    return ide.csvfile.read(ide_file)

def output_csv_file(filename, data):
    with open(filename, 'wb') as f:
        writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerows(data)

USERS_FILE = 'mahara-users.csv'
GROUPS_FILE = 'mahara-groups.csv'
GROUPS_MEMBERS_FILE = 'mahara-groups-members.csv'

USER_FIELDS = [
    'username',
    'remoteuser',
    'password',
    'email',
    'firstname',
    'lastname',
    'preferredname',
    'studentid',
    'introduction',
    'officialwebsite',
    'personalwebsite',
    'blogaddress',
    'address',
    'town',
    'city',
    'country',
    'homenumber',
    'businessnumber',
    'mobilenumber',
    'faxnumber',
    'icqnumber',
    'msnnumber',
    'aimscreenname',
    'yahoochat',
    'skypeusername',
    'jabberusername',
    'occupation',
    'industry']

CSV_FIELDS = [
    'mlepUsername',
    'mlepSmsPersonId',
    'password',
    'mlepEmail',
    'mlepFirstName',
    'mlepLastName',
    'preferredname',
    'mlepSmsPersonId',
    'introduction',
    'officialwebsite',
    'personalwebsite',
    'blogaddress',
    'address',
    'town',
    'city',
    'country',
    'homenumber',
    'businessnumber',
    'mobilenumber',
    'faxnumber',
    'icqnumber',
    'msnnumber',
    'aimscreenname',
    'yahoochat',
    'skypeusername',
    'jabberusername',
    'occupation',
    'industry']

FIELD_MAP = dict(zip(USER_FIELDS, CSV_FIELDS))

def main():

    # setup logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')

    # setup command line args
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="ide_file", default='ide.csv', type="string",
                          help="The Identity Data Extract CSV file for input.           Fields supported are:\n" + ", ".join(CSV_FIELDS), metavar="IDE_FILE")
    parser.add_option("-u", "--users", dest="users", action="store_true", default=False,
                          help="Process users", metavar="USUERS")
    parser.add_option("-n", "--domain", dest="school_domain", default='', type="string",
                          help="The registered domain name of the school, typically used for email addresses, and/or Google Apps - hogwarts.school.nz", metavar="SCHOOL_DOMAIN")
    parser.add_option("-p", "--password", dest="password", default=False, type="string",
                          help="A default password for all new accounts", metavar="PASSWORD")
    parser.add_option("-z", "--genpassword", dest="genpassword", action="store_true", default=False,
                          help="Generate new passwords", metavar="GENPASSWORD")
    parser.add_option("-g", "--groups", dest="groups", action="store_true", default=False,
                          help="Process groups", metavar="GROUPS")
    parser.add_option("-a", "--admin", dest="admin", default=False, type="string",
                          help="The default admin user for all groups", metavar="ADMIN")
    (options, args) = parser.parse_args()

    # load the csv file
    logging.info("CSV file to process: " + str(options.ide_file))
    logging.info("options are: " + str(options))
    if not options.school_domain:
        logging.error("You must specify the school domain.")
        sys.exit(1)

    if not options.admin:
        logging.error("You must specify the group default admin.")
        sys.exit(1)

    if not os.path.isfile(options.ide_file):
        logging.error("CSV file not found: " + str(options.ide_file))
        sys.exit(1)
    sms_users = get_csv_file(options.ide_file)

    if not sms_users or len(sms_users) == 0:
        logging.info('CSV file is empty')
        sys.exit(0)

    # get a dictionary baked on the internal remote user for this institution context
    csv_attrs = dict(zip(sms_users[0].keys(), sms_users[0].keys()))

    # add on password field
    if (options.genpassword or options.password) and not 'password' in csv_attrs:
        csv_attrs['password'] = 1

    # determine the basic user fields for adding on
    user_cols = [field for field in USER_FIELDS if FIELD_MAP[field] in csv_attrs]

    # loop through user records and accumulate users, and groups
    groups = {}
    users = [user_cols]
    for user in sms_users:
        # construct the username
        user['mlepUsername'] = user['mlepSmsPersonId'] + '@' + options.school_domain
        # process groups for this user
        user_groups = []
        if 'mlepGroupMembership' in user and len(user['mlepGroupMembership']) > 0:
            user_groups = [g.replace(' ', '_') for g in user['mlepGroupMembership'].split('#')]
        if 'mlepRole' in user and len(user['mlepRole']) > 0:
            user_groups.append(user['mlepRole'])
        if 'mlepRole' in user and re.match('Teach', user['mlepRole']):
            role = 'tutor'
        else:
            role = 'member'
        for group in user_groups:
            if not group in groups:
                groups[group] = {}
            groups[group][user['mlepUsername']] = role
        # password is given, defaulted or generated
        if options.genpassword:
            user['password'] = 'pass' + str(random.random()) + str(int(time.time()))
        elif options.password:
            user['password'] = options.password
        # map only the fields given for the target CSV format
        users.append([user[FIELD_MAP[field]] for field in user_cols])

    logging.info("user records: " + str(len(users) - 1))

    if options.users:
        logging.info("outputing user file")
        output_csv_file(USERS_FILE, users)

    # now create the group file structures
    csv_groups = [['shortname', 'displayname', 'description', 'roles', 'request']]
    csv_group_members = [['shortname', 'username', 'role']]
    for (group, members) in groups.iteritems():
        csv_groups.append([group, group, group, 'course', 1])
        csv_group_members.append([group, options.admin, 'admin'])
        for (user, role) in members.iteritems():
            csv_group_members.append([group, user, role])
    
    logging.info("group records: " + str(len(csv_groups) - 1))
    logging.info("group member records: " + str(len(csv_group_members) - 1))

    if options.groups:
        logging.info("outputing group files")
        output_csv_file(GROUPS_FILE, csv_groups)
        output_csv_file(GROUPS_MEMBERS_FILE, csv_group_members)

    logging.info("finished")
    sys.exit(0)

# ------ Good Ol' main ------
if __name__ == "__main__":
    main()
