#!/usr/bin/env python
# encoding: utf-8
"""
main.py

Created by brian.rogers on 2009-11-05.
Copyright (c) 2010 Rustici Software. All rights reserved.
"""

import cgi
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from google.appengine.dist import use_library
use_library('django', '1.1')



from models import *
from decorators import *
from views import *
from adminviews import *


# application setup - add new pages here...
logging.getLogger().setLevel(logging.DEBUG)
application = webapp.WSGIApplication([
                                                                        ('/', MyTraining),
                                                                        ('/mytraining', MyTraining),
                                                                        ('/course/upload', UploadForm),
                                                                        ('/course/import', Importer),
                                                                        ('/course/addFromCloud', AddCloudCourseAction),
                                                                        ('/course/update/(.*)', CourseUpdateForm),
                                                                        ('/course/updateaction', CourseUpdateAction),
                                                                        ('/course/list', CourseList),
                                                                        ('/course/list/(.*)', CourseList),
                                                                        ('/course/catalog', CourseCatalog),
                                                                        ('/course/detail/(.*)', CourseDetail),
                                                                        ('/course/admindetail/(.*)', CourseAdminDetail),
                                                                        ('/course/registrations/(.*)/(.*)', CourseRegs),
                                                                        ('/course/delete/(.*)', DeleteCourse),
                                                                        ('/course/preview/(.*)', PreviewCourse),
                                                                        ('/course/launch/(.*)', NewRegLaunchCourse),
                                                                        ('/registration/userreg/(.*)', NewReg),
                                                                        ('/registration/delete/(.*)', DeleteReg),
                                                                        ('/registration/reset/(.*)', ResetReg),
                                                                        ('/registration/report/(.*)', RegReport),
                                                                        ('/registration/lhreport/(.*)', LaunchHistoryReport),
                                                                        ('/registration/launch/(.*)', LaunchCourse),
                                                                        ('/registration/list', RegList),
                                                                        ('/reports', Reports),
                                                                        ('/course/exit', CourseExit),
                                                                        ('/registration/assign', AssignForm),
                                                                        ('/assignments/(.*)', AssignmentDetail),
                                                                        ('/assignment/launch/(.*)', LaunchAssignment),
                                                                        ('/assignment/delete/(.*)', DeleteAssignment),
                                                                        ('/NonUserLaunch', NonUserLaunch),
                                                                        ('/admin/settings', SettingsForm),
                                                                        ('/admin/settings/update', SettingsAction),
                                                                        ('/user/(.*)', UserDetails),
                                                                        ('/usersettings', UserSettings),
                                                                        ('/usersettingsaction', UserSettingsAction),
                                                                        ('/admin/user/edit/(.*)', UserAdminForm),
                                                                        ('/useradminaction', UserAdminAction),
                                                                        ('/useradminaction/update', UpdateUserInfo),
                                                                        ('/useradminaction/import', ImportDomainUsers),
                                                                        ('/usergadget', UserGadget),
                                                                        ('/admin/user/list', UserList),
                                                                        ('/admin/user/list/(.*)', UserList),
                                                                        ('/api', ApiAction),
                                                                        ('/avatar', Avatar),
                                                                        ('/ajax/assignaction', AssignAction),
                                                                        ('/ajax/reporturl', ReportageUrl),
                                                                        ('/ajax/checkemail',CheckUserEmail),
                                                                        ('/ajax/assignactive',AssignActive),
                                                                        ('/ajax/assignautoexpire',AssignAutoExpire),
                                                                        ('/ajax/assignemail',AssignUpdateEmail),
                                                                        ('/ajax/sendemail',AssignSendEmail),
                                                                        ('/ajax/assigndate',AssignDate),
                                                                        ('/ajax/assignusers',AssignNewUsers),
                                                                        ('/ajax/updateevent',AssignUpdateEvent),
                                                                        ('/ajax/removemessage/(.*)',RemoveMessage),
                                                                        ('/ajax/addreminder',AddReminder),
                                                                        ('/ajax/delreminder',DeleteReminder),
                                                                        ('/inactivecourse',InactiveCourse),
                                                                        ('/search', CourseSearch)],
                                    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
