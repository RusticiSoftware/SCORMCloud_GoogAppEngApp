#!/usr/bin/env python
# encoding: utf-8
"""
decorators.py

Created by brian.rogers on 2009-11-05.
Copyright (c) 2009 Rustici Software. All rights reserved.
"""

import cgi
import os
import datetime
from google.appengine.ext import db
from google.appengine.api import users

from models import *
from modelutils import *

cloud = GetCloudService()

# decorators
def loginRequired(func):
    def wrapper(self, *args, **kw):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
        else:
            #make sure this user is in our UserProfile table
            #also update the lastaccess field
            up = GetUserProfile()
            if up is not None:
                #user exists, update lastaccess
                up.lastaccess = datetime.datetime.utcnow()
                if not up.email == user.email():
                    up.email = user.email()
                up.put()
            else:
                ups = UserProfile.gql("WHERE email = :1", user.email())
                if(ups.count() > 0):
                    for up in ups:
                        #user exists, update lastaccess
                        up.lastaccess = datetime.datetime.utcnow()
                        if up.guser is None:
                            up.guser = user.user_id()
                            up.nickname = user.nickname()

                            userMsg = UserMessages(guser=user.user_id(),msgtype="info")
                            userMsg.message = "Welcome to the SCORM Cloud App for Google Domains. You can find your assignments and any available courses by clicking on the 'My Training' link."
                            userMsg.put()

                        up.put()
                else:
                    #user doesn't exist yet...create a UserProfile for them
                    up = UserProfile()
                    up.guser = user.user_id()
                    up.email = user.email()
                    up.nickname = user.nickname()
                    up.fname = user.nickname()
                    up.lname = user.nickname()
                    up.assignmentemail = True
                    up.allowcalendaraccess = True
                    if users.is_current_user_admin():
                        up.accesslevel = "9"
                    else:
                        up.accesslevel = "0"
                    up.lastaccess = datetime.datetime.utcnow()
                    settings = GetSettings()
                    if settings is not None and settings.defaultavatar:
                        up.userimage = settings.defaultavatar

                    userMsg = UserMessages(guser=user.user_id(),msgtype="info")
                    userMsg.message = "Welcome to the SCORM Cloud App for Google Domains. You can find your assignments and any available catalog courses by clicking on the 'My Training' link."
                    userMsg.put()

                    userMsg = UserMessages(guser=user.user_id(),msgtype="info")
                    userMsg.message = "Your first and last names have been defaulted to your account nickname.  Please click on the 'My Settings' link at the top of the page to edit your account info."
                    userMsg.put()

                    up.put()
                    if settings is None:
                        self.redirect('admin/settings')

            func(self, *args, **kw)
    return wrapper

def adminRequired(func):
    def wrapper(self, *args, **kw):
        if(users.is_current_user_admin()):
            func(self, *args, **kw)
        else:
            self.redirect('/')
    return wrapper

def checkConnection(func):
    def wrapper(self, *args, **kw):
        if CheckAuthCloudPing():
            func(self, *args, **kw)
        elif CheckCloudPing():
            if(users.is_current_user_admin()):
                userMsg = UserMessages(guser=users.get_current_user().user_id(),msgtype="error")
                userMsg.message = "There is a problem authenticating your account with SCORM Cloud.  Please check the appId and secret key saved in the app settings."
                userMsg.put()
                func(self, *args, **kw)
                #self.redirect('/admin/settings?tab=cloud')
            else:
                userMsg = UserMessages(guser=users.get_current_user().user_id(),msgtype="error")
                userMsg.message = "There is a problem authenticating your account with SCORM Cloud.  Please contact your system administrator."
                userMsg.put()
                func(self, *args, **kw)
        else:
            userMsg = UserMessages(guser=users.get_current_user().user_id(),msgtype="error")
            userMsg.message = "There is a problem contacting the SCORM Cloud.  Please contact your system administrator."
            userMsg.put()
            func(self, *args, **kw)
    return wrapper

def CheckAuthCloudPing():
    dsvc = cloud.get_debug_service()
    return dsvc.authping()
def CheckCloudPing():
    dsvc = cloud.get_debug_service()
    return dsvc.ping()


def roleRequired(role):
    def wrapper(handler_method):
        def check_role(self, *args, **kwargs):
            obj = None
            args = list(args)
            user = users.get_current_user()
            if not user:
                self.redirect(users.create_login_url(self.request.uri))
            else:
                if(CheckUserRole(user,role)):
                    #obj = True
                    #args[0] = obj
                    handler_method(self, *args, **kwargs)
                else:
                    self.redirect('/')
        return check_role
    return wrapper


def CheckUserRole(user, role):
    if(users.is_current_user_admin()):
        return True
    else:
        ups = db.GqlQuery("SELECT * FROM UserProfile WHERE guser = :1", user.user_id())
        if(ups.count(1) > 0):
            for up in ups:
                if(up.accesslevel >= role):
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False

def dump_image(imgfile):
    i = open(imgfile, 'rb')
    i.seek(0)
    w = i.read()
    i.close()
    return cPickle.dumps(w,1)
