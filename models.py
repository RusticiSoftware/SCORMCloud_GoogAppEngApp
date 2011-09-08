#!/usr/bin/env python
# encoding: utf-8
"""
models.py

Created by brian.rogers on 2009-11-05.
Copyright (c) 2009 Rustici Software. All rights reserved.
"""

from google.appengine.ext import db

#data objects
class UserProfile(db.Expando):
    guser = db.StringProperty()
    email = db.EmailProperty()
    fname = db.StringProperty()
    lname = db.StringProperty()
    nickname = db.StringProperty()
    createddate = db.DateTimeProperty(auto_now_add=True)
    lastaccess = db.DateTimeProperty()
    timezone = db.StringProperty()
    assignmentemail = db.BooleanProperty()
    allowcalendaraccess = db.BooleanProperty()
    accesslevel = db.StringProperty()
    twitterhandle = db.StringProperty()
    oauthtoken = db.StringProperty()
    userimage = db.BlobProperty()
    tags = db.StringListProperty()

class Course(db.Expando):
    courseid = db.StringProperty()
    title = db.StringProperty()
    descriptiontext = db.TextProperty()
    duration = db.StringProperty()
    createdbyuser = db.StringProperty()
    createddate = db.DateTimeProperty(auto_now_add=True)
    tags = db.StringListProperty()
    incatalog = db.BooleanProperty()
    gappimport = db.BooleanProperty()
    orphaned = db.BooleanProperty()

class Assignments(db.Expando):
    createddate = db.DateTimeProperty(auto_now_add=True)
    createdbyuser = db.StringProperty()
    courseid = db.StringProperty()
    inviteecount = db.IntegerProperty()
    addevent = db.BooleanProperty()
    duedate = db.DateTimeProperty()
    title = db.StringProperty()
    description = db.TextProperty()
    sendemail = db.BooleanProperty()
    emailsubject = db.StringProperty()
    emailbody = db.TextProperty()
    remindersubject = db.StringProperty()
    reminderbody = db.TextProperty()
    autoexpire = db.BooleanProperty()
    active = db.BooleanProperty()
    eventfeed = db.StringProperty()

class Registration(db.Expando):
    regid = db.StringProperty()
    courseid = db.StringProperty()
    coursetitle = db.StringProperty()
    userid = db.StringProperty()
    createddate = db.DateTimeProperty(auto_now_add=True)
    score = db.StringProperty()
    completion = db.StringProperty()
    satisfaction = db.StringProperty()
    timespent = db.StringProperty()
    lastaccess = db.DateTimeProperty()
    assignment = db.ReferenceProperty(Assignments)
    active = db.BooleanProperty()

class Settings(db.Expando):
    sitetitle = db.StringProperty()
    sitelogo = db.BlobProperty()
    appid = db.StringProperty()
    secretkey = db.StringProperty()
    servicehost = db.StringProperty()
    appsdomain = db.StringProperty()
    appserverhost = db.StringProperty()
    starttext = db.TextProperty()
    startlogo = db.TextProperty()
    defaultavatar = db.BlobProperty()
    calendarid = db.StringProperty()
    calendartimezone = db.StringProperty()
    enablereminders = db.BooleanProperty()
    enableautoexpire = db.BooleanProperty()
    remindersender = db.StringProperty()
    duetime = db.TimeProperty()

class UserMessages(db.Expando):
    guser = db.StringProperty()
    msgtype = db.StringProperty()
    message = db.TextProperty()

class Reminders(db.Expando):
    createddate = db.DateTimeProperty(auto_now_add=True)
    createdbyuser = db.StringProperty()
    population = db.StringProperty()
    assignment = db.ReferenceProperty(Assignments)
    timeunits = db.StringProperty()
    timequantity = db.IntegerProperty()
    remindertime = db.DateTimeProperty()
    sent = db.BooleanProperty()
