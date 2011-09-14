import cgi
import os
import datetime
from datetime import timedelta
import logging

from google.appengine.ext import db
from google.appengine.ext.db import Key
from google.appengine.api import users
from google.appengine.api import images
from google.appengine.api import memcache

from scormcloud.client import ScormCloudService
from scormcloud.client import ScormCloudUtilities
from models import *

# **********************************
#               Settings
# **********************************

def GetCloudService():
    settings = GetSettings()
    origin = ScormCloudUtilities.get_canonical_origin_string('Rustici Software',
                'Google App Engine', '2.0')
    return ScormCloudService.withargs(settings.appid, settings.secretkey,
                                      settings.servicehost, origin)

def GetSettings():
    s = memcache.get('current_settings')
    if s is not None:
        return s
    else:
        s = Settings.all()
        if(s.count(1)>0):
            memcache.add("current_settings", s[0], 60)
            return s[0]
        else:
            return None

def GetSiteTitle():
    settings = GetSettings()
    if settings is not None:
        return settings.sitetitle
    else:
        return None

def GetAppsDomain():
    settings = GetSettings()
    if settings is not None and settings.appsdomain != '':
        return settings.appsdomain
    else:
        return None

def GetAppServerHost():
    settings = GetSettings()
    return settings.appserverhost

def GetCalendarId():
    settings = GetSettings()
    return settings.calendarid

def SetCalendarId(newid):
    s = GetSettings()
    s.calendarid = newid
    s.put()

def GetCalendarTimezone():
    settings = GetSettings()
    return settings.calendartimezone

def SetCalendarTimezone(timezone):
    s = GetSettings()
    s.calendartimezone = timezone
    s.put()

def GetEnableReminders():
    settings = GetSettings()
    return settings.enablereminders

def GetEnableAutoExpire():
    settings = GetSettings()
    return settings.enableautoexpire


def GetReminderSender():
    settings = GetSettings()
    return settings.remindersender

def GetSiteDefaultAvatar():
    settings = GetSettings()
    return settings.defaultavatar

def GetStartLogo():
    settings = GetSettings()
    if settings is not None:
        return settings.startlogo
    else:
        return None

def GetStartText():
    settings = GetSettings()
    if settings is not None:
        return settings.starttext
    else:
        return None


# **********************************
#               Courses
# **********************************


def GetCourse(courseid):
    courses = Course.gql("WHERE courseid = :1", courseid)
    if courses.count() > 0:
        return courses[0]
    else:
        return None

def GetCourses(qtype=None,qtext=None):
    foundCourses = []
    if qtype and qtext:
        if qtype == 'tag':
            courses = Course.all()
            courses.filter('tags = ',qtext)
            courses.order("title")
            for course in courses:
                foundCourses.append(course)
        else:
            courses = Course.gql("ORDER BY title")
            for course in courses:
                if course.title.lower().find(qtext.lower()) > -1:
                    foundCourses.append(course)
    else:
        courses = Course.gql("ORDER BY title")
        for course in courses:
            foundCourses.append(course)
    if len(foundCourses) > 0:
        return foundCourses
    else:
        return None


def GetCoursesDateDesc():
    return Course.gql("ORDER BY createddate DESC")

def GetCatalogCoursesDateDesc():
    return Course.gql("WHERE incatalog = True ORDER BY createddate DESC")


def GetCourseTitle(courseid):
    return GetCourse(courseid).title


def GetCourseDescription(courseid):
    return GetCourse(courseid).descriptiontext

def GetCourseTags(courseid,separator=' '):
    course = GetCourse(courseid)
    if (course.tags is not None) and len(course.tags) > 0:
        return separator.join(course.tags)
    else:
        return None

def DbDeleteCourse(courseid):
    if GetCourseAssignments(courseid) is not None:
        assignments = GetCourseAssignments(courseid)
        for a in assignments:
            db.delete(a)
    if GetCourseRegs(courseid) is not None:
        db.delete(GetCourseRegs(courseid))
    db.delete(GetCourse(courseid))

