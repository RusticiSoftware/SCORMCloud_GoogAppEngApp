import cgi
import os
import datetime
import logging

from google.appengine.ext import db
from google.appengine.ext.db import Key
from google.appengine.api import users
from google.appengine.api import images
from google.appengine.api import memcache
from google.appengine.api import mail

import pytz
from pytz import timezone

from models import *
from modelutils import *
from scormcloud import *
from gdatautils import *
from viewutils import *


LAUNCH_URL = "[launchurl]"
FIRST_NAME = "[fname]"
LAST_NAME = "[lname]"
MY_NAME = "[myname]"
DUE_DATE = "[duedate]"

class EmailBodyBuilder(object):
	
	def __init__(self,strBody=None,launchurl='',fname='',lname='',myname='',duedate=''):
		if strBody is None:
			self.body = GetEmailTemplate()
		else:
			self.body = strBody or ""
		self.launchurl = launchurl or ""
		self.fname = fname or ""
		self.lname = lname or ""
		self.myname = myname or ""
		self.duedate = duedate or ""
	
	def GetTextEmailBody(self):
		body = self.body
		body = body.replace(LAUNCH_URL,self.launchurl)
		body = body.replace(FIRST_NAME,self.fname)
		body = body.replace(LAST_NAME,self.lname)
		body = body.replace(MY_NAME,self.myname)
		body = body.replace(DUE_DATE,self.duedate)
		return body
		
	def GetHTMLEmailBody(self):
		body = self.body
		body = body.replace(LAUNCH_URL,"<a href='" + self.launchurl + "'>Launch Training</a>")
		body = body.replace(FIRST_NAME,self.fname)
		body = body.replace(LAST_NAME,self.lname)
		body = body.replace(MY_NAME,self.myname)
		body = body.replace(DUE_DATE,self.duedate)
		return body

def GetEmailTemplate():
	return """Dear [fname],
You have been assigned to take some training.
Click the Launch link below to start your training.

[launchurl]
	
Thanks, 
[myname]
"""



def GetCalendarDescTemplate():
	return """Please take the following training.
	
[launchurl]
	
"""

def GetReminderSubjectTemplate():
	return "Reminder: You have training due."

def GetReminderTemplate():
	return """Dear [fname],
You have been assigned to take some training and the duedate is coming up.  Please complete your training before [duedate].
Click the Launch link below to start your training.

[launchurl]
	
Thanks, 
[myname]
"""

def BuildCalendarDesc(description=None,launchurl=None):
	if description is None:
		description = GetCalendarDescTemplate()
	description = description.replace(LAUNCH_URL,"<a href='" + launchurl + "'>Launch Training</a>")
	return description

def FormatEmailAddress(userprofile):
	if userprofile.fname and userprofile.lname:
		return userprofile.fname + ' ' + userprofile.lname + ' <' + userprofile.email + '>'
	else:
		return userprofile.email

