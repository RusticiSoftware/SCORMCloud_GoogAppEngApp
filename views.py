#!/usr/bin/env python
# encoding: utf-8
"""
views.py

Created by brian.rogers on 2009-11-05.
Copyright (c) 2009 Rustici Software. All rights reserved.
"""

import cgi
import os
import datetime
import logging
import urllib

from xml.dom import minidom
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from scormcloud import UploadService
from scormcloud import CourseService
from scormcloud import RegistrationService
from scormcloud import ReportingService
from scormcloud import WidgetSettings
from google.appengine.ext.db import Key
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext.webapp import template
from google.appengine.api import images

from django.utils import simplejson
from django.core.paginator import Paginator, InvalidPage

from pytz import common_timezones



from models import *
from decorators import *
from modelutils import *
from viewutils import *

template.register_template_library('templatetags.seconds_to_duration')
template.register_template_library('templatetags.scormcloud_filters')

# Page handlers
class StartPage(webapp.RequestHandler):
	@loginRequired
	def get(self):
		regs = GetUserRegs(users.get_current_user().user_id())
	
		myregs = []
		if regs is not None:
			for reg in regs.fetch(5):
				myregs.append(reg)
		self.template_values = {'regs':myregs
							,'hasregs':(len(myregs) > 0)
							,'starttext':GetStartText()
							,'startlogo':GetStartLogo()
							}

		page_display(self,"templates/start.html")

class UserSettings(webapp.RequestHandler):
	@loginRequired
	def get(self):
		u = GetUserProfile()
		
		timezones = common_timezones
		
		self.template_values = {'userprofile':u
							,'timezones':timezones
							}
		page_display(self,"templates/usersettings.html")

class UserSettingsAction(webapp.RequestHandler):
	@loginRequired
	def post(self):
		u = GetUserProfile()
		u.fname = self.request.get('fname')
		u.lname = self.request.get('lname')
		u.timezone = self.request.get('timezone')
		u.put()
		timezones = common_timezones
		self.redirect('/usersettings')

class MyTraining(webapp.RequestHandler):
	@loginRequired
	def get(self):
		settings = GetSettings()
		up = GetUserProfile()
		regs = GetUserRegs(up.key())
		unfinishedRegs = []
		completedRegs = []
		
		if regs is not None:
			for reg in regs:
				regcourse = GetCourse(reg.courseid)
				reg.descriptiontext = regcourse.descriptiontext
				if reg.lastaccess:
					reg.lastaccess = AdjustTimeZone(reg.lastaccess)
				reg.duration = regcourse.duration
				reg.moreinfo = (reg.duration != 'unknown' and reg.descriptiontext is not None)
				#reg.active = True
				if reg.assignment is not None:
					reg.active = reg.assignment.active
					if reg.assignment.duedate:
						reg.overdue = reg.assignment.duedate < datetime.datetime.utcnow() and 'overdue' or ''
						reg.duedate = AdjustTimeZone(reg.assignment.duedate)
					else:
						reg.duedate = None
				if reg.completion != "complete" and reg.active:
					unfinishedRegs.append(reg)
				else:
					completedRegs.append(reg)

		courses = GetCatalogCoursesDateDesc()
		allcourses = []
		for course in courses:
			c = {}
			#c['creatoremail'] = GetUserEmailFromGuser(course.createdbyuser)
			c['userreg'] = GetUserCourseReg(users.get_current_user().user_id(), course.courseid)
			c['course'] = course
			allcourses.append(c)
		
		actpage = self.request.get('actpage') and int(self.request.get('actpage')) or 1
		actpaginator = Paginator(unfinishedRegs,5)
		inactpage = self.request.get('inactpage') and int(self.request.get('inactpage')) or 1
		inactpaginator = Paginator(completedRegs,5)
		
		cpage = self.request.get('cpage') and int(self.request.get('cpage')) or 1
		cpaginator = Paginator(allcourses,10)
		
		self.template_values = {'unfinishedregs': actpaginator.page(actpage).object_list
        						,"actpages" : actpaginator.page_range
								,"actmorepages" : (actpaginator.num_pages > 1)
								,"actpage" : actpage
								,'completedregs': inactpaginator.page(inactpage).object_list
        						,"inactpages" : inactpaginator.page_range
								,"inactmorepages" : (inactpaginator.num_pages > 1)
								,"inactpage" : inactpage
								,'courses':cpaginator.page(cpage).object_list
					            ,"cpages" : cpaginator.page_range
								,"cmorepages" : (cpaginator.num_pages > 1)
								,"cpage" : cpage
								,'regcount':len(unfinishedRegs) + len(completedRegs)
								}

		page_display(self,"templates/mytraining.html")