def SetOrphanCourse(courseid):
    course = GetCourse(courseid)
    if not course.orphaned:
        course.incatalog = False
        course.orphaned = True
        course.put()
        if GetCourseAssignments(courseid) is not None:
            assignments = GetCourseAssignments(courseid)
            for a in assignments:
                a.active = False;
                a.put()
        if GetCourseRegs(courseid) is not None:
            regs = GetCourseRegs(courseid)
            for r in regs:
                r.active = False
                r.put()


# **********************************
#               Users
# **********************************


def GetLearnerTags(userkey,separator=' '):
    u = GetUserProfileFromUserId(Key(userkey))
    if u.tags is not None:
        return separator.join(u.tags)
    else:
        return None

def GetUsers(qtype=None,qtext=None):
    foundUsers = []
    if qtype and qtext:
        if qtype == 'tag':
            userprofiles = UserProfile.all()
            userprofiles.filter('tags = ',qtext)
            userprofiles.order("lname")
            for userprofile in userprofiles:
                foundUsers.append(userprofile)
        elif qtype == 'lname':
            userprofiles = UserProfile.gql("ORDER BY lname")
            for userprofile in userprofiles:
                if userprofile.lname is not None and userprofile.lname.lower().find(qtext.lower()) > -1:
                    foundUsers.append(userprofile)
        elif qtype == 'fname':
            userprofiles = UserProfile.gql("ORDER BY lname")
            for userprofile in userprofiles:
                if userprofile.fname is not None and userprofile.fname.lower().find(qtext.lower()) > -1:
                    foundUsers.append(userprofile)

    else:
        userprofiles = UserProfile.gql("ORDER BY lname")
        for u in userprofiles:
            foundUsers.append(u)
    return foundUsers


    UserProfile.gql("ORDER BY lname")

def GetAdminUsers():
    admins = UserProfile.gql("WHERE accesslevel = :1","9")
    return admins

def GetUserProfileFromUserId(userkey):
    return db.get(userkey)

def GetUserProfileFromEmail(email):
    u = UserProfile.gql("WHERE email = :1",email)
    if u.count() > 0:
        return u[0]
    else:
        return None

def GetUserProfile():
    if users.get_current_user() is not None:
        return GetUserProfileFromGuser(users.get_current_user().user_id())
    else:
        return None;

def GetUserTimezone():
    u = GetUserProfile()
    return u.timezone

def SetUserTimezone(timezone):
    u = GetUserProfile()
    u.timezone = timezone
    u.put()

def GetUserProfileFromGuser(guser):
    u = UserProfile.gql("WHERE guser = :1",guser)
    if u.count() > 0:
        return u[0]
    else:
        return None

def GetUserKeyFromGuser(guser):
    u = UserProfile.gql("WHERE guser = :1",guser)
    if u.count() > 0:
        return u[0].key()
    else:
        return None

def GetUserEmailFromGuser(guser):
    u = GetUserProfileFromGuser(guser)
    return u.email

def GetUserNicknameFromGuser(guser):
    u = GetUserProfileFromGuser(guser)
    return u.nickname

def GetAssignmentUsers(assignid):
    assignment = GetAssignment(assignid)
    regs = GetAssignmentRegs(assignment)
    ups = []
    if regs is not None:
        for reg in regs:
            up = GetUserProfileFromUserId(key(reg.userid))
            ups.append(up)
        if len(ups) > 0:
            return ups
        else:
            return None
    else:
        return None

def UserEmailExists(email):
    return (GetUserProfileFromEmail(email) is not None)

def CheckUserRole(guser, role):
    up = GetUserProfileFromGuser(guser)
    if(up.accesslevel >= role):
        return True
    else:
        return False


# **********************************
#               Registrations
# **********************************


def GetCourseRegCount(courseid):
    regs = Registration.gql("WHERE courseid = :1", courseid)
    return regs.count()


def GetRegistrationTags(regid,separator=' '):
    settings = GetSettings()
    reg = GetRegistration(regid)
    tags = ''
    if reg.assignment is not None:
        tags = str(reg.assignment.key()) + separator
    return tags + settings.appsdomain



