#EXTERNAL LIBRARIES
import webapp2
import re
import jinja2
import os 
from google.appengine.ext import db
import string
import random
import hashlib
import hmac
from string import letters

#FOR HASHING COOKIE
secret = "imsosecret"

#INIT TEMPLATE DIRECTORY
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                                autoescape = True)

#REGULAR EXPRESSION VALIDATION----------
FIRST_RE = re.compile(r"^[a-zA-Z]{1,20}$") #atleast one characters, atmost 20, only letters
LAST_RE  = re.compile(r"^[a-zA-Z]{1,20}$") #atleast one characters, atmost 20, only letters
USER_RE = re.compile(r"^[a-zA-Z0-9_]{5,20}$") #atelast five characters, atmost 20, letters, numbers, underscore, hyphen
EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$') #m@m.m format
PASS_RE = re.compile(r"^.{5,20}$") #atleast five characters, atmost 20

#validate user inputs
def valid_firstname(first_name):
    return FIRST_RE.match(first_name)
def valid_lastname(last_name):
    return LAST_RE.match(last_name)
def valid_username(username):
    return USER_RE.match(username)
def valid_password(password):
    return PASS_RE.match(password)
def valid_email(email):
    return EMAIL_RE.match(email)
#---------------------------------------

#HANDLING COOKIES-----------------------
def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val
#---------------------------------------
#USER AUTHENTICATION--------------------
def make_salt():
    return ''.join(random.choice(string.letters) for x in xrange(5))

def make_pw_hash(name, pw, salt = None):
    if not salt: #we only create a new salt if a new user comes in
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return "%s,%s" % (h,salt)

def valid_pw(name,pw,h):
    salt = h.split(',')[1]
    return h == make_pw_hash(name,pw,salt)
#---------------------------------------


#-----------------------------------------------------USER DB-----------------------------------------------------#
class User(db.Model):
    first_name = db.StringProperty(required=True)
    last_name = db.StringProperty(required=True)
    user_name = db.StringProperty(required=True)
    pass_hash = db.StringProperty(required = True)
    email = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add = True)

    @classmethod
    def by_username(cls, u_name):
        u = User.all().filter('user_name =', u_name).get()
        return u

    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid)

    @classmethod
    def register(cls, f_name, l_name, u_name, pw, email):
        pw_hash = make_pw_hash(u_name, pw)
        return User(first_name = f_name,
                    last_name = l_name,
                    user_name = u_name,
                    pass_hash = pw_hash,
                    email = email)

    @classmethod
    def login(cls, u_name, pw):
        user = cls.by_username(u_name)
        if user and valid_pw(u_name, pw, user.pass_hash):
            return user
#-----------------------------------------------------------------------------------------------------------------#

#---------------------------------------------------MAIN HANDLER--------------------------------------------------#
class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------SIGN UP PAGE HANDLER-----------------------------------------------#
class SignUpHandler(Handler):
    def get(self):
        self.render('signup.html')

    def post(self):
        have_error = False

        #Get from input
        self.first_name = self.request.get('first_name')
        self.last_name = self.request.get('last_name')
        self.user_name = self.request.get('user_name')     
        self.password = self.request.get('password')
        self.pass_verify = self.request.get('pass_verify')
        self.email = self.request.get('email')

        #Check for errors
        params = dict(first_name = self.first_name, last_name = self.last_name, user_name = self.user_name, email = self.email)
        #first name
        if not self.first_name:
            params['error_first'] = "*required"
            have_error = True
        elif not valid_firstname(self.first_name):
            params['error_first'] = "*not a valid name"
            have_error = True

        #last name
        if not self.last_name:
            params['error_last'] = "*required"
            have_error = True
        elif not valid_lastname(self.last_name):
            params['error_last'] = "*not a valid name"
            have_error = True

        #user name

        if not self.user_name:
            params['error_username'] = "*required"
            have_error = True
        elif not valid_username(self.user_name):
            params['error_username'] = "*minimum five characters, letters, numbers and underscore"
            have_error = True
        else:
            user = User.by_username(self.user_name)
            if user:
                params['error_username'] = "*user name already exists"

        #password and verify passoword
        if not self.password or not self.pass_verify:
            if not self.password:
                params['error_password'] = "*required"
                have_error = True
            if not self.pass_verify:
                params['error_verify'] = "*required"
                have_error = True
        if not valid_password(self.password) or self.password != self.pass_verify:
            if not valid_password(self.password):
                params['error_password'] = "*minimum five characters"
                have_error = True
            elif self.password != self.pass_verify:
                params['error_verify'] = "*your passwords didn't match"
                have_error = True

        #email
        if not self.email:
            params['error_email'] = "*required"
            have_error = True
        elif not valid_email(self.email):
            params['error_email'] = "*that's not a valid email."
            have_error = True

        #REGISTER OR RETURN ERROR
        if have_error:
            self.render('signup.html', **params)
        else:
            user = User.register(self.first_name, self.last_name, self.user_name, self.password, self.email)
            user.put()
            self.login(user)
            self.redirect("/")
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------SIGN IN PAGE HANDLER-----------------------------------------------#
class SignInHandler(Handler):
    def get(self):
        self.render('signin.html')

    def post(self):
        user_name = self.request.get('username')
        password = self.request.get('password')

        user = User.login(user_name, password)
        if user:
            self.login(user)
            self.redirect("/")
        else:
            err = 'Invalid username or password'
            self.render('signin.html', error_login = err)
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------FRONT PAGE HANDLER-------------------------------------------------#
class FrontHandler(Handler):
    def get(self):   
        self.render("frontpage.html")
#-----------------------------------------------------------------------------------------------------------------#

app = webapp2.WSGIApplication([ #URL handlers
    ('/', FrontHandler),
    ('/register', SignUpHandler),
    ('/signin', SignInHandler)
    ], debug=True)
