This is a set of tools for reformatting and processing
the NZ School SMS IDE (Identity Data Extract) CSV file
format into import formats for Moodle, and Mahara

 - starting with:
 - Mahara via Web Services - https://gitorious.org/mahara-contrib/artefact-webservice
 - Mahara via CSV upload  - https://wiki.mahara.org/index.php/Institute_administrator_guide/1_User_administration/Bulk_uploading_students
 - Moodle via CSV upload - http://docs.moodle.org/20/en/admin/uploaduser

Each program is written in Python, and will require 2.5 or later, with 
additional library dependencies for OAuth when communicating with
Mahara via web services.

each program has further documentation within, and the command line options
have standard help eg: python mahara_ide_import.py -h

The IDE (Identity Data Extract) is a CSV file format that SMS vendors in 
New Zealand generate to describe users for synchronisation to the school
user directory.  This program extends the usefulness of this export format
for the purpose of automatic provisioning of Moodle accounts, and courses.

Further information can be found at http://www.iam.school.nz/ and the original 
user directory initiative is at: https://gitorious.org/pla-udi/pages/Home

Copyright (C) Piers Harding 2011 and beyond, All rights reserved

all included programs are free software; you can redistribute them and/or
modify them under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2 of the License, or (at your option) any later version.

This software is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

