import cgi
import os
import datetime
import logging
from xml.dom import minidom

from google.appengine.api import users
from google.appengine.api import mail
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.api import images
from google.appengine.api import memcache
from google.appengine.ext.db import stats
from google.appengine.ext.db import Key

from django.utils import simplejson
from django.core.paginator import Paginator, InvalidPage
from django import http

import pytz
from pytz import timezone
from pytz import common_timezones

from models import *
from modelutils import *
from decorators import *
from viewutils import *
from assignutils import *
from scormcloud.client import ScormCloudService
from scormcloud.client import ScormCloudUtilities
from gdatautils import *


template.register_template_library('templatetags.seconds_to_duration')
template.register_template_library('templatetags.scormcloud_filters')

settings = GetSettings()
origin = ScormCloudUtilities.get_canonical_origin_string('Rustici Software',
            'Google App Engine', '2.0')
cloud = ScormCloudService.withargs(settings.appid, settings.secretkey, 
                                   settings.servicehost, origin)


# *******************************************
# ****                  Settings Views
#********************************************

class SettingsForm(webapp.RequestHandler):
    @loginRequired
    @adminRequired
    def get(self):
        settings = GetSettings()
        if settings is None:
            settings = Settings()
            settings.sitetitle = "SCORM Cloud For Google Apps"
            settings.appid = None
            settings.secretkey = None
            settings.servicehost = "http://cloud.scorm.com/EngineWebServices"
            settings.appsdomain = None
            settings.duetime = datetime.datetime.strptime("18:00", "%H:%M").time()
            settings.enableautoexpire = False
            settings.enablereminders = False
            settings.put()

        timezones = common_timezones
        self.template_values = {'settings': settings,
                                'timezones': timezones,
                                'enablereminders':(settings.enablereminders and 
                                        "checked" or ""),
                                'enableautoexpire': (settings.enableautoexpire 
                                        and "checked" or ""),
                                'tab': self.request.get('tab') or None }
        page_display(self,"templates/settingsform.html")


class SettingsAction(webapp.RequestHandler):
    @loginRequired
    @adminRequired
    def post(self):
        s = GetSettings()
        if self.request.get('sitetitle') and 
            self.request.get('sitetitle') != '':
            s.sitetitle = self.request.get('sitetitle')
        if self.request.get('appid'):
            s.appid = self.request.get('appid')
        if self.request.get('secretkey'):
            s.secretkey = self.request.get('secretkey')
        if self.request.get('servicehost'):
            s.servicehost = self.request.get('servicehost')
        if self.request.get('appsdomain'):
            s.appsdomain = self.request.get('appsdomain')
        if self.request.get('starttext') 
            and self.request.get('starttext') != '':
            s.starttext = self.request.get('starttext')
        if self.request.get('startlogo') 
            and self.request.get('startlogo') != '':
            s.startlogo = self.request.get('startlogo')
        if self.request.get('duetime'):
            s.duetime = datetime.datetime.strptime(self.request.get('duetime'),
                "%H:%M").time()
        if self.request.get('timezone'):
            s.calendartimezone = self.request.get('timezone')
        if self.request.get('remindersender'):
            s.remindersender = self.request.get('remindersender')
            if self.request.get('enablereminders'):
                s.enablereminders = (self.request.get('enablereminders') == 
                    "on")
            else:
                s.enablereminders = False
            if self.request.get('enableautoexpire'):
                s.enableautoexpire = (self.request.get('enableautoexpire') == 
                    "on")
            else:
                s.enableautoexpire = False
        if self.request.get("defaultavatar"):
            avatar = images.resize(self.request.get("defaultavatar"), 50, 50)
            s.defaultavatar = db.Blob(avatar)
        s.appserverhost = self.request.headers['Host']
        s.put()
        memcache.set("current_settings", s, 60)
        self.redirect('/admin/settings')

# *******************************************
# ****                  User Admin Views
#********************************************

