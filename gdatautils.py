
import getopt
import getpass
import sys
import datetime
import logging
from xml.dom import minidom

from google.appengine.api import users
from google.appengine.ext import webapp
import atom.url
import gdata
import gdata.service
import gdata.alt.appengine
import gdata.contacts
import gdata.contacts.service
from gdata import calendar


import gdata.auth
import gdata.calendar
from gdata.calendar import service as calendar_service

class GClient(object):
	
	def __init__(self):
		self.client = gdata.service.GDataService()
		gdata.alt.appengine.run_on_appengine(client)
		

class GProfileService(object):

	def __init__(self, uri,domain):
		self.uri = uri
		self.domain = domain
		self.client = gdata.contacts.service.ContactsService(contact_list=domain,additional_headers={'GData-Version':'3.0'})
		gdata.alt.appengine.run_on_appengine(self.client)
		self.valid = True
		try:
			self.client.AuthSubTokenInfo()
		except:
			self.valid = False
		
		if not self.valid:
			session_token = None
			# Find the AuthSub token and upgrade it to a session token.
			try:
				auth_token = gdata.auth.extract_auth_sub_token_from_url(uri)
				if auth_token:
		    		# Upgrade the single-use AuthSub token to a multi-use session token.
					session_token = self.client.upgrade_to_session_token(auth_token)
				if session_token and users.get_current_user():
					# If there is a current user, store the token in the datastore and
					# associate it with the current user. Since we told the client to
					# run_on_appengine, the add_token call will automatically store the
					# session token if there is a current_user.
					self.client.token_store.add_token(session_token)
					self.valid = True
				else:
					self.valid = False
			except:
				self.valid = False
		
		
	def GetAuthenticationURL(self):
		return self.client.GenerateAuthSubURL(self.uri,'http://www.google.com/m8/feeds/',domain=self.domain,secure=False,session=True)
	
	def GetAllDomainUsers(self):
		try:
			feed = self.client.GetProfilesFeed()
			domainUsers = {}
			for entry in feed.entry:
				du = GetContactUserInfo(entry)
				if 'email' in du:
					domainUsers[du['email']] = du
			return domainUsers
		except gdata.service.RequestError, request_error:
			logging.info('GetProfilesFeed failed.  Likely due to not being logged in. user: ' + users.get_current_user().nickname())
			return None

		
		

	def GetDomainUserByUsername(self,username):
		try:
			uri = self.client.GetFeedUri('profiles')+'/'+username
			#logging.info('uri:  ' + uri)
			entry = self.client.GetProfile(uri)
			return DomainUser(entry)
		except gdata.service.RequestError:
			logging.info('GetProfilesFeed failed.  Likely due to not being logged in. user: ' + users.get_current_user().nickname())
			return None
			
			