class CourseCatalog(webapp.RequestHandler):
	@loginRequired
	def get(self,page=1):
		try:
			page = int(page)
		except:
			page = 1
		courses = Course.all()
		allcourses = []
		for course in courses:
			course.tagstring = GetCourseTags(course.courseid)
			course.creatoremail = GetUserEmailFromGuser(course.createdbyuser)
			course.usercanreg = UserCanRegister(users.get_current_user().user_id(), course.courseid)
			course.regcount = GetCourseRegCount(course.courseid)
			allcourses.append(course)

		paginator = Paginator(allcourses,3)
		#if page>=paginator:
		#	page = paginator

		self.template_values = {
            "courses" : paginator.page(page).object_list
            ,"pages" : paginator.page_range
			,"morepages" : (paginator.num_pages > 1)
            ,"page" : page
		}

		page_display(self,"templates/courselist.html")
		

class CourseDetail(webapp.RequestHandler):
	@loginRequired
	def get(self, courseid):
		settings = GetSettings()
		#get the course title
		course = GetCourse(courseid)
		
		
		reg = GetUserCourseReg(users.get_current_user().user_id(), courseid)
		#reg.active = True
		#if reg.assignment is not None:
		#	reg.active = reg.assignment.active
		#	reg.duedate = reg.assignment.duedate
		
		#set the template values
		self.template_values = {'course': course
							,'tags':GetCourseTags(courseid)
							,'reg':reg
							}

		page_display(self,"templates/coursedetail.html")


class PreviewCourse(webapp.RequestHandler):
	@loginRequired
	def get(self,cid):
		redirecturl = self.request.get('redirecturl')
		if redirecturl is None:
			redirecturl = "http://" + self.request.headers['Host'] + "/course/detail/" + cid
		settings = GetSettings()
		csvc = CourseService(settings.appid,settings.secretkey,settings.servicehost)
		self.response.out.write('<script language="javascript">window.document.location.href="'+csvc.GetPreviewLink(cid,redirecturl)+'";</script>')



class LaunchCourse(webapp.RequestHandler):
	#@loginRequired
	def get(self,regid):
		redirecturl = "http://" + self.request.headers['Host'] + "/course/exit"
		UpdateRegAccessDate(regid)
		settings = GetSettings()
		
		regsvc = RegistrationService(settings.appid,settings.secretkey,settings.servicehost)
									
		self.redirect(regsvc.GetLaunchLink(regid, redirecturl,GetCourseTags(GetRegCourseId(regid),','),GetLearnerTags(GetRegUserId(regid),','),GetRegistrationTags(regid,',')))

class NonUserLaunch(webapp.RequestHandler):
	def post(self):
		assignid = self.request.get('assignid')
		email = self.request.get('useremail')

		ups = GetUserProfileFromEmail(email)
		notrainingmsg = None
		if ups is not None:
			assignment = GetAssignment(assignid)
			regid = GetRegIdFromUserAssignment(str(ups.key()),assignment)
			if regid is not None:
				UpdateRegAccessDate(regid)
				settings = GetSettings()
				redirecturl = "http://" + self.request.headers['Host'] + "/course/exit"
				regsvc = RegistrationService(settings.appid,settings.secretkey,settings.servicehost)

				self.redirect(regsvc.GetLaunchLink(regid, redirecturl,GetCourseTags(GetRegCourseId(regid),','),GetLearnerTags(GetRegUserId(regid),','),GetRegistrationTags(regid,',')))
			else:
				notrainingmsg = "The email entered is not associated with the assignment being launched. Please check the email you entered."
		else:
			notrainingmsg = "The email entered was not found in the training system.  Please check the email you entered."
		if notrainingmsg is not None:
			loginurl = users.create_login_url(self.request.uri)
			self.template_values = {'loginurl': loginurl
									,'assignid': assignid
									,'message': notrainingmsg
									}
			page_display(self,"templates/nonuserlaunch.html")
			
