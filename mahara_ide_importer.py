"""
This program is a tool for synchronising SMS IDE export format accounts
with Mahara via the Web Services interface.

SYNOPSIS:

execute import:

  python mahara_ide_importer.py --help

  python mahara_ide_importer.py --file=ide.csv --maharaurl=http://mahara.hogwarts.school.nz --consumerkey=<consumer key> --consumersecret=<consumer secret> --domain=hogwarts.school.nz -c -u -d -g



It provides options for create/update/delete of user accounts, and 
automatic updating of groups based on the mlepRole and mlepGroupMembership
fields in the CSV format.

The IDE (Identity Data Extract) is a CSV file format that SMS vendors in 
New Zealand generate to describe users for synchronisation to the school
user directory.  This program extends the usefulness of this export format
for the purpose of automatic provisioning of Mahara ePortfolio accounts.

Further information can be found at http://www.iam.school.nz/ and the original 
user directory initiative is at: https://gitorious.org/pla-udi/pages/Home

Details on Mahara Web Services can be found at:
https://gitorious.org/mahara-contrib/artefact-webservice

Copyright (C) Piers Harding 2011 and beyond, All rights reserved

mahara_ide_importer.py is free software; you can redistribute it and/or
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
import oauth2 as oauth
import urllib, cgi
import json
import ide
from optparse import OptionParser, SUPPRESS_HELP
import logging

DEFAULT_AUTH = 'internal'
TOKEN_DIR = 'oauth_token'
TOKEN_FILE = TOKEN_DIR + '/mahara.oauth'
if not os.path.isdir(TOKEN_DIR):
    os.mkdir(TOKEN_DIR)


def write_token_file(filename, oauth_token, oauth_token_secret):
    """
    Write a token file to hold the oauth token and oauth token secret.
    """
    oauth_file = open(filename, 'w')
    print(oauth_token, file=oauth_file)
    print(oauth_token_secret, file=oauth_file)
    oauth_file.close()

def read_token_file(filename):
    """
    Read a token file and return the oauth token and oauth token secret.
    """
    if not os.path.isfile(filename):
        return False, False

    f = open(filename)
    return f.readline().strip(), f.readline().strip()


class MaharaProxy:
    def __init__(self, options):
        self.options = options
        self.consumer = oauth.Consumer(key=self.options.consumer_key, secret=self.options.consumer_secret)
        oauth_token, oauth_token_secret = read_token_file(TOKEN_FILE)
        self.oauth_token = oauth_token
        self.oauth_token_secret = oauth_token_secret

    def is_authorised(self):
        return self.oauth_token

    def authorise(self):
        if not self.is_authorised():
            #oauth_callback=oob
            request_token_url = self.options.mahara_url + "/artefact/webservice/oauthv1.php/request_token"
            client = oauth.Client(self.consumer)
    
            response, content = client.request(request_token_url, 'POST', urllib.urlencode({'oauth_callback':'oob'}))
            parsed_content = dict(cgi.parse_qsl(content))
            print(parsed_content)
            request_token = oauth.Token(parsed_content['oauth_token'], parsed_content['oauth_token_secret'])

            # ask the user to authorize this application
            print('Authorize this application at: %s?oauth_token=%s' % (self.options.mahara_url + '/artefact/webservice/oauthv1.php/authorize', parsed_content['oauth_token']))
            oauth_verifier = raw_input('Enter the PIN / OAuth verifier: ').strip()
            # associate the verifier with the request token
            request_token.set_verifier(oauth_verifier)
            
            # upgrade the request token to an access token
            client = oauth.Client(self.consumer, request_token)
            response, content = client.request(self.options.mahara_url + '/artefact/webservice/oauthv1.php/access_token', 'POST')
            parsed_content = dict(cgi.parse_qsl(content))
            print(parsed_content)
            write_token_file(TOKEN_FILE, parsed_content['oauth_token'], parsed_content['oauth_token_secret'])
            self.oauth_token, self.oauth_token_secret = parsed_content['oauth_token'], parsed_content['oauth_token_secret']

    def call_mahara(self, content):
        # make an authenticated API call
        access_token = oauth.Token(self.oauth_token, self.oauth_token_secret)
        print(access_token)

        client = oauth.Client(self.consumer, access_token)
        response = client.request(self.options.mahara_url + '/artefact/webservice/rest/server.php?alt=json', method='POST', body=json.dumps(content), headers={'Content-Type': 'application/jsonrequest'})
        response = json.loads(response[1])
        if response and 'exception' in response and response['exception'] == 'OAuthException2':
            print("There was an OAuth authentication problem - try removing " + TOKEN_DIR + " dir", response)
            logging.error("There was an OAuth authentication problem - try removing " + TOKEN_DIR + " dir")
            sys.exit(1)

        return response


def get_csv_file(ide_file):
    return ide.csvfile.read(ide_file)


def filter_by_remote_user(existing_users):
    result = {}
    for user in existing_users:
        auth = [a['remoteuser'].lower() for a in user['auths'] if a['auth'] == DEFAULT_AUTH]
        if auth:
            result[auth.pop()] = user
    return result


def main():

    # setup logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')

    # setup command line args
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="ide_file", default='ide.csv', type="string",
                          help="The Identity Data Extract CSV file for input", metavar="IDE_FILE")
    parser.add_option("-c", "--create", dest="create", action="store_true", default=False,
                          help="Process creates", metavar="CREATES")
    parser.add_option("-u", "--update", dest="update", action="store_true", default=False,
                          help="Process updates", metavar="UPDATES")
    parser.add_option("-d", "--delete", dest="delete", action="store_true", default=False,
                          help="Process deletes", metavar="DELETES")
    parser.add_option("-k", "--consumerkey", dest="consumer_key", default='', type="string",
                          help="The OAuth Consumer Key for Mahara", metavar="CONSUMER_KEY")
    parser.add_option("-n", "--domain", dest="school_domain", default='', type="string",
                          help="The registered domain name of the school, typically used for email addresses, and/or Google Apps - hogwarts.school.nz", metavar="SCHOOL_DOMAIN")
    parser.add_option("-p", "--password", dest="password", default=False, type="string",
                          help="A default password for all new accounts", metavar="PASSWORD")
    parser.add_option("-s", "--consumersecret", dest="consumer_secret", default='', type="string",
                          help="The OAuth Consumer Secret for Mahara", metavar="CONSUMER_SECRET")
    parser.add_option("-m", "--maharaurl", dest="mahara_url", default='http://mahara.local.net/maharadev', type="string",
                          help="The base URL for Mahara - http://mahara.hogwarts.school.nz", metavar="MAHARA_URL")
    parser.add_option("-g", "--groups", dest="groups", action="store_true", default=False,
                          help="Process groups", metavar="GROUPS")
    (options, args) = parser.parse_args()

    # load the csv file
    logging.info("CSV file to process: " + str(options.ide_file))
    logging.info("options are: " + str(options))
    if not options.school_domain:
        logging.error("You must specify the school domain.")
        sys.exit(1)

    if not os.path.isfile(options.ide_file):
        logging.error("CSV file not found: " + str(options.ide_file))
        sys.exit(1)
    sms_users = get_csv_file(options.ide_file)


    # authenticate against Mahara
    mp = MaharaProxy(options)
    mp.authorise()

    # determine the connected users context
    parameters = {"wsfunction":"mahara_user_get_context"}
    current_context = mp.call_mahara(parameters)
    logging.info("The institution context: " + current_context)

    # process csv file:
    #     - determine existing users
    parameters = {"wsfunction":"mahara_user_get_users"}
    existing_users = mp.call_mahara(parameters)

    # remember all the usernames that are known in this institution
    usernames = set([user['username'].lower() for user in existing_users])

    # get a dictionary baked on the internal remote user for this institution context
    existing_users = filter_by_remote_user(existing_users)
    logging.debug('existing users: ' + repr(existing_users.keys()))
    sms_users = dict(zip([v['mlepSmsPersonId'].lower() for v in sms_users], sms_users))

    # compare the sets of user keys
    create_users = list(set(sms_users.keys()).difference(set(existing_users.keys())))
    update_users = list(set(sms_users.keys()).intersection(set(existing_users.keys())))
    delete_users = list(set(existing_users.keys()).difference(set(sms_users.keys())))
    logging.info("New users to process: " + str(len(create_users)))
    logging.info("Update users to process: " + str(len(update_users)))
    logging.info("Delete users to process: " + str(len(delete_users)))
    logging.debug("create users: " + repr(create_users))
    logging.debug("update users: " + repr(update_users))
    logging.debug("delete users: " + repr(delete_users))

    # process create users
    new_users = []
    all_users = {} # need to collect all real user names
    for user in create_users:
        user = sms_users[user]
        username = user['mlepSmsPersonId'] + '@' + options.school_domain
        if username.lower() in usernames:
            logging.error("cannot create user - username already exists: " + username)
            sys.exit(1)
        all_users[user['mlepSmsPersonId'].lower()] = username # save new usernames
        if 'password' in user:
            new_password = user['password']
        elif options.password:
            new_password = options.password
        else:
            new_password = 'pass' + str(random.random()) + str(int(time.time()))
        new_users.append(
                        { 'username': username,
                          'password': new_password,
                          'firstname': user['mlepFirstName'],
                          'lastname': user['mlepLastName'],
                          'email': user['mlepEmail'],
                          'auth': DEFAULT_AUTH,
                          'institution': current_context,
                          'studentid': user['mlepSmsPersonId'],
                          'preferredname': user['mlepFirstName'] + ' ' + user['mlepLastName'],
                          'remoteuser': user['mlepSmsPersonId'],
                        })

    if options.create and new_users:
        parameters = {"wsfunction":"mahara_user_create_users", "users": new_users}
        result = mp.call_mahara(parameters)
        logging.debug('Create users response: ' + repr(result))
    else:
        logging.info('create users skipped')

    # process update users
    change_users = []
    for user in update_users:
        current = existing_users[user]
        all_users[user] = current['username'] # save old usernames
        user = sms_users[user]
        update = {}
        user = { 'username': current['username'],
                 'firstname': user['mlepFirstName'],
                 'firstname': user['mlepFirstName'],
                 'lastname': user['mlepLastName'],
                 'email': user['mlepEmail'],
                 'auth': DEFAULT_AUTH,
                 'institution': current_context,
                 'studentid': user['mlepSmsPersonId'],
                 'preferredname': user['mlepFirstName'] + ' ' + user['mlepLastName']}
        for k in user.keys():
            if current[k] != user[k]:
                update[k] = user[k]
        if update:
            update['username'] = user['username']
            change_users.append(update)

    if options.update and change_users:
        parameters = {"wsfunction":"mahara_user_update_users", "users": change_users}
        result = mp.call_mahara(parameters)
        logging.debug('Update users response: ' + repr(result))
    else:
        logging.info('update users skipped')

    # process delete users
    remove_users = []
    for user in delete_users:
        user = existing_users[user]
        remove_users.append({'username': user['username']})

    if options.delete and remove_users:
        parameters = {"wsfunction":"mahara_user_delete_users", "users": remove_users}
        result = mp.call_mahara(parameters)
        logging.debug('Delete users response: ' + repr(result))
    else:
        logging.info('delete users skipped')

    # - determine existing groups
    parameters = {"wsfunction":"mahara_group_get_groups"}
    existing_groups = mp.call_mahara(parameters)
    existing_groups = dict(zip([v['shortname'] for v in existing_groups], existing_groups))
    logging.debug('Existing groups: ' + repr(existing_groups.keys()))

    # find groups in SMS import - record users against groups
    groups = {}
    for user in all_users.keys():
        attrs = sms_users[user]
        user_groups = []
        if 'mlepGroupMembership' in attrs and len(attrs['mlepGroupMembership']) > 0:
            user_groups = [g.replace(' ', '_') for g in attrs['mlepGroupMembership'].split('#')]
        if 'mlepRole' in attrs and len(attrs['mlepRole']) > 0:
            user_groups.append(attrs['mlepRole'])
        for group in user_groups:
            if not group in groups:
                groups[group] = []
            groups[group].append(user)

    # calculate group change sets
    create_groups = list(set(groups.keys()).difference(set(existing_groups.keys())))
    update_groups = list(set(groups.keys()).intersection(set(existing_groups.keys())))
    delete_groups = list(set(existing_groups.keys()).difference(set(groups.keys())))
    logging.info("New groups to process: " + str(len(create_groups)))
    logging.info("Update groups to process: " + str(len(update_groups)))
    logging.info("Delete groups to process: " + str(len(delete_groups)))


    # calculate group deletes
    group_deletes = []
    for group in delete_groups:
        group = existing_groups[group]
        group_deletes.append({'shortname': group['shortname'], 'institution': group['institution']})

    # calculate group updates
    group_creates = []
    for group in create_groups:
        group_members = groups[group]
        # do the members
        members = []
        for user in group_members:
            account = sms_users[user]
            # teachers are 'tutor' students are members
            if 'mlepRole' in account and re.match('Teacher', account['mlepRole']):
                role = 'tutor'
            else:
                role = 'member'
            members.append({'username': all_users[user], 'role': role})
        group_creates.append({'shortname': group, 'institution': current_context, 'name': group, 'description': group, 'grouptype': 'course', 'request': 1, 'members': members})

    # calculate group updates
    group_updates = []
    for group in update_groups:
        group = existing_groups[group]
        old_members = [v['username'] for v in group['members']]
        actions = []
        # diff old members vs new image to get remove actions
        remove_members = list(set(old_members).difference(set(groups[group['shortname']])))
        for user in remove_members:
            # check that this is one of our users
            if user in sms_users:
                account = sms_users[user]
                # only remove ordinary members - not teachers
                if 'mlepRole' in account and not re.match('Teacher', account['mlepRole']):
                    actions.append({'username': all_users[user], 'action': 'remove'})
        # do the add/update roles
        for user in groups[group['shortname']]:
            account = sms_users[user]
            # teachers are 'tutor' students are members
            if 'mlepRole' in account and re.match('Teacher', account['mlepRole']):
                role = 'tutor'
            else:
                role = 'member'
            actions.append({'username': all_users[user], 'role': role, 'action': 'add'})
        group_updates.append({'shortname': group['shortname'], 'institution': group['institution'], 'members': actions})
    
    # process the group change sets
    if options.groups:
        logging.info("processing groups")
        if group_creates:
            logging.info("processing group creates")
            parameters = {"wsfunction":"mahara_group_create_groups", "groups": group_creates}
            result = mp.call_mahara(parameters)
            logging.debug('Create groups response: ' + repr(result))

        if group_updates:
            logging.info("processing group updates")
            parameters = {"wsfunction":"mahara_group_update_group_members", "groups": group_updates}
            result = mp.call_mahara(parameters)
            logging.debug('Update groups response: ' + repr(result))

        if group_deletes:
            logging.info("processing group deletes")
            parameters = {"wsfunction":"mahara_group_delete_groups", "groups": group_deletes}
            result = mp.call_mahara(parameters)
            logging.debug('Delete groups response: ' + repr(result))
    else:
        logging.info('group processing skipped')

    sys.exit(0)



# ------ Good Ol' main ------
if __name__ == "__main__":
    main()