def GetRegistration(regid):
    regs = Registration.gql("WHERE regid = :1", regid)
    if regs.count() > 0:
        return regs[0]
    else:
        return None


def GetCourseRegs(courseid):
    regs = Registration.gql("WHERE courseid = :1 "
                                                    "ORDER BY lastaccess DESC",courseid)
    if regs.count() > 0:
        return regs
    else:
        return None

def GetUserRegs(userkey):
    regs = Registration.gql("WHERE userid = :1 "
                                                    "ORDER BY lastaccess DESC",str(userkey))
    if regs.count() > 0:
        return regs
    else:
        return None

def GetActiveUserRegs(userkey):
    allregs = Registration.gql("WHERE userid = :1 "
                                                    "ORDER BY lastaccess DESC",str(userkey))

    if allregs.count() > 0:
        regs = []
        for reg in allregs:
            if reg.assignment is None or reg.assignment.active:
                regs.append(reg)
        if len(regs) > 0:
            return regs
    else:
        return None
    return None


def GetUserCourseReg(guser, courseid):
    up = GetUserProfileFromGuser(guser)
    regs = Registration.gql("WHERE userid = :1 AND courseid = :2 "
                                                    "ORDER BY lastaccess DESC",str(up.key()), courseid)
    if regs.count() > 0:
        for reg in regs:
            if reg.assignment is None or reg.assignment.active:
                return reg
    else:
        return None
    return None


def GetUserCourseRegId(guser, courseid):
    reg = GetUserCourseReg(guser, courseid)
    return (reg is None and None or reg.regid)

def GetRegIdFromUserAssignment(userid,assignment):
    regs = Registration.gql("WHERE userid = :1 AND assignment = :2", userid,assignment)
    if regs.count() > 0:
        return regs[0].regid
    else:
        return None

def GetAssignmentRegs(assignment,population="all"):
    regs = Registration.all()
    regs.filter('assignment = ',assignment)
    if population == "started":
        regs.filter('lastaccess != ',None)
        regs.order("-lastaccess")
    if population == "notstarted":
        regs.filter('lastaccess == ',None)
    if population == "complete":
        regs.filter('completion == ','complete')
    if population == "incomplete":
        regs.filter('completion != ','complete')
        regs.order("completion")



    if regs.count() > 0:
        return regs
    else:
        return None


def GetRegUserId(regid):
    regs = Registration.gql("WHERE regid = :1", regid)
    if regs.count() > 0:
        return regs[0].userid
    else:
        return None

def GetRegCourseId(regid):
    regs = Registration.gql("WHERE regid = :1", regid)
    if regs.count() > 0:
        return regs[0].courseid
    else:
        return None

def UpdateRegAccessDate(regid):
    regs = Registration.gql("WHERE regid = :1", regid)
    for reg in regs:
        reg.lastaccess = datetime.datetime.utcnow()
        reg.put()

def CreateNewRegistration(userkey, courseid, assignment=None):
    oUser = GetUserProfileFromUserId(userkey)
    cloud = GetCloudService()
    regsvc = cloud.get_registration_service()
    fname = oUser.fname or oUser.lname or oUser.email
    lname = oUser.lname or oUser.email
    regid = regsvc.create_registration(regid=None, courseid=courseid, userid=str(oUser.key()), fname=fname, lname=lname)
    #now create one in the GQL table
    reg = Registration()
    reg.regid = regid
    reg.courseid = courseid
    reg.coursetitle = GetCourseTitle(courseid)
    reg.userid = str(oUser.key())
    reg.completion = 'unknown'
    reg.satisfaction = 'unknown'
    if assignment is not None:
        reg.assignment = assignment
    reg.put()
    return regid

def DeleteRegistration(regid):
    #delete from the cloud
    cloud = GetCloudService()
    regsvc = cloud.get_registration_service()
    cloudresult = regsvc.delete_registration(regid)
    #need to check for success here:
    #but for now...
    #delete from local tables
    localregs = db.GqlQuery("SELECT * FROM Registration WHERE regid = :1",regid)
    for r in localregs:
        r.delete()

