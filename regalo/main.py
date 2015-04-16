#EXTERNAL LIBRARIES
import webapp2
import re
import jinja2
import os 
from google.appengine.ext import db
from google.appengine.api import mail
import string
import random
import hashlib
import hmac
from string import letters

import logging
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler


#FOR HASHING COOKIE
secret = "imsosecret"

#RETAILERS
retailers=("Applebees", "Best Buy","Body Shop","Chipotle","CVS","Dominos Pizza","Dunkin Donuts","Forever 21","Papa Johns","WalMart")

#INIT TEMPLATE DIRECTORY
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                                autoescape = True)
def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

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

#---------------------------------------------------RETAILER DB---------------------------------------------------#
class Retailer(db.Model):
    name = db.StringProperty(required=True,choices=retailers)
    link = db.LinkProperty()

    @classmethod
    def by_ret_name(cls, ret_name):
        u = Retailer.all().filter('name =', ret_name).get()
        return u

    @classmethod
    def by_id(cls, rid):
        return Retailer.get_by_id(rid)

    @classmethod
    def register(cls, name, link = None):
        return Retailer(name = name, link = link)
#-----------------------------------------------------------------------------------------------------------------#

#-----------------------------------------------------USER DB-----------------------------------------------------#
class User(db.Model):
    first_name = db.StringProperty(required=True)
    last_name = db.StringProperty(required=True)
    user_name = db.StringProperty(required=True)
    pass_hash = db.StringProperty(required = True)
    email = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add = True)
    rating = db.IntegerProperty()

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
                    email = email,
                    rating = 0)

    @classmethod
    def login(cls, u_name, pw):
        user = cls.by_username(u_name)
        if user and valid_pw(u_name, pw, user.pass_hash):
            return user
#-----------------------------------------------------------------------------------------------------------------#

#-----------------------------------------------------POST DB-----------------------------------------------------#
class Post(db.Model):
    owner = db.ReferenceProperty(User,collection_name='user_posts')
    retailer = db.ReferenceProperty(Retailer)
    card_val = db.StringProperty(required=True)
    looking_for = db.ListProperty(str,required= True)
    created = db.DateTimeProperty(auto_now_add = True)
    num_bids = db.IntegerProperty()



    @classmethod
    def register(cls, owner, ret, val,choices):
        return Post(owner = owner, retailer = ret, card_val = val, looking_for = choices, num_bids = 0)

    def render(self):
        return render_str("post.html", p = self)

    def render_prof(self):
        return render_str("post_profile.html", p = self)

    def getsortkey(post):
        return post.created
#-----------------------------------------------------------------------------------------------------------------#

#-----------------------------------------------------------------------------------------------------------------#
class Review(db.Model):
    reviewer = db.ReferenceProperty(User,collection_name='reviewer_rev')
    owner = db.ReferenceProperty(User,collection_name='owner_rev')
    rev_content = db.TextProperty()
    created = db.DateTimeProperty(auto_now_add = True) 

    def render_myprof(self):
        return render_str("reviews.html", r = self)
#-----------------------------------------------------------------------------------------------------------------#

