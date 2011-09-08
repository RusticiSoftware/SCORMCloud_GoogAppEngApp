#!/usr/bin/env python
# encoding: utf-8
"""
reminders.py

Copyright (c) 2010 Rustici Software. All rights reserved.
"""

import cgi
import os
import datetime
from datetime import timedelta


from google.appengine.dist import use_library
use_library('django', '1.1')



from models import *
from modelutils import *
from assignutils import *
from viewutils import *

if GetEnableAutoExpire():

    # application setup - add new pages here...
    logging.getLogger().setLevel(logging.DEBUG)



    logging.info("Kicking off the scheduled Auto-Expire process.")

    assignments = GetExpirableAssignments()

    if assignments is not None:
        totaldeactivated = 0
        for assignment in assignments:
            assignment.active = False;
            #setting the autoexpire to False to make the future GetAssignments calls faster
            assignment.autoexpire = False;
            assignment.put()
            totaldeactivated = totaldeactivated + 1
        logging.info(str(totaldeactivated) + " assignments were deactivated automatically at expiration.")

    logging.info("Ending the scheduled Auto-Expire process.")
