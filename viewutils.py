import cgi
import os
import datetime
import logging

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext.webapp import template
from google.appengine.api import images

import pytz
from pytz import timezone

from models import *
from modelutils import *

# utility functions
def page_display(page,file,values={}):
    template_values = {}

    userid = None
    isadmin = False
    istrainer = False
    iscc = False
    useremail = None
    messages = None
    isdomainadmin = False
    user = users.get_current_user()
    if user is not None:
        userid = user.user_id()
        #logging.info('userid:  ' + str(userid))
        isadmin = CheckUserRole(userid, "9")
        istrainer = isadmin or CheckUserRole(userid, "7")
        iscc = istrainer or CheckUserRole(userid, "5")
        useremail = user.email()
        isdomainadmin = users.is_current_user_admin()

        messages = GetUserMessages(userid)

    default_template_values = {'isadmin':isadmin
                                                            ,'isdomainadmin':isdomainadmin
                                                            ,'istrainer':istrainer
                                                            ,'iscc':iscc
                                                            ,'sitetitle': GetSiteTitle()
                                                            ,'currenturi': cgi.escape(page.request.uri)
                                                            ,'currenthost':page.request.headers['Host']
                                                            ,'logouturl':GetLogoutUrl()
                                                            ,'useremail':useremail
                                                            ,'userid':userid
                                                            ,'appsdomain':GetAppsDomain()
                                                            ,'usermessages':messages
                                                            }
    template_values = dict(page.template_values, **default_template_values)

    path = os.path.join(os.path.dirname(__file__),file)
    page.response.out.write(template.render(path,template_values))


def objectDisplay(obj):
    rt = ""
    for attr in dir(obj):
        rt += "<br/>entry.%s = %s" % (attr, getattr(obj, attr))
    return rt

def AdjustTimeZone(dtTime,ptimezone=None):
    if ptimezone is not None:
        strTz = ptimezone
    elif GetUserTimezone():
        strTz = GetUserTimezone()
    elif GetCalendarTimezone():
        strTz = GetCalendarTimezone()
        SetUserTimezone(strTz)
        userMsg = UserMessages(guser=users.get_current_user().user_id(),msgtype="warning")
        userMsg.message = "There is no timezone set for you. The primary timezone for the application has been set for you. <br/>You can change your timezone by clicking on the 'My Settings' link at the top of the page."
        userMsg.put()
    else:
        userMsg = UserMessages(guser=users.get_current_user().user_id(),msgtype="warning")
        userMsg.message = "There is no timezone set for you.  You can set your timezone by clicking on the 'My Settings' link at the top of the page."
        userMsg.put()
        return dtTime

    tz = timezone(strTz)
    if dtTime.tzinfo is None:
        utcdtTime = pytz.utc.localize(dtTime)
    else:
        utcdtTime = dtTime
    #logging.info(str(utcdtTime) + ' timezone: ' + str(tz) + ' : ' + str(tz.normalize(utcdtTime.astimezone(tz))))
    return tz.normalize(utcdtTime.astimezone(tz))