#---------------------------------------------------MAIN HANDLER--------------------------------------------------#
class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        kw.update(self.get_logintop())
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

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))

    def get_user(self):
        uid = self.read_secure_cookie('user_id')
        return User.by_id(int(uid))

    def get_logintop(self):
        if not self.user:
            return {"first":"SIGN IN", "second":"Don't have an account?","third":"CREATE ONE", "firstref":"/signin","secondref":"/register","arr1_disp":"inline-block"}
        else:
            u = self.get_user();
            return {"first":"Hi, " + u.first_name + ". ", "second":"  Not " + u.first_name + "?","third":"Sign out","firstref":"/myprofile","secondref":"/logout","arr1_disp":"none"}
    def default_logintop(self):
        return {"first":"SIGN IN", "second":"Don't have an account?","third":"CREATE ONE", "firstref":"/signin","secondref":"/register","arr1_disp":"inline-block"}
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------SIGN UP PAGE HANDLER-----------------------------------------------#
class SignUpHandler(Handler):
    def get(self):
        self.render('register.html')


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
                have_error = True

        #password and verify passoword
        if not self.password or not self.pass_verify:
            if not self.password:
                params['error_password'] = "*required"
                have_error = True
            if not self.pass_verify:
                params['error_verify'] = "*required"
                have_error = True
        elif not valid_password(self.password) or self.password != self.pass_verify:
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
            self.render('register.html', **params)
        else:
            user = User.register(self.first_name, self.last_name, self.user_name, self.password, self.email)
            user.put()
            self.login(user)
            self.redirect("/browse")
            message = mail.EmailMessage()
            message.sender = "accounts@reeegalo.appspotmail.com"
            message.to = "yosephbasileal@yahoo.com"
            message.subject = "Account Registeration Successful! - Reeegalo"
            message.body = """Welcome, %s!\nYour reeegalo.appspot.com account has been approved.  You can now visit\nhttp://reeegalo.appspot.com/ and sign in using your account to\naccess its features.\nThe Reeegalo Team""" % self.last_name
            message.send()
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------SIGN IN PAGE HANDLER-----------------------------------------------#
class SignInHandler(Handler):
    def get(self):
        if self.user:
            self.redirect("/browse")
        else:
            self.render('signin.html')
       

    def post(self):
        user_name = self.request.get('username')
        password = self.request.get('password')

        user = User.login(user_name, password)
        if user:
            self.login(user)
            self.redirect("/browse")
        else:
            err = 'Invalid username or password'
            self.render('signin.html', error_login = err)
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------FRONT PAGE HANDLER-------------------------------------------------#
class FrontPageHandler(Handler):
    def get(self):   
        self.render("frontpage.html")
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------FRONT PAGE HANDLER-------------------------------------------------#
class BrowseHandler(Handler):
    def get(self):
        get_values = self.request.GET
        t = None
        try:
            t = get_values['type']
        except KeyError:
            pass

        if self.user:
            u = self.get_user()
            if not t  or t == '1':
                posts = Post.all().filter('owner !=', u)
                self.render('browse_swap.html', posts = sorted(posts, key=Post.getsortkey, reverse=True))

            if t == '2':
                self.render('browse_sell.html')
            if t == '0':
                self.render('browse_all.html')
        else:
            self.redirect('/signin')
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------MY PROFILE HANDLER-------------------------------------------------#
class MyProfileHandler(Handler):
    def get(self):
        if self.user:
            posts = Post.all().filter('owner =', self.user)
            self.render("myprofile.html", username = self.user.user_name, email = self.user.email, rating = self.user.rating, posts = sorted(posts, key=Post.getsortkey, reverse=True))
        else:
            self.redirect('/signin')
#-----------------------------------------------------------------------------------------------------------------#

#------------------------------------------------MY POSTS HANDLER-------------------------------------------------#
class MyPostsHandler(Handler):
    def get(self):
        get_values = self.request.GET
        t = None
        try:
            t = get_values['type']
        except KeyError:
            pass

        if self.user:
            u = self.get_user()
            if not t  or t == '1':
                posts = Post.all().filter('owner =', u)
                self.render('myposts_swap.html', posts = sorted(posts, key=Post.getsortkey, reverse=True))

            if t == '2':
                self.render('myposts_sell.html')
        else:
            self.redirect('/signin')      
#-----------------------------------------------------------------------------------------------------------------#

#------------------------------------------------NEW POSTS HANDLER------------------------------------------------#
class NewPostHandler(Handler):
    def get(self):
        if self.user:
            self.render("myposts_new.html", retailers = retailers)
        else:
            self.redirect('/signin')

    def post(self):
        have_error = False
        self.card_retailer = self.request.get('retailer')
        self.selected_rets = self.request.get('choices', allow_multiple=True)
        self.value = self.request.get('value')

        if not self.value or not self.selected_rets:
            have_error = True
        self.response.write(self.selected_rets)
        #????????????????????/do error checking
        if have_error:
            self.render("myposts_new.html", retailers = retailers)
        else:
            num_choices = len(self.selected_rets)
            choices = [0] * num_choices
            for i in range(0,num_choices):
                choices[i] = str(self.selected_rets).split(',')[i].split("'")[1]

            u = self.get_user()
            r = Retailer.by_ret_name(self.card_retailer)
            self.response.write(choices)
            p = Post.register(u, r, self.value, choices)
            p.put()
            self.redirect('/myposts')   