class GContactsService(object):

	def __init__(self, uri,domain):
		self.uri = uri
		self.domain = domain
		self.client = gdata.contacts.service.ContactsService(additional_headers={'GData-Version':'3.0'})
		gdata.alt.appengine.run_on_appengine(self.client)
		self.valid = True
		try:
			self.client.AuthSubTokenInfo()
		except:
			self.valid = False
		
		if not self.valid:
			session_token = None
			# Find the AuthSub token and upgrade it to a session token.
			try:
				auth_token = gdata.auth.extract_auth_sub_token_from_url(uri)
				if auth_token:
		    		# Upgrade the single-use AuthSub token to a multi-use session token.
					session_token = self.client.upgrade_to_session_token(auth_token)
				if session_token and users.get_current_user():
					# If there is a current user, store the token in the datastore and
					# associate it with the current user. Since we told the client to
					# run_on_appengine, the add_token call will automatically store the
					# session token if there is a current_user.
					self.client.token_store.add_token(session_token)
					self.valid = True
				else:
					self.valid = False
			except:
				self.valid = False
				
	def GetAuthenticationURL(self):
		return self.client.GenerateAuthSubURL(self.uri,'http://www.google.com/m8/feeds/',domain=self.domain,secure=False,session=True)
	
	def GetAllContacts(self):
		try:
			feed = self.client.GetContactsFeed()
			domainUsers = {}
			for entry in feed.entry:
				du = GetContactUserInfo(entry)
				if 'email' in du:
					domainUsers[du['email']] = du
			if len(domainUsers) > 0:
				return domainUsers
			else:
				return None
			
		except gdata.service.RequestError, request_error:
			logging.info('GetAllContacts failed.  Likely due to not being logged in. user: ' + users.get_current_user().nickname())
			return None
			
	def GetGroupContacts(self,groupid):
		try:
			query = gdata.contacts.service.ContactsQuery()
			query.group = groupid
			feed = self.client.GetContactsFeed(query.ToUri())
			#logging.info('groupcontactsfeed' + str(feed))
			contacts = []
			for entry in feed.entry:
				contacts.append(GetContactUserInfo(entry))
			return contacts
		except gdata.service.RequestError, request_error:
			logging.info('GetGroupContacts failed.  Likely due to not being logged in. user: ' + users.get_current_user().nickname())
			return None
			
	def GetAllGroups(self):
		try:
			feed = self.client.GetGroupsFeed()
			#logging.info('groupfeed' + str(feed))
			groups = []
			for entry in feed.entry:
				xmldoc = minidom.parseString(str(entry))
				systemgrps = xmldoc.getElementsByTagNameNS('http://schemas.google.com/contact/2008','systemGroup')
				if len(systemgrps) == 0:
					group = {}
					group['name'] = entry.title.text
					group['id'] = entry.id.text
					groups.append(group)
			if len(groups) > 0:
				return groups
			else:
				return None
		except gdata.service.RequestError, request_error:
			logging.info('GetAllGroups failed.  Likely due to not being logged in. user: ' + users.get_current_user().nickname())
			return None

def GetContactUserInfo(entry):
	contact = {}
	contact['name'] = entry.title.text
	for email in entry.email:
	      if email.primary == 'true':
	        contact['email'] = email.address
	contact['firstname'] = None
	contact['lastname'] = None
	xmldoc = minidom.parseString(str(entry))
	name = xmldoc.getElementsByTagNameNS('http://schemas.google.com/g/2005','name')
	if name.length > 0:
		contact['firstname'] = name[0].getElementsByTagNameNS('http://schemas.google.com/g/2005','givenName')[0].childNodes[0].nodeValue
		contact['lastname'] = name[0].getElementsByTagNameNS('http://schemas.google.com/g/2005','familyName')[0].childNodes[0].nodeValue
	return contact

