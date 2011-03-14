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

if GetEnableReminders():

	# application setup - add new pages here...	
	logging.getLogger().setLevel(logging.DEBUG)



	logging.info("Kicking off the scheduled reminders process.")

	sender = GetReminderSender()
	
	if sender is None:
		AddAdminMessages("warning","Reminders are enabled but there is no sender email address specified.  Please provide a sender email on the App Settings Page.")
	else:
		totalsent = 0
		reminders = GetSendableReminders()
		if reminders is not None:
			
	
			for reminder in reminders:
				assignment = reminder.assignment
				if assignment.remindersubject is None or assignment.remindersubject == '' or assignment.reminderbody is None or assignment.reminderbody == '':
					assigner = GetUserProfileFromGuser(assignment.createdbyuser.guser)
					userMsg = UserMessages(assigner.guser,"warning")
					userMsg.message = "Reminders have been created but no email subject and/or body provided for the assignment due " + AdjustTimeZone(assignment.duedate,ptimezone=assigner.timezone).strftime("%b %d, %Y %H:%M")
					userMsg.message +=	". The course title is '" + GetCourseTitle(assignment.courseid) + "'."
					userMsg.put()
				else:
					regs = GetAssignmentRegs(assignment,population=reminder.population)
					for reg in regs:
						up = GetUserProfileFromUserId(Key(reg.userid))
			
						message = mail.EmailMessage()
						message.sender = sender
						message.to = FormatEmailAddress(up)
						message.subject = assignment.remindersubject
						launchurl = "http://" + GetAppServerHost() + "/registration/launch/" + reg.regid
		
						msgBuilder = EmailBodyBuilder(strBody=assignment.reminderbody,launchurl=launchurl,fname=up.fname,lname=up.lname)
						if assignment.duedate:
							dd = AdjustTimeZone(assignment.duedate,ptimezone=up.timezone)
							msgBuilder.duedate = dd.strftime("%b %d, %Y %H:%M")
						message.body = msgBuilder.GetTextEmailBody()
						#message.html = msgBuilder.GetHTMLEmailBody()
						message.send()
						totalsent = totalsent + 1
					reminder.sent = True
					reminder.put()
					
	
		logging.info("Sending " + str(totalsent) + " reminders.")				
	logging.info("Ending the scheduled reminders process.")

