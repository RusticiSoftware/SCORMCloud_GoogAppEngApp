# Import template library
from google.appengine.ext.webapp import template
from modelutils import *
register = template.create_template_register()
# Set register
#register = template.Library()

# Register filter
@register.filter
def usertype(value):
	if value == '9':
		return "Administrator"
	elif value == '6':
		return "Trainer"
	elif value == '5':
		return "Content Creator"
	else:
		return "Learner"

@register.filter
def populationtype(value):
	if value =="all":
		return "All invitees"
	elif value == "incomplete":
		return "Learners not complete"
	elif value == "notstarted":
		return "Learners not started"
	else:
		return value

@register.filter
def username(value):
	up = GetUserProfileFromGuser(value)
	return up.fname + ' ' + up.lname

@register.filter
def noNone(value,replacement=""):
	if value is None:
		return replacement
	else:
		return value
		
@register.filter
def qtypeDict(value):
	if value == 'lname':
		return "last name"
	elif value == 'fname':
		return "first name"
	elif value == 'notstarted':
		return "not started"
	else:
		return value