#-----------------------------------------------------------------------------------------------------------------#

#-------------------------------------------------MY BIDS HANDLER-------------------------------------------------#
class MyBidsHandler(Handler):
    def get(self):
        if self.user:
            self.render("mybids.html")
        else:
            self.redirect('/signin')
#-----------------------------------------------------------------------------------------------------------------#

#---------------------------------------------------ABOUT HANDLER-------------------------------------------------#
class AboutHandler(Handler):
    def get(self):  
        self.render("about.html")       
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------------HELP HANDLER-------------------------------------------------#
class HelpHandler(Handler):
    def get(self):
        self.render("help.html")
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------------HELP HANDLER-------------------------------------------------#
class LogoutHandler(Handler):
    def get(self):
        self.logout()
        self.redirect('/signin')
#-----------------------------------------------------------------------------------------------------------------#

#--------------------------------------------RETAILER REGISTRATION HANDLER----------------------------------------#
class RetRegHandler(Handler):
    def get(self):
        for ret in retailers:
            r = Retailer.register(ret)
            r.put()
#-----------------------------------------------------------------------------------------------------------------#

#-----------------------------------------------USERS PROFILE PAGE HANDLER----------------------------------------#
class UsersPageHandler(Handler):
    def get(self, user_id):
        user = User.by_id(int(user_id))
        if not user:
            self.error(404)
            return
        posts = Post.all().filter('owner =', user)
        reviews = Review.all().filter('owner =', user)
        self.render("users.html", u = user, posts = posts, reviews = reviews )
#-----------------------------------------------------------------------------------------------------------------#

#--------------------------------------------------SWAP BID PAGE HANDLER------------------------------------------#
class SwapbidHandler(Handler):
    def get(self):
        user = self.get_user();
        get_values = self.request.GET
        post_id = get_values['p']

        owner_id = get_values['o']
        owner = User.by_id(int(owner_id))

        self.render("swapbid.html", owner_id = owner_id, owner = owner.user_name, post = post_id, user_id = user.key().id(), user = user.user_name)
#-----------------------------------------------------------------------------------------------------------------#


#//////////////////////////////////////////TEST/////////////////////////////////////
class Movie(db.Model):
    title = db.StringProperty()
    picture = db.BlobProperty(default=None)

class TestHandler(Handler):
    def get(self):
        title = "pic"
        movie = getMovie(title)
        if (movie and movie.picture):
            self.response.headers['Content-Type'] = 'image/jpeg'
            self.response.out.write(movie.picture)
        else:
            self.redirect('/static/noimage.jpg') 

def getMovie(title):
    result = db.GqlQuery("SELECT * FROM Movie WHERE title = :1 LIMIT 1",
                    title).fetch(1)
    if (len(result) > 0):
        return result[0]
    else:
        return None

class LogSenderHandler(InboundMailHandler):
    def receive(self, mail_message):
        logging.info("Received a message from: " + mail_message.sender)

#///////////////////////////////////////^^TEST^^/////////////////////////////////////


app = webapp2.WSGIApplication([ #URL handlers
    ('/', FrontPageHandler),
    ('/register', SignUpHandler),
    ('/signin', SignInHandler),
    ('/browse', BrowseHandler),
    ('/myprofile', MyProfileHandler),
    ('/myposts', MyPostsHandler),
    ('/myposts/newpost', NewPostHandler),
    ('/mybids', MyBidsHandler),
    ('/about', AboutHandler),
    ('/help', HelpHandler),
    ('/test',TestHandler),
    ('/logout', LogoutHandler),
    ('/retailersReg', RetRegHandler),
    ('/users/([0-9]+)', UsersPageHandler),
    ('/swapbid',SwapbidHandler)
    ], debug=True)

app2 = webapp2.WSGIApplication([LogSenderHandler.mapping()], debug=True)