def AddAssignmentUsers(assignment,selectedUsers,serverhost,requestUri):
	settings = GetSettings()
	domain = GetAppsDomain()
	
	invitees = []
	failedInvitees = []
	failedemails = []
	for su in selectedUsers:
		up = None
		if su['type'] == 'appuser':
			up = GetUserProfileFromUserId(Key(su['key']))
		else:
			up = GetUserProfileFromEmail(su['key'])
			if up is None:
				up = UserProfile()
				up.fname = su['fname']
				up.lname = su['lname']
				up.email = su['key']
				up.accesslevel = "0"
				if settings.defaultavatar:
					up.userimage = settings.defaultavatar
				up.put()
		
		#create registration
		try:
			#logging.info ('adding reg for ' + up.email)			
			regid = CreateNewRegistration(up.key(), assignment.courseid, assignment.key())
			invitees.append(up.email)
		except ScormCloudError, instance:
			logging.error("SC Error creating Registation: " + instance.msg)
			failedInvitees.append(up.email)
		except Exception, e:
			logging.error("Error creating Registation: " + str(e.args))
			failedInvitees.append(up.email)
		
		try:
			if assignment.sendemail and len(assignment.emailbody) > 0 and len(assignment.emailsubject) > 0:
				#send an email to the user
				currentUserProf = GetUserProfileFromGuser(users.get_current_user().user_id())
				message = mail.EmailMessage()
				message.sender = FormatEmailAddress(currentUserProf)
				message.to = FormatEmailAddress(up)
				message.subject = assignment.emailsubject
				launchurl = "http://" + serverhost + "/registration/launch/" + regid
			
				msgBuilder = EmailBodyBuilder(strBody=assignment.emailbody,launchurl=launchurl,fname=up.fname,lname=up.lname,myname=currentUserProf.fname + ' ' + currentUserProf.lname)
				if assignment.duedate:
					dd = AdjustTimeZone(assignment.duedate)
					msgBuilder.duedate = dd.strftime("%b %d, %Y %H:%M")
				message.body = msgBuilder.GetTextEmailBody()
				message.html = msgBuilder.GetHTMLEmailBody()
				message.send()
				
	
		except Exception, e:
			logging.error("Error sending assignment email to " + up.email + ": " + str(e.args))
			failedemails.append(up.email)
	
	assignment.inviteecount += len(invitees)
	assignment.put()
	
	failedevent = False
	if assignment.addevent:
		try:
			ctz = timezone(GetCalendarTimezone())
			if assignment.duedate.tzinfo is None:
				utcduedate = pytz.utc.localize(assignment.duedate)
			else:
				utcduedate = assignment.duedate
			tzduedate = ctz.normalize(utcduedate.astimezone(ctz))
			
			calLaunchUrl = "http://" + serverhost + "/assignment/launch/" + str(assignment.key())
			calDesc = BuildCalendarDesc(assignment.description,calLaunchUrl)
			csvc = GCalendarService(requestUri,domain)
			event = csvc.UpdateCalendarTrainingEvent(GetCalendarId(),tzduedate,invitees,assignment.title,calDesc,assignment.eventfeed)
			assignment.eventfeed = event.GetSelfLink().href
			assignment.put()
		except Exception, e:
			failedevent = True
			logging.error("Error creating/updating calendar event for assignment " + str(assignment.key()) + ". : " + str(e.args))
	
	errorMsg = ""
	if failedevent:
		errorMsg += "<p>The Calendar Event creation/update was not successful.</p><br/>"

	if len(failedInvitees) > 0:
		errorMsg += "<p>Registrations for the following invitees could not be created.  Check for available registrations on your account.</p><ul>"
		for email in failedInvitees:
			errorMsg += "<li>" + email + "</li>"
		errorMsg += "</ul>"
	if len(failedemails) > 0:
		errorMsg += "<p>Emails to the following invitees could not be sent.</p><ul>";
		for email in failedemails:
			errorMsg += "<li>" + email + "</li>"
		errorMsg += "</ul>"
	
	userMsg = None
	if len(errorMsg) > 0:
		userMsg = UserMessages(guser=users.get_current_user().user_id(),msgtype="error")
		userMsg.message = errorMsg
		userMsg.put()
	
	if len(invitees) > 0:
		return "success"
	else:
		return "error"


def AssignSendEmails(userobjects,subj,body,assignment,serverhost):
	failedemails = []
	for userobj in userobjects:
		up = userobj['userprofile']
		regid = userobj['regid']
		try:
			currentUserProf = GetUserProfileFromGuser(users.get_current_user().user_id())
			message = mail.EmailMessage()
			message.sender = FormatEmailAddress(currentUserProf)
			message.to = FormatEmailAddress(up)
			message.subject = subj
			if regid is not None:
				launchurl = "http://" + serverhost + "/registration/launch/" + regid
			else:
				launchurl = ''

			msgBuilder = EmailBodyBuilder(strBody=assignment.emailbody,launchurl=launchurl,fname=up.fname,lname=up.lname,myname=currentUserProf.fname + ' ' + currentUserProf.lname)
			if assignment.duedate:
				msgBuilder.duedate = assignment.duedate.strftime("%b %d, %Y %H:%M")
			message.body = msgBuilder.GetTextEmailBody()
			#message.html = msgBuilder.GetHTMLEmailBody()
			message.send()
			
		except Exception, e:
			logging.error("Error sending email to " + up.email + ": " + str(e.args))
			failedemails.append(up.email)
		
	errorMsg = ""
	if len(failedemails) > 0:
		errorMsg += "<p>Emails sent to the following were not successful.</p><ul>";
		for email in failedemails:
			errorMsg += "<li>" + email + "</li>"
		errorMsg += "</ul>"

	userMsg = None
	if len(errorMsg) > 0:
		userMsg = UserMessages(guser=users.get_current_user().user_id(),msgtype="error")
		userMsg.message = errorMsg
		userMsg.put()
	else:
		userMsg = UserMessages(guser=users.get_current_user().user_id(),msgtype="info")
		if len(userobjects) == 1:
			userMsg.message = "1 email was sent successfully."
		else:
			userMsg.message = str(len(userobjects)) + " emails were sent successfully."
		userMsg.put()

	if len(failedemails) > 0:
		return "success"
	else:
		return "error"