def ResetRegistration(regid):
    cloud = GetCloudService()
    regsvc = cloud.get_registration_service()
    cloudresult = regsvc.reset_registration(regid)
    #need to check for success here:
    #but for now...
    #delete from local tables
    localregs = db.GqlQuery("SELECT * FROM Registration WHERE regid = :1",regid)
    for reg in localregs:
        reg.completion = 'unknown'
        reg.satisfaction = 'unknown'
        reg.score = None
        reg.timespent = None
        reg.lastaccess = None
        reg.put()


# **********************************
#               Assignments
# **********************************


def GetCourseAssignments(courseid):
    assignments = Assignments.gql("WHERE courseid = :1 ",courseid)
    if assignments.count() > 0:
        return assignments
    else:
        return None

def GetUserAssignments(guser):
    assignments = Assignments.gql("WHERE createdbyuser = :1  ORDER By createddate DESC",guser)
    if assignments.count() > 0:
        return assignments
    else:
        return None

def GetAssignments(guser=None,datetype='all'):
    assignments = Assignments.all()
    datenow = datetime.datetime.utcnow()
    if guser is not None:
        assignments.filter('createdbyuser =',guser)
    if datetype == 'expired':
        assignments.filter('duedate <',datenow)
    elif datetype == 'pending':
        assignments.filter('duedate >',datenow)
    elif datetype == 'nodate':
        assignments.filter('duedate =',None)
    elif datetype == 'active':
        assignments.filter('active =',True)
    elif datetype == 'inactive':
        assignments.filter('active =',False)
    assignments.order("-duedate")
    assignments.order("-createddate")
    if assignments.count() > 0:
        return assignments
    else:
        return None

def GetAssignment(assignid):
    return db.get(Key(assignid))


def IsAssignmentActive(assignid):
    a = GetAssignment(assignid)
    return a.active

def DbDeleteAssignment(assignid):
    a = GetAssignment(assignid)
    if GetAssignmentRegs(a) is not None:
        db.delete(GetAssignmentRegs(a))
    db.delete(a)

def GetExpirableAssignments():
    testtime = datetime.datetime.utcnow() + timedelta(minutes=5)
    assignments = Assignments.gql("WHERE autoexpire = True and duedate < :1", testtime)
    if assignments.count() > 0:
        return assignments
    else:
        return None

# **********************************
#               Reminders
# **********************************

def GetReminders(assignment):
    reminders = Reminders.gql("WHERE assignment = :1", assignment)
    if reminders.count() > 0:
        return reminders
    else:
        return None

def GetSendableReminders():
    testtime = datetime.datetime.utcnow() + timedelta(hours=1)
    reminders = Reminders.gql("WHERE sent = :1 and remindertime < :2", False,testtime)
    if reminders.count() > 0:
        return reminders
    else:
        return None

def SetReminderTime(reminder):
    duedate = reminder.assignment.duedate
    reminderTimeDelta = None
    if reminder.timeunits == "minutes":
        reminderTimeDelta = timedelta(minutes=reminder.timequantity)
    elif reminder.timeunits == "hours":
        reminderTimeDelta = timedelta(hours=reminder.timequantity)
    elif reminder.timeunits == "days":
        reminderTimeDelta = timedelta(days=reminder.timequantity)
    if reminderTimeDelta is not None:
        reminder.reminderdate = duedate - reminderTimeDelta
        reminder.put()


# **********************************
#               Misc.
# **********************************

def GetUserMessages(guser):
    msgs = UserMessages.gql("WHERE guser = :1",guser)
    return msgs.count() > 0 and msgs or None

def AddAdminMessages(msgType,msg):
    admins = GetAdminUsers()
    for admin in admins:
        userMsg = UserMessages(admin.guser,msgtype)
        userMsg.message = msg
        userMsg.put()



# **********************************
#               Misc.
# **********************************



def GetLogoutUrl():
    return users.create_logout_url('/')