class UserList(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def get(self, page=1):
        try:
            page = int(page)
        except:
            page = 1

        qtype = self.request.get('qtype') or None
        qtext = self.request.get('qtext') or None
        if qtype and qtext:
            querystring = "?qtype=" + qtype + "&qtext=" + qtext
        else:
            querystring = None
        userprofiles = GetUsers(qtype,qtext)

        paginator = Paginator(userprofiles,10)

        self.template_values = {
            'userprofiles': paginator.page(page).object_list,
            'usercount': len(userprofiles),
            'pages': paginator.page_range,
            'morepages': (paginator.num_pages > 1),
            'page': page,
            'qtype': qtype,
            'qtext': qtext,
            'qs': querystring,
            'showreportLinks': CheckAuthCloudPing()
        }
        page_display(self,"templates/userlist.html")


class UserDetails(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def get(self, userkey):
        ukey = Key(userkey)
        userprofile = GetUserProfileFromUserId(ukey)
        if userprofile.lastaccess:
            userprofile.lastaccess = AdjustTimeZone(userprofile.lastaccess)
        userregs = []
        regs = GetUserRegs(ukey)
        if regs is not None:
            for reg in regs:
                if reg.assignment and reg.assignment.duedate:
                    reg.assignment.duedate = AdjustTimeZone(reg.assignment.duedate)
                userregs.append(reg)

        self.template_values = {'userprofile':userprofile,
                                'userregs':userregs}
        page_display(self,"templates/userdetails.html")


class UserAdminForm(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def get(self, guser):
        userprofile = GetUserProfileFromGuser(guser)

        self.template_values = {'userprofile':userprofile}

        page_display(self,"templates/useradminform.html")


class UserAdminAction(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def post(self):
        userkey = self.request.get('userkey')
        u = db.get(Key(userkey))
        u.fname = self.request.get('fname')
        u.lname = self.request.get('lname')
        #if self.request.get('avatar'):
        #       avatar = images.resize(self.request.get("avatar"), 50, 50)
        #       u.userimage = db.Blob(avatar)

        oldEmail = u.email
        u.email = self.request.get('email')
        emailChanged = (oldEmail != u.email)

        oldAccessLevel = u.accesslevel
        u.accesslevel = self.request.get('accesslevel')
        accessChanged = (oldAccessLevel != u.accesslevel)

        if emailChanged or accessChanged:
            calsvc = GCalendarService(self.request.uri,GetAppsDomain())
            if not calsvc.valid:
                calurl = calsvc.GetAuthenticationURL()
                output = "<script type='text/javascript'>window.location = '" + str(calurl) + "'</script>"
                self.response.out.write(output)
            else:
                if int(oldAccessLevel) > 5 and (emailChanged or int(u.accesslevel) < 6):
                    try:
                        calsvc.UpdateCalendarOwnership(GetCalendarId(),'remove',oldEmail)
                    except:
                        userMsg = UserMessages(guser=users.get_current_user().user_id(),msgtype="error")
                        userMsg.message = "There was a problem removing calendar rights from " + oldEmail + ". You may need to try again manually within the calendar."
                        userMsg.put()

                if accessChanged:
                    if int(u.accesslevel) > 5:
                        if u.accesslevel == '9':
                            try:
                                calsvc.UpdateCalendarOwnership(GetCalendarId(),'owner',u.email)
                            except Exception, e:
                                userMsg = UserMessages(guser=users.get_current_user().user_id(),msgtype="error")
                                userMsg.message = "There was a problem adding calendar 'owner' rights to " + u.email + ". You may need to try again manually within the calendar."
                                userMsg.put()
                        else:
                            try:
                                calsvc.UpdateCalendarOwnership(GetCalendarId(),'editor',u.email)
                            except Exception, e:
                                userMsg = UserMessages(guser=users.get_current_user().user_id(),msgtype="error")
                                userMsg.message = "There was a problem adding calendar 'editor' rights to " + u.email + ". You may need to try again manually within the calendar."
                                userMsg.put()
                u.put()
                self.redirect('/user/' + str(u.key()))
        else:
            u.put()
            self.redirect('/user/' + str(u.key()))

class UpdateUserInfo(webapp.RequestHandler):
    @loginRequired
    @adminRequired
    def get(self):
        appUsers = UserProfile.all()

        domain = GetAppsDomain()
        gsvc = GProfileService(self.request.uri,domain)
        if not gsvc.valid:
            url = gsvc.GetAuthenticationURL()
            output = "<script type='text/javascript'>window.location = '" + str(url) + "'</script>"
            self.response.out.write(output)
        else:
            domainUsers = gsvc.GetAllDomainUsers()
            for up in appUsers:
                if up.email in domainUsers:
                    du = domainUsers[up.email]
                    up.fname = du['firstname']
                    up.lname = du['lastname']
                    up.put()

            self.redirect('/admin/user/list')

class ImportDomainUsers(webapp.RequestHandler):
    @loginRequired
    @adminRequired
    def get(self):
        settings = GetSettings()
        appUsers = UserProfile.all()

        gsvc = GProfileService(self.request.uri,settings.appsdomain)
        if not gsvc.valid:
            url = gsvc.GetAuthenticationURL()
            output = "<script type='text/javascript'>window.location = '" + str(url) + "'</script>"
            self.response.out.write(output)
        else:
            domainUsers = gsvc.GetAllDomainUsers()
            if domainUsers is not None:
                '''for u in appUsers:
                        if u.email in domainUsers:
                                du = domainUsers[u.email]
                                u.fname = du['firstname']
                                u.lname = du['lastname']
                                u.put()
                                del domainUsers[u.email]'''
                for email in domainUsers:
                    if not UserEmailExists(email):
                        du = domainUsers[email]
                        up = UserProfile()
                        gu = users.User(email)
                        up.guser = gu.user_id()
                        up.email = email
                        up.fname = du['firstname']
                        up.lname = du['lastname']
                        up.nickname = gu.nickname()
                        up.assignmentemail = True
                        up.allowcalendaraccess = True
                        up.accesslevel = "0"
                        if settings.defaultavatar:
                            up.userimage = settings.defaultavatar
                        up.put()
            self.redirect('/admin/user/list')



# *******************************************
# ****                  Upload / Import Views
#********************************************

class UploadForm(webapp.RequestHandler):
    @loginRequired
    @roleRequired("5")

    def get(self):
        settings = GetSettings()
        upsvc = cloud.get_upload_service()

        importurl = "http://" + self.request.headers['Host'] + "/course/import"
        clouduploadurl = upsvc.get_upload_url(importurl)
        self.template_values = {'action': clouduploadurl}

        page_display(self,"templates/uploadform.html")


class Importer(webapp.RequestHandler):
    @loginRequired
    @roleRequired("5")
    def get(self):
        #import the course to the cloud
        csvc = cloud.get_course_service()
        course = csvc.import_uploaded_couse(path=self.request.get('location'))

        courseid = course.courseid

        metadataXml = csvc.get_metadata(courseid)
        metadataDom = minidom.parseString(metadataXml)
        desc = metadataDom.getElementsByTagName("description")
        description = None
        if desc.length > 0 and desc[0].childNodes.length > 0:
            description = desc[0].childNodes[0].nodeValue

        dur = metadataDom.getElementsByTagName("duration")
        duration =dur.length > 0 and int(dur[0].childNodes[0].nodeValue) > 0 and int(dur[0].childNodes[0].nodeValue)//100 or "unknown"


        #now add the course to the local tables
        cdb = Course()
        cdb.courseid = courseid
        cdb.title = course.title
        cdb.descriptiontext = description
        cdb.duration = str(duration)
        cdb.createdbyuser = users.get_current_user().user_id()
        cdb.gappimport = True
        cdb.put()

        self.template_values = {'action': '/course/updateaction'
                                                ,'coursetitle': cdb.title
                                                ,'descriptiontext': cdb.descriptiontext
                                                ,'tags': ' '.join(cdb.tags)
                                                ,'courseid': courseid
                                                ,'incatalog': (cdb.incatalog and 'checked' or '')
                                                }

        page_display(self,"templates/updatecourseform.html")

class AddCloudCourseAction(webapp.RequestHandler):
    @loginRequired
    @roleRequired("5")
    def post(self):
        courseid = self.request.get('cloudcourseid')

        csvc = cloud.get_course_service()
        metadataXml = csvc.get_metadata(courseid)
        metadataDom = minidom.parseString(metadataXml)
        desc = metadataDom.getElementsByTagName("description")
        description = None
        if desc.length > 0 and desc[0].childNodes.length > 0:
            description = desc[0].childNodes[0].nodeValue

        dur = metadataDom.getElementsByTagName("duration")
        duration = int(dur[0].childNodes[0].nodeValue) > 0 and int(dur[0].childNodes[0].nodeValue)//100 or "unknown"

        course = Course()
        course.courseid = courseid
        course.title = self.request.get('cloudcoursetitle')
        course.descriptiontext = description
        course.duration = str(duration)
        course.createdbyuser = users.get_current_user().user_id()
        course.gappimport = False
        course.put()

        self.redirect("/course/update/"+self.request.get('cloudcourseid'))


# *******************************************
# ****                  Course Admin Views
#********************************************

class CourseList(webapp.RequestHandler):
    @loginRequired
    @roleRequired("5")
    @checkConnection
    def get(self,page=1):
        try:
            page = int(page)
        except:
            page = 1

        qtype = self.request.get('qtype') or None
        qtext = self.request.get('qtext') or None


        courses = GetCourses(qtype,qtext)

        if qtype and qtext:
            querystring = "?qtype=" + qtype + "&qtext=" + qtext
            allAppcourses = GetCourses()
        else:
            querystring = None
            allAppcourses = courses

        csvc = cloud.get_course_service()
        cloudCourses =  csvc.get_course_list()


        coursecount = courses is not None and len(courses) or 0
        allcourses = []
        if coursecount > 0:
            for course in courses:
                course.tagstring = GetCourseTags(course.courseid)
                up = GetUserProfileFromGuser(course.createdbyuser)
                if up.fname and up.lname:
                    course.creator = up.fname + ' ' + up.lname
                else:
                    course.creator = up.email
                #course.usercanreg = UserCanRegister(users.get_current_user().user_id(), course.courseid)
                course.regcount = GetCourseRegCount(course.courseid)

                checkconnection = None
                if course.courseid in cloudCourses:
                    del cloudCourses[course.courseid]
                    allcourses.append(course)
                else:
                    if checkconnection is None:
                        checkconnection = CheckAuthCloudPing()
                    if checkconnection:
                        SetOrphanCourse(course.courseid)
                        allcourses.append(course)
            #if doing a search
            if allAppcourses is not None:
                for course in allAppcourses:
                    if course.courseid in cloudCourses:
                        del cloudCourses[course.courseid]



        paginator = Paginator(allcourses,10)

        upsvc = cloud.get_upload_service()

        importurl = "http://" + self.request.headers['Host'] + "/course/import"
        clouduploadurl = upsvc.get_upload_url(importurl)

        self.template_values = {
    "courses" : paginator.page(page).object_list
                ,"coursecount" : coursecount
    ,"pages" : paginator.page_range
                ,"morepages" : (paginator.num_pages > 1)
    ,"page" : page
                ,'uploadaction': clouduploadurl 
                ,'showcloudcourse': (len(cloudCourses) > 0)
                ,'cloudcourses':cloudCourses
                ,'qtype':qtype
                ,'qtext':qtext
                ,'qs':querystring
        }

        page_display(self,"templates/courselist.html")


class CourseAdminDetail(webapp.RequestHandler):
    @loginRequired
    @roleRequired("5")
    def get(self, courseid):
        course = GetCourse(courseid)
        #get the course metadata from the cloud
        csvc = cloud.get_course_service()
        rsvc = cloud.get_reporting_service()

        tags = TagSettings()
        #tags.AddTag('registration',settings.appsdomain)

        widgetSettings = WidgetSettings(None,tags)
        widgetSettings.courseId = courseid
        widgetSettings.showTitle = True
        widgetSettings.divname = 'CourseSummary'

        reportageUrl = rsvc.get_widget_url(rsvc.get_reportage_auth('NONAV','true'),'courseSummary',widgetSettings)

        userregs = []
        regs = GetCourseRegs(courseid)
        if regs is not None:
            for reg in regs:
                ur = {}
                ur['reg'] = reg
                ur['user'] = GetUserProfileFromUserId(Key(reg.userid))
                userregs.append(ur)

        #set the template values
        self.template_values = {'course': course
                                                ,'regcount':GetCourseRegCount(courseid)
                                                ,'tags':GetCourseTags(courseid)
                                                ,'reportageurl':reportageUrl
                                                ,'userregs':userregs
                                                }

        page_display(self,"templates/courseadmindetail.html")

class CourseUpdateForm(webapp.RequestHandler):
    @loginRequired
    @roleRequired("5")
    def get(self,courseid):
        course = GetCourse(courseid)

        self.template_values = {'action': '/course/updateaction'
                                                ,'coursetitle': course.title
                                                ,'descriptiontext': course.descriptiontext
                                                ,'tags': ' '.join(course.tags)
                                                ,'courseid': courseid
                                                ,'incatalog': (course.incatalog and 'checked' or '')
                                                }

        page_display(self,"templates/updatecourseform.html")

class CourseUpdateAction(webapp.RequestHandler):
    @loginRequired
    @roleRequired("5")
    def post(self):
        tags = self.request.get('tags').split(' ')
        course = GetCourse(self.request.get('courseid'))

        course.title = self.request.get('coursetitle')
        course.descriptiontext = self.request.get('descriptiontext')
        tags = self.request.get('tags').split(' ')
        course.tags = tags
        course.incatalog = (self.request.get('incatalog') == 'checked')
        course.put()
        #redirect back to the courselist page
        self.redirect("/course/admindetail/"+self.request.get('courseid'))

class DeleteCourse(webapp.RequestHandler):
    @loginRequired
    @roleRequired("5")
    def get(self,courseid):
        if courseid:

            course = GetCourse(courseid)
            if course.gappimport:
                #delete from the cloud
                csvc = cloud.get_course_service()
                csvc.delete_course(courseid)

            #delete from the local data
            DbDeleteCourse(courseid)
            self.redirect('/course/list')
        else:
            self.error(403)

class CourseRegs(webapp.RequestHandler):
    @loginRequired
    @adminRequired
    def get(self, courseid, page=1):
        try:
            page = int(page)
        except:
            page = 1

        #get all registrations for this course
        regs = Registration.all()
        regs.filter("courseid =", courseid)
        allregs = []
        for reg in regs:
            reg.useremail = GetUserEmailFromGuser(reg.userid)
            allregs.append(reg)
        #get the course title
        coursetitle = GetCourseTitle(courseid)
        coursedescription = GetCourseDescription(courseid)
        #setup the paginator
        paginator = Paginator(allregs,5)
        #set the template values
        self.template_values = {'regs' : paginator.page(page).object_list
                                                ,"pages" : paginator.page_range
                                    ,"page" : page
                                                ,'coursetitle': coursetitle
                                                ,'courseid':courseid
                                                }

        page_display(self,"templates/courseregs.html")



# *******************************************
# ****                  Registration Admin Views
#********************************************

class NewReg(webapp.RequestHandler):
    @loginRequired
    @adminRequired
    def get(self,courseid):
        if courseid:
            #add the registration to the cloud and local data
            CreateNewRegistration(GetUserKeyFromGuser(users.get_current_user().user_id()), courseid, None)
            #redirect to the launch page for now...
            self.redirect("/course/list")

class DeleteReg(webapp.RequestHandler):
    @loginRequired
    @adminRequired
    def get(self,regid):
        if regid:
            #add the registration to the cloud and local data
            result = DeleteRegistration(regid)
            #redirect to the launch page for now...
            #self.redirect(returnurl)

class ResetReg(webapp.RequestHandler):
    @loginRequired
    @adminRequired
    def get(self,regid):
        #add the registration to the cloud and local data
        result = ResetRegistration(regid)
        #redirect to the launch page for now...
        #if self.request.get('returnurl'):
        #       self.redirect(self.request.get('returnurl'))
        #else:
        self.redirect('/')

class RegList(webapp.RequestHandler):
    @loginRequired
    @adminRequired
    def get(self,regid):
        regs = db.GqlQuery("SELECT * FROM Registration ORDER BY created_date DESC LIMIT 100")
        output = '<table>'
        output += '<thead><tr><th>Course Title</th><th>Created Date</th><th></th></tr></thead>'
        for reg in regs:
            output += '<tr><td>%s</td><td>%s</td>' % (reg.userid,str(reg.created_date))
            output += '<td>%s</td>' % (cgi.escape(reg.courseid))
            output += '<td><a href="/launch?regid=%s">launch</a></td>' % (cgi.escape(reg.regid))
            output += '</tr>'

        output += '</table>'
        self.response.out.write(output)


# *******************************************
# ****                  Assignment Admin Views
#********************************************


class AssignForm(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    @checkConnection
    def get(self):

        courseid = self.request.get('courseid')
        settings = GetSettings()
        courses = GetCourses()

        uassignments = GetAssignments(users.get_current_user().user_id())
        uassignmentObjects = []
        if uassignments is not None:
            for assignment in uassignments:
                a = {}
                if assignment.duedate:
                    assignment.duedate = AdjustTimeZone(assignment.duedate)
                    assignment.createddate = AdjustTimeZone(assignment.createddate)
                a['assignment'] = assignment
                a['key'] = str(assignment.key())
                a['coursename'] = GetCourseTitle(assignment.courseid)
                uassignmentObjects.append(a)
        uapage = self.request.get('uapage') and int(self.request.get('uapage')) or 1
        uapaginator = Paginator(uassignmentObjects,10)

        assignments = GetAssignments()
        assignmentObjects = []
        if assignments is not None:
            for assignment in assignments:
                a = {}
                if assignment.duedate:
                    assignment.duedate = AdjustTimeZone(assignment.duedate)
                    assignment.createddate = AdjustTimeZone(assignment.createddate)
                a['assignment'] = assignment
                a['key'] = str(assignment.key())
                a['coursename'] = GetCourseTitle(assignment.courseid)
                assignmentObjects.append(a)
        apage = self.request.get('apage') and int(self.request.get('apage')) or 1
        apaginator = Paginator(assignmentObjects,10)

        userProfiles = UserProfile.all()
        appusers = []
        for up in userProfiles:
            u = {}
            u['key'] = str(up.key())
            u['fname'] = up.fname
            u['lname'] = up.lname
            u['email'] = up.email
            appusers.append(u)

        domain = GetAppsDomain()
        if domain is None:
            userMsg = UserMessages(guser=users.get_current_user().user_id(),msgtype="error")
            userMsg.message = "There is no apps domain specified in your settings.  Please update your the Application Settings."
            userMsg.put()
            self.redirect('/admin/settings')
        else:
            gpsvc = GProfileService(self.request.uri,domain)
            if not gpsvc.valid:
                gpurl = gpsvc.GetAuthenticationURL()
                output = "<script type='text/javascript'>window.location = '" + str(gpurl) + "'</script>"
                self.response.out.write(output)

            else:
                domainUsers = gpsvc.GetAllDomainUsers()
                #the contact service and Profile service use the same feed; so the same token will work
                gcsvc = GContactsService(self.request.uri,domain)
                contacts = gcsvc.GetAllContacts()
                #logging.info(gcsvc.GetGroupContacts('http://www.google.com/m8/feeds/groups/troyef%40mybrewing.com/base/6d413f850da80267'))
                groups = gcsvc.GetAllGroups()


                calsvc = GCalendarService(self.request.uri,domain)
                if not calsvc.valid:
                    calurl = calsvc.GetAuthenticationURL()
                    output = "<script type='text/javascript'>window.location = '" + str(calurl) + "'</script>"
                    self.response.out.write(output)
                else:
                    #logging.info(str(calsvc.GetAllCalendars()))
                    #SetCalendarId(None)
                    calendarid = GetCalendarId()
                    if calendarid is None:
                        newid = calsvc.CreateScormCloudCalendar()
                        SetCalendarId(newid)
                        calendarid = newid

                    timezone = GetCalendarTimezone()
                    if timezone is None:
                        timezone = calsvc.GetCalendarTimezone(calendarid)
                        SetCalendarTimezone(timezone)


                    self.template_values = {'courses':courses
                                                            ,"assignments" : apaginator.page(apage).object_list
                                                ,"apages" : apaginator.page_range
                                                            ,"amorepages" : (apaginator.num_pages > 1)
                                                ,"apage" : apage
                                                            ,"alistfocus": self.request.get('apage')
                                                            ,"uassignments" : uapaginator.page(uapage).object_list
                                                ,"uapages" : uapaginator.page_range
                                                            ,"uamorepages" : (uapaginator.num_pages > 1)
                                                ,"uapage" : uapage
                                                            ,'appusers':appusers
                                                            ,'domainusers':domainUsers
                                                            ,'contacts':contacts
                                                            ,'groups':groups
                                                            ,'calendarid':calendarid
                                                            ,'timezone':timezone
                                                            ,'utimezone':GetUserTimezone()
                                                            ,'courseid': courseid
                                                            ,'calendardescription':GetCalendarDescTemplate()
                                                            ,'emailbody':GetEmailTemplate()
                                                            ,'duetime':settings.duetime
                                                            }
                    page_display(self,"templates/assignform.html")

class DeleteAssignment(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def get(self,assignid):
        if assignid:
            DbDeleteAssignment(assignid)

            self.redirect('/registration/assign')
        else:
            self.error(403)

class AssignAction(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def post(self):
        domain = GetAppsDomain()

        assignment = Assignments()

        courseid = self.request.get('courseid')
        assignment.courseid = courseid
        assignment.createdbyuser = users.get_current_user().user_id()
        assignment.remindersubject = GetReminderSubjectTemplate()
        assignment.reminderbody = GetReminderTemplate()
        assignment.active = True

        if self.request.get('duedate'):
            duedate = datetime.datetime.strptime(self.request.get('duedate'), "%Y-%m-%d %H:%M")
            tz = timezone(GetUserTimezone())
            local_duedate = tz.localize(duedate)
            utcduedate = local_duedate.astimezone(pytz.utc)

            assignment.duedate = utcduedate

        addevent = self.request.get('addevent') == 'true'
        assignment.addevent = addevent
        if addevent:
            assigntitle = self.request.get('assigntitle')
            assigndesc = self.request.get('assigndesc')

            assignment.title = assigntitle
            assignment.description = assigndesc

        sendemail = self.request.get('sendemail') == 'true'
        assignment.sendemail = sendemail
        if sendemail:
            emailsubject = self.request.get('emailsubject')
            emailbody = self.request.get('emailbody')
            assignment.emailsubject = emailsubject
            assignment.emailbody = emailbody
        assignment.inviteecount = 0
        assignment.put()

        usercount = int(self.request.get('usercount'))
        selectedUsers = []
        for idx in range(0, usercount):
            if self.request.get('users[' + str(idx) + '][ctype]') == 'contactgroup':
                gcsvc = GContactsService(self.request.uri,domain)
                groupcontacts = gcsvc.GetGroupContacts(self.request.get('users[' + str(idx) + '][key]'))
                #logging.info('domaincontacts: ' + str(groupcontacts))
                for contact in groupcontacts:
                    u = {}
                    u['type'] = 'contactgroup'
                    u['key'] = contact['email']
                    u['fname'] = contact['firstname'] or contact['name']
                    u['lname'] = contact['lastname'] or contact['name']
                    selectedUsers.append(u)
            else:
                u = {}
                u['type'] = self.request.get('users[' + str(idx) + '][ctype]')
                u['key'] = self.request.get('users[' + str(idx) + '][key]')
                u['fname'] = self.request.get('users[' + str(idx) + '][fname]')
                u['lname'] = self.request.get('users[' + str(idx) + '][lname]')
                selectedUsers.append(u)

        #logging.info("selectedUsers: " + str(selectedUsers))
        assignResult = AddAssignmentUsers(assignment,selectedUsers,self.request.headers['Host'],self.request.uri)

        self.response.out.write(simplejson.dumps({'rsp':{'result':assignResult}}))

class AssignmentDetail(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def get(self,assignid):
        assign = GetAssignment(assignid)
        if assign.duedate:
            assign.duedate = AdjustTimeZone(assign.duedate)
        course = GetCourse(assign.courseid)
        reminders = GetReminders(assign)

        userregs = []
        incompleteRegs = []
        regs = GetAssignmentRegs(assign)
        if regs is not None:
            for reg in regs:
                ur = {}
                ur['compl'] = (reg.completion == "complete") and "Complete" or "Incomplete"
                ur['reg'] = reg
                ur['user'] = GetUserProfileFromUserId(Key(reg.userid))
                if ur['compl'] == "Incomplete":
                    userregs.append(ur)
                else:
                    incompleteRegs.append(ur)
        userregs.extend(incompleteRegs)


        userProfiles = UserProfile.all()
        appusers = []
        for up in userProfiles:
            u = {}
            u['key'] = str(up.key())
            u['fname'] = up.fname
            u['lname'] = up.lname
            u['email'] = up.email
            appusers.append(u)

        domain = GetAppsDomain()
        gpsvc = GProfileService(self.request.uri,domain)
        if not gpsvc.valid:
            gpurl = gsvc.GetAuthenticationURL()
            output = "<script type='text/javascript'>window.location = '" + str(gpurl) + "'</script>"
            self.response.out.write(output)

        else:
            domainUsers = gpsvc.GetAllDomainUsers()
            #the contact service and Profile service use the same feed; so the same token will work
            gcsvc = GContactsService(self.request.uri,domain)
            contacts = gcsvc.GetAllContacts()
            groups = gcsvc.GetAllGroups()

            self.template_values = {'assignment':assign
                                                            ,'course':course
                                                            ,'userregs':userregs
                                                            ,'appusers':appusers
                                                            ,'domainusers':domainUsers
                                                            ,'contacts':contacts
                                                            ,'groups':groups
                                                            ,'timezone':GetCalendarTimezone()
                                                            ,'utimezone':GetUserTimezone()
                                                            ,'enablereminders':GetEnableReminders()
                                                            ,'enableautoexpire':GetEnableAutoExpire()
                                                            ,'reminders':reminders
                                                    }
            page_display(self,"templates/assigndetail.html")

class AssignNewUsers(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def post(self):
        domain = GetAppsDomain()
        assignid = self.request.get('assignid')
        isactive = (self.request.get('active') == 'true')
        assignment = GetAssignment(assignid)

        usercount = int(self.request.get('usercount'))
        selectedUsers = []
        for idx in range(0, usercount):
            if self.request.get('users[' + str(idx) + '][ctype]') == 'contactgroup':
                gcsvc = GContactsService(self.request.uri,domain)
                groupcontacts = gcsvc.GetGroupContacts(self.request.get('users[' + str(idx) + '][key]'))
                #logging.info('domaincontacts: ' + str(groupcontacts))
                for contact in groupcontacts:
                    u = {}
                    u['type'] = 'contactgroup'
                    u['key'] = contact['email']
                    u['fname'] = contact['firstname'] or contact['name']
                    u['lname'] = contact['lastname'] or contact['name']
                    selectedUsers.append(u)
            else:
                u = {}
                u['type'] = self.request.get('users[' + str(idx) + '][ctype]')
                u['key'] = self.request.get('users[' + str(idx) + '][key]')
                u['fname'] = self.request.get('users[' + str(idx) + '][fname]')
                u['lname'] = self.request.get('users[' + str(idx) + '][lname]')
                selectedUsers.append(u)

        assignResult = AddAssignmentUsers(assignment,selectedUsers,self.request.headers['Host'],self.request.uri)

        self.response.out.write(simplejson.dumps({'rsp':{'result':assignResult}}))



class AssignActive(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def post(self):
        assignid = self.request.get('assignid')
        isactive = (self.request.get('active') == 'true')
        assign = GetAssignment(assignid)
        assign.active = not isactive
        assign.put();

        self.response.out.write('success')

class AssignAutoExpire(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def post(self):
        assignid = self.request.get('assignid')
        autoexpire = (self.request.get('autoexpire') == 'true')
        assign = GetAssignment(assignid)
        assign.autoexpire = autoexpire
        assign.put();

        self.response.out.write('success')


class AddReminder(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def post(self):
        assignid = self.request.get('assignid')
        assign = GetAssignment(assignid)

        rem = Reminders()
        rem.createdbyuser = users.get_current_user().user_id()
        rem.assignment = assign
        rem.population = self.request.get('pop')
        rem.timeunits = self.request.get('units')
        rem.timequantity = int(self.request.get('quant'))
        rem.sent = False
        rem.put();

        SetReminderTime(rem)

        self.response.out.write(simplejson.dumps({'rsp':{'result':'success','key':str(rem.key())}}))

class DeleteReminder(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def post(self):
        remkey = self.request.get('key')
        reminder = db.get(Key(remkey))
        db.delete(reminder)
        self.response.out.write(simplejson.dumps({'rsp':{'result':'success'}}))

class AssignUpdateEmail(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def post(self):
        assignid = self.request.get('assignid')
        subj = self.request.get('emailsubject')
        body = self.request.get('emailbody')

        remsubj = self.request.get('remsubject')
        rembody = self.request.get('rembody')

        assign = GetAssignment(assignid)
        if subj and body:
            assign.sendemail = True
            assign.emailbody = body
            assign.emailsubject = subj
        elif remsubj and rembody:
            assign.remindersubject = remsubj
            assign.reminderbody = rembody
        assign.put();

        self.response.out.write(simplejson.dumps({'rsp':{'result':'success'}}))

class AssignSendEmail(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def post(self):
        assignid = self.request.get('assignid')
        subj = self.request.get('emailsubject')
        body = self.request.get('emailbody')
        population = self.request.get('emailpop')


        assignment = GetAssignment(assignid)
        regs = GetAssignmentRegs(assignment,population)
        userObjects = []
        if regs is not None:
            for reg in regs:
                uo = {}
                up = GetUserProfileFromUserId(Key(reg.userid))
                uo['userprofile'] = up
                uo['regid'] = reg.regid
                userObjects.append(uo)

        assignResult = AssignSendEmails(userObjects,subj,body,assignment,self.request.headers['Host'])
        self.response.out.write(simplejson.dumps({'rsp':{'result':assignResult}}))


class AssignUpdateEvent(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def post(self):
        assignid = self.request.get('assignid')
        eventtitle = self.request.get('eventtitle')
        eventdesc = self.request.get('eventdesc')
        assignment = GetAssignment(assignid)

        try:
            calLaunchUrl = "http://" + self.request.headers['Host'] + "/assignment/launch/" + str(assignment.key())
            calDesc = BuildCalendarDesc(assignment.description,calLaunchUrl)

            ctz = timezone(GetCalendarTimezone())
            if assignment.duedate.tzinfo is None:
                utcduedate = pytz.utc.localize(assignment.duedate)
            else:
                utcduedate = assignment.duedate
            tzduedate = ctz.normalize(utcduedate.astimezone(ctz))

            csvc = GCalendarService(self.request.uri,GetAppsDomain())
            event = csvc.UpdateCalendarTrainingEvent(GetCalendarId(),tzduedate,None,eventtitle,calDesc,assignment.eventfeed)
            assignment.addevent = True
            assignment.eventfeed = event.GetSelfLink().href
            assignment.title = eventtitle
            assignment.description = eventdesc
            assignment.put()
            self.response.out.write(simplejson.dumps({'rsp':{'result':'success'}}))
        except Exception, e:
            logging.error(e)
            self.response.out.write(simplejson.dumps({'rsp':{'result':'error','errormsg':"There was a problem saving the event change. Please try again."}}))

class AssignDate(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def post(self):
        assignid = self.request.get('assignid')
        strduedate = self.request.get('duedate')
        assignment = GetAssignment(assignid)

        try:
            tz = timezone(GetUserTimezone())
            duedate = datetime.datetime.strptime(strduedate, "%Y-%m-%d %H:%M")
            local_duedate = tz.localize(duedate)
            utcduedate = local_duedate.astimezone(pytz.utc)

            if tz != GetCalendarTimezone():
                ctz = timezone(GetCalendarTimezone())
                duedate = ctz.normalize(utcduedate.astimezone(ctz))


            if assignment.addevent:
                csvc = GCalendarService(self.request.uri,GetAppsDomain())
                event = csvc.UpdateCalendarTrainingEvent(GetCalendarId(),duedate,None,None,None,assignment.eventfeed)
                assignment.eventfeed = event.GetSelfLink().href
            assignment.duedate = utcduedate
            assignment.put()
            reminders = GetReminders(assignment)
            if reminders is not None:
                for reminder in reminders:
                    SetReminderTime(reminder)

            self.response.out.write(simplejson.dumps({'rsp':{'result':'success','duedate':duedate.strftime("%b %d, %Y %H:%M")}}))
        except ValueError:
            self.response.out.write(simplejson.dumps({'rsp':{'result':'error','errormsg':"Please format your date as yyyy-mm-dd (eg. 2009-02-28) and use a 24 hour time format such as '09:02'."}}))
        except Exception, e:
            logging.error(e)
            self.response.out.write(simplejson.dumps({'rsp':{'result':'error','errormsg':"There was a problem saving the date change. Please try again."}}))


# *******************************************
# ****                  Report Views
#********************************************

class ReportageUrl(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def post(self):

        email = self.request.get('email') or None
        regid = self.request.get('regid') or None
        courseid = self.request.get('courseid') or None
        userid = self.request.get('userid') or None

        rsvc = cloud.get_reporting_service()

        if email is not None:
            userprofile = GetUserProfileFromEmail(email)
            ukey = str(userprofile.key())
            reporturl = rsvc.get_reportage_service_url() + '/Reportage/reportage.php?learnerId=' + ukey + '&appId=' + settings.appid
        elif regid is not None:
            reporturl = rsvc.get_reportage_service_url() + '/Reportage/reportage.php?registrationId=' + regid + '&appId=' + settings.appid
        elif courseid is not None:
            reporturl = rsvc.get_reportage_service_url() + '/Reportage/reportage.php?courseId=' + courseid + '&appId=' + settings.appid
        elif userid is not None:
            reporturl = rsvc.get_reportage_service_url() + '/Reportage/reportage.php?learnerId=' + userid + '&appId=' + settings.appid


        else:
            reporturl = rsvc.get_reportage_service_url() + '/Reportage/reportage.php?appId=' + settings.appid


        reportageUrl = rsvc.get_report_url(rsvc.get_reportage_auth('FULLNAV','true'),reporturl)
        #logging.info('reportUrl: ' + str(reportageUrl))

        self.response.out.write(str(reportageUrl))

class Reports(webapp.RequestHandler):
    @loginRequired
    @roleRequired("6")
    def get(self):
        regtype = self.request.get('regtype') or 'assign'
        poptype = self.request.get('pop') or 'all'
        datetype = self.request.get('date') or 'all'
        seltype = self.request.get('sel') or 'all'

        if poptype == "user":
            queryUser = users.get_current_user().user_id()
        else:
            queryUser = None

        regObjects = []
        if regtype == 'cat':
            regs = GetAssignmentRegs(None,seltype)
            if regs is not None:
                for reg in regs:
                    ur = {}
                    ur['groupfield'] = reg.coursetitle
                    ur['assignment'] = None
                    ur['reg'] = reg
                    ur['user'] = GetUserProfileFromUserId(Key(reg.userid))
                    regObjects.append(ur)


        else:
            assignments = GetAssignments(queryUser,datetype)
            if assignments is not None:
                for assignment in assignments:
                    regs = GetAssignmentRegs(assignment,seltype)
                    if regs is not None:
                        for reg in regs:
                            ur = {}
                            ur['groupfield'] = assignment
                            ur['assignment'] = assignment
                            ur['reg'] = reg
                            ur['user'] = GetUserProfileFromUserId(Key(reg.userid))
                            regObjects.append(ur)

        apage = self.request.get('apage') and int(self.request.get('apage')) or 1
        apaginator = Paginator(regObjects,20)

        rsvc = cloud.get_reporting_service()

        repAuth = rsvc.get_reportage_auth('NONAV','true')
        if repAuth is not None:
            reporturl = rsvc.get_reportage_service_url() + '/Reportage/reportage.php?appId=' + settings.appid
            reportageLaunchUrl = rsvc.get_report_url(repAuth,reporturl)
        else:
            reportageLaunchUrl = None

        #tags = TagSettings()
        #tags.AddTag('registration',settings.appsdomain)

        #widgetSettings = WidgetSettings(None,tags)
        #widgetSettings.divname = 'TrainingSummary'


        #reportageUrl = rsvc.GetWidgetUrl(repAuth,'allSummary',widgetSettings)
        #reportageDate = rsvc.GetReportageDate()

        self.template_values = {'regObjects':apaginator.page(apage).object_list
                                                        ,"apages" : apaginator.page_range
                                                        ,"amorepages" : (apaginator.num_pages > 1)
                                                ,"apage" : apage
                                                        ,'regcount':len(regObjects)
                                                        ,'regtype':regtype
                                                        ,'poptype':poptype
                                                        ,'datetype':datetype
                                                        ,'seltype':seltype
                                                        #,'reportageurl':reportageUrl
                                                        #,'reportagedate':reportageDate
                                                        ,'reportagelaunchurl':reportageLaunchUrl
                                                        }



        page_display(self,"templates/reports.html")