class CheckUserEmail(webapp.RequestHandler):
	def get(self,email):
		ups = GetUserProfileFromEmail(user.email())
		if ups is None:
			self.response.out.write("None")
		else:
			logging.info("key: " + str(ups.key()))
			self.response.out.write(str(ups.key()))
			
class InactiveCourse(webapp.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if not user:
			self.template_values = {}
								
			page_display(self,"templates/inactiveCourse_nonu.html")
		else:
			self.template_values = {}
								
			page_display(self,"templates/inactiveCourse.html")
		

class LaunchAssignment(webapp.RequestHandler):
	def get(self,assignid):
		assignment = GetAssignment(assignid)
		if assignment is None:
			msg = UserMessages(guser=user.user_id(),msgtype="warning")
			msg.message = "The training you attempted to launch is no longer available."
			msg.put()
			self.redirect("/")
		else:
			assignactive = IsAssignmentActive(assignid)
			user = users.get_current_user()
		

			if not user:
				loginurl = users.create_login_url(self.request.uri)
		
				self.template_values = {'loginurl': loginurl
										,'assignid': assignid
										}
			
				if not assignactive:
					page_display(self,"templates/inactivecourse_nonuser.html")
				else:
					page_display(self,"templates/nonuserlaunch.html")
			else:
				if not assignactive:
					msg = UserMessages(guser=user.user_id(),msgtype="warning")
					msg.message = "The training you attempted to launch, '" + GetCourseTitle(assignment.courseid) + "' , is no longer available."
					msg.put()
					self.redirect("/")
				else:
					ups = GetUserProfileFromGuser(user.user_id())
					if ups is None:
						ups = GetUserProfileFromEmail(user.email())
			
					regid = GetRegIdFromUserAssignment(str(ups.key()),assignment)
					if regid is not None:
						UpdateRegAccessDate(regid)
						settings = GetSettings()
						redirecturl = "http://" + self.request.headers['Host'] + "/course/exit"
						regsvc = RegistrationService(settings.appid,settings.secretkey,settings.servicehost)

						self.redirect(regsvc.GetLaunchLink(regid, redirecturl,GetCourseTags(GetRegCourseId(regid),','),GetLearnerTags(GetRegUserId(regid),','),GetRegistrationTags(regid,',')))
					else:
						msg = UserMessages(guser=user.user_id(),msgtype="warning")
						msg.message = "You have not been assigned the training you attempted to launch, '" + GetCourseTitle(assignment.courseid) + "'."
						msg.put()
						self.redirect("/")

class NewRegLaunchCourse(webapp.RequestHandler):
	@loginRequired
	def get(self,courseid):
		if courseid:
			regid = CreateNewRegistration(GetUserKeyFromGuser(users.get_current_user().user_id()), courseid, None)
		UpdateRegAccessDate(regid)
		settings = GetSettings()
		redirecturl = "http://" + self.request.headers['Host'] + "/course/exit"
		regsvc = RegistrationService(settings.appid,settings.secretkey,settings.servicehost)
		
		self.redirect(regsvc.GetLaunchLink(regid, redirecturl))

class CourseExit(webapp.RequestHandler):
	def get(self):
		
		settings = GetSettings()
		#get the reg results from the cloud
		regsvc = RegistrationService(settings.appid,settings.secretkey,settings.servicehost)
		data = regsvc.GetRegistrationResults(self.request.get('regid'),'course')
		xmldoc = minidom.parseString(data)
		complete = xmldoc.getElementsByTagName("complete")[0].childNodes[0].nodeValue
		success = xmldoc.getElementsByTagName("success")[0].childNodes[0].nodeValue
		totaltime = xmldoc.getElementsByTagName("totaltime")[0].childNodes[0].nodeValue
		score = xmldoc.getElementsByTagName("score")[0].childNodes[0].nodeValue
		#then update the local registration object
		regs = Registration.gql("WHERE regid = :1", self.request.get('regid'))
		for reg in regs:
			reg.completion = complete
			reg.satisfaction = success
			reg.timespent = totaltime
			reg.score = score
			reg.put()
		
		redirecturl = "/mytraining"
		self.redirect(redirecturl)

class UserGadget(webapp.RequestHandler):
	def get(self):
		user = users.get_current_user()
		parent = self.request.get('parent') or self.request.uri
		container = self.request.get('container') or "ig"
		if not user:
			#gadgetlogin
			regs = None
			login_url = users.create_login_url(parent)
			loggedin = False
		else:
			up = GetUserProfile()
			regs = GetActiveUserRegs(up.key())
			login_url = users.create_logout_url(users.create_login_url(parent))
			loggedin = True

		self.template_values = {'regs': regs
								,'loggedin':loggedin
								,'loginurl':login_url
								,'container':container
								}

		page_display(self,"templates/usergadget.html")

		
class ApiAction(webapp.RequestHandler):
	@loginRequired
	def post(self):
		func = None
		action = self.request.get('action')
		if action:
			if action[0] == '_':
				self.error(403) # access denied
				return
			else:
				if action == 'delreg':
					self.response.out.write('delreg')
					#result = DeleteRegistration(self.request.get('regid'))
					self.response.out.write(simplejson.dumps(['rsp',{'result':'success'}]))
		
class Avatar (webapp.RequestHandler):
	def get(self):
		#self.response.out.write("looking for :" + self.request.get("guser"))
		if self.request.get('guser'):
			userprofiles = db.GqlQuery("SELECT * FROM UserProfile WHERE email = :1", self.request.get("guser"))
			#self.response.out.write(len(list(userprofiles)))
			for up in userprofiles:
				if(up.userimage!=None):
					self.response.headers['Content-Type'] = "image/jpg"
					self.response.out.write(up.userimage)
				else:
					self.response.out.write("No image")
		elif self.request.get('default'):
			settings = Settings.all()
			self.response.headers['Content-Type'] = "image/jpg"
			self.response.out.write(settings[0].defaultavatar)

class CourseSearch(webapp.RequestHandler):
	@loginRequired
	def post(self,page=1):
		searchText = self.request.get('searchtext')	
		try:
			page = int(page)
		except:
			page = 1
		courses = Course.all()
		allcourses = []
		for course in courses:
			if searchText in course.tags:
				course.tagstring = GetCourseTags(course.courseid)
				course.creatoremail = GetUserEmailFromGuser(course.createdbyuser)
				course.usercanreg = UserCanRegister(users.get_current_user().user_id(), course.courseid)
				course.regcount = GetCourseRegCount(course.courseid)
				allcourses.append(course)

		paginator = Paginator(allcourses,3)
		#if page>=paginator:
		#	page = paginator

		self.template_values = {
            "courses" : paginator.page(page).object_list
            ,"pages" : paginator.page_range
            ,"page" : page
		}

		page_display(self,"templates/coursesearch.html")

class RegReport(webapp.RequestHandler):
	@loginRequired
	def get(self,regid):
		regs = db.GqlQuery("SELECT * FROM Registration WHERE regid = :1", regid)
		settings = GetSettings()
		#create the scorm cloud registration
		regsvc = RegistrationService(settings.appid,settings.secretkey,settings.servicehost)

		data = regsvc.GetRegistrationResults(regid, 'full')

		self.template_values = {'coursetitle': GetCourseTitle(regs[0].courseid)
							,'regxml': data
							,'regid': regid
							}

		page_display(self,"templates/regreport.html")

class LaunchHistoryReport(webapp.RequestHandler):
	@loginRequired
	def get(self,regid):
		settings = GetSettings()
		regs = db.GqlQuery("SELECT * FROM Registration WHERE regid = :1", regid)
		#create the scorm cloud registration
		regsvc = RegistrationService(settings.appid,settings.secretkey,settings.servicehost)
		data = regsvc.GetLaunchHistory(regid)

		self.template_values = {'coursetitle': GetCourseTitle(regs[0].courseid)
							,'regxml': data
							,'regid': regid
							}

		page_display(self,"templates/lhreport.html")
		
		
class RemoveMessage(webapp.RequestHandler):
	@loginRequired
	def post(self,messagekey):
		usermessage = db.get(Key(messagekey))
		usermessage.delete()
		self.response.out.write('success')