class GCalendarService(object):

	def __init__(self,uri,domain):
		self.uri = uri
		self.domain = domain
		headers = {'X-Redirect-Calendar-Shard': 'true','GData-Version':'2'}
		self.client = calendar_service.CalendarService(additional_headers=headers)
		gdata.alt.appengine.run_on_appengine(self.client)
		self.valid = True
		try:
			self.client.AuthSubTokenInfo()
		except:
			self.valid = False
		
		if not self.valid:
			session_token = None
			# Find the AuthSub token and upgrade it to a session token.
			try:
				auth_token = gdata.auth.extract_auth_sub_token_from_url(uri)
				if auth_token:
		    		# Upgrade the single-use AuthSub token to a multi-use session token.
					session_token = self.client.upgrade_to_session_token(auth_token)
				if session_token and users.get_current_user():
					# If there is a current user, store the token in the datastore and
					# associate it with the current user. Since we told the client to
					# run_on_appengine, the add_token call will automatically store the
					# session token if there is a current_user.
					self.client.token_store.add_token(session_token)
					self.valid = True
				else:
					self.valid = False
			except:
				self.valid = False
		
	def GetAuthenticationURL(self):
		return self.client.GenerateAuthSubURL(self.uri,['https://www.google.com/calendar/feeds/','http://www.google.com/calendar/feeds/'],domain=self.domain,secure=False,session=True)
	
	def GetCalendarTimezone(self,calendarId=None):
		if calendarId is not None:
			uri = 'http://www.google.com/calendar/feeds/'+ calendarId + '/private/full'
			calFeed = self.client.GetOwnCalendarsFeed(uri)
		else:
			calFeed = self.client.GetOwnCalendarsFeed()
		xmlFeed = minidom.parseString(str(calFeed))
		timezoneNode = xmlFeed.getElementsByTagNameNS('http://schemas.google.com/gCal/2005','timezone')[0]
		timezone = timezoneNode.attributes["value"].value
		return timezone
	
	def CreateScormCloudCalendar(self):
		timezone = self.GetCalendarTimezone()
		
		calendar = gdata.calendar.CalendarListEntry()
		calendar.title = atom.Title(text='SCORM Cloud Training')
		calendar.summary = atom.Summary(text='This calendar contains training events from the SCORM Cloud Application in Google Apps.')
		#calendar.where = gdata.calendar.Where(value_string='Oakland')
		calendar.color = gdata.calendar.Color(value='#182C57')
		calendar.timezone = gdata.calendar.Timezone(value=str(timezone))
		calendar.hidden = gdata.calendar.Hidden(value='false')

		new_calendar = self.client.InsertCalendar(new_calendar=calendar)
		newId = new_calendar.id.text.partition("/calendars/")[2]
		return newId
	
	def UpdateCalendarOwnership(self,calid,accesslevel,useremail):
		
		if accesslevel == 'remove':
			try:
				logging.info('Removeing calendar rights for ' + useremail)
				aclEntryUri = "http://www.google.com/calendar/feeds/%s/acl/full/user:%s" % (calid,useremail)
				entry = self.client.GetCalendarAclEntry(aclEntryUri)
			
				self.client.DeleteAclEntry(entry.GetEditLink().href)
				
			except:
				logging.error(str(e.args))
				raise
		
		else:
			try:
				logging.info('Adding "' + accesslevel + '" calendar rights for ' + useremail)
				rule = gdata.calendar.CalendarAclEntry()
				rule.scope = gdata.calendar.Scope(value=useremail, scope_type='user')
				roleValue = 'http://schemas.google.com/gCal/2005#%s' % (accesslevel)
				rule.role = gdata.calendar.Role(value=roleValue)
				aclUrl = 'https://www.google.com/calendar/feeds/%s/acl/full' % (calid)
				returned_rule = self.client.InsertAclEntry(rule, aclUrl)
			except Exception, e:
				logging.error(str(e.args))
				raise
	
		
		
	def UpdateCalendarTrainingEvent(self,calid,duedate,invitees,title,description,eventfeed=None):
		reqType = calendar.AttendeeType()
		reqType.value = 'REQUIRED'
		accStatus = calendar.AttendeeStatus()
		accStatus.value = 'ACCEPTED'
		
		if eventfeed is None:
			newevent = True
			event_entry = gdata.calendar.CalendarEventEntry()
		else:
			newevent = False
			event_entry = self.client.GetCalendarEventEntry(eventfeed)
			#logging.info(str(event_entry))
			
			
		if invitees is not None:
			for email in invitees:
					new_who = calendar.Who(email=email,
		        							attendee_type=reqType,attendee_status=accStatus,
		    								)
					event_entry.who.append(new_who)
				
		if title is not None:
			event_entry.title = atom.Title(text=title)

		if description is not None:
			event_entry.content = atom.Content(text=description)
		
		if duedate is not None:
			enddate = duedate + datetime.timedelta(microseconds=1)
			event_entry.when = []
			event_entry.when.append(gdata.calendar.When(start_time=duedate.strftime("%Y-%m-%dT%H:%M:%S"),end_time=enddate.strftime("%Y-%m-%dT%H:%M:%S")))
			
		if newevent:
			event_entry.where.append(gdata.calendar.Where(value_string="Anywhere"))
			event_entry.guests_can_invite_others = calendar.GuestsCanInviteOthers(value='false')
			event_entry.guests_can_modify = calendar.GuestsCanModify(value='false')
			event_entry.guests_can_see_guests = calendar.GuestsCanSeeGuests(value='false')
			#event.extended_property.append(gdata.calendar.ExtendedProperty(name=name, value=value))
			return self.client.InsertEvent(event_entry,'http://www.google.com/calendar/feeds/'+ calid + '/private/full')
		else:
			return self.client.UpdateEvent(event_entry.GetEditLink().href, event_entry)
		
	
	def GetAllCalendars(self):
		feed = self.client.GetAllCalendarsFeed()
		return feed
	