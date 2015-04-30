#EXTERNAL LIBRARIES
import webapp2 #web framework
import re #regular expressions
import jinja2 #templating library
import os #to access template directory
from google.appengine.ext import db #google datasotre
from google.appengine.api import mail #for sending in/out emails
import string
import random
import hashlib
import hmac
from string import letters
import logging  #python logging library
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler


#FOR HASHING COOKIE
secret = "imsosecret"

#RETAILERS SUPPORTED
retailers=["Applebees",
           "Best-Buy",
           "Body-Shop",
           "Chipotle",
           "CVS",
           "Dominos-Pizza",
           "Dunkin-Donuts",
           "Forever-21",
           "Papa-Johns",
           "WalMart",
           "Starbucks",
           "Home-Depot",
           "Subway",
           "Barnes-and-Noble",
           "Nordstrom",
           "Lowes",
           "TJ-Maxx",
           "Toys-R-Us",
           "Old-Navy",
           "Sears",
           "Target"]
retailers.sort()

#INIT TEMPLATE DIRECTORY
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                                autoescape = True)

#THIS IS USED TO RENDER ANY TEMPLATE SUCH AS POST, BID...
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

#get a user_id val and makes a secure cookie
def make_secure_val(val):   
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

#gets a cokkie and validates
def check_secure_val(secure_val):
    val = secure_val.split('|')[0]         #cookie val string has a val and a hash separated by |
    if secure_val == make_secure_val(val):
        return val
#---------------------------------------

#USER AUTHENTICATION--------------------

#makes random salt of length five
def make_salt():
    return ''.join(random.choice(string.letters) for x in xrange(5))

#hashes the password and combines it with salt
def make_pw_hash(name, pw, salt = None):
    if not salt: #we only create a new salt if a new user comes in
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return "%s,%s" % (h,salt)       #combine hased password and salt

#given a username and password validate passoword by comparing to the hash already stored
def valid_pw(name,pw,h):
    salt = h.split(',')[1]
    return h == make_pw_hash(name,pw,salt)

#hashes email address -- to be used for email address verification
def make_email_hash(secret, email, h):
    h = hashlib.sha256(secret + email + h).hexdigest()
    return "%s" % (h)
#---------------------------------------
    
#------------------------------------------------ERROR HANDLER---------------------------------------------------#

#handles HTTP 404 error - file not found
def handle_404(request, response, exception):
    logging.exception(exception)
    response.write(render_str('404.html'));
    response.set_status(404)

#handles HTTP 500 error - internal server error
def handle_500(request, response, exception):
    logging.exception(exception)
    response.write(render_str('500.html'));
    response.set_status(500)
#-----------------------------------------------------------------------------------------------------------------#

#---------------------------------------------------RETAILER DB---------------------------------------------------#
#model is for retailers
class Retailer(db.Model):
    #attributes of retailer model
    name = db.StringProperty(required=True,choices=retailers)
    link = db.LinkProperty() #link to balance verification page on retailers website, not implemented yet

    #help functions
    @classmethod
    def by_ret_name(cls, ret_name): #given a retailer name return the entity from db
        u = Retailer.all().filter('name =', ret_name).get()
        return u

    @classmethod
    def by_id(cls, rid): #given a retailer id return the entity from db
        return Retailer.get_by_id(rid)

    @classmethod
    def register(cls, name, link = None): #given the necesary info, register a new retailer and return the new entity
        return Retailer(name = name, link = link)
#-----------------------------------------------------------------------------------------------------------------#

#-----------------------------------------------------USER DB-----------------------------------------------------#
#model of user accounts
class User(db.Model):
    #attributes for user model
    first_name = db.StringProperty(required=True)
    last_name = db.StringProperty(required=True)
    user_name = db.StringProperty(required=True)
    pass_hash = db.StringProperty(required = True) #hashed password
    email = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add = True)
    traded_with = db.ListProperty(int, required = True) #to allow them to write comments 
    rating_u = db.IntegerProperty(required=True)    #thumbs up count
    rating_d = db.IntegerProperty(required=True)    #thumbs down count

    #for email verification
    auth_token = db.StringProperty(required = True)
    confirmed = db.BooleanProperty(required = True)

    #help functions
    @classmethod
    def by_username(cls, u_name):  #given a username return the user entity from db
        u = User.all().filter('user_name =', u_name).get()
        return u

    @classmethod
    def by_id(cls, uid):    #given an id return the user entity from db
        return User.get_by_id(uid)

    @classmethod
    def register(cls, f_name, l_name, u_name, pw, email): #create and return a new user entity
        pw_hash = make_pw_hash(u_name, pw)  #hash password
        email_hash = make_email_hash(secret, email, pw_hash) #hash email for making verification link
        return User(first_name = f_name,
                    last_name = l_name,
                    user_name = u_name,
                    pass_hash = pw_hash,
                    email = email,
                    traded_with = [],
                    rating_u = 0,
                    rating_d = 0,
                    auth_token = email_hash,
                    confirmed = False)

    @classmethod
    def login(cls, u_name, pw): #validate password when a user tries to log in
        user = cls.by_username(u_name)
        if user and valid_pw(u_name, pw, user.pass_hash):
            return user
#-----------------------------------------------------------------------------------------------------------------#

#---------------------------------------------------SWAP POST DB--------------------------------------------------#
#model for swap posts
class SwapPost(db.Model):
    #attributes for swap post model
    owner = db.ReferenceProperty(User,collection_name='user_swapposts')
    retailer = db.ReferenceProperty(Retailer, collection_name='ret_swapposts')
    card_val = db.StringProperty(required=True)
    card_code = db.StringProperty(required = True)
    card_pin = db.StringProperty()
    looking_for = db.ListProperty(str,required= True) #gift cards owner of post is looking ofr
    created = db.DateTimeProperty(auto_now_add = True)
    num_bids = db.IntegerProperty()
    status = db.StringProperty()

    #help functions
    @classmethod
    def register(cls, owner, ret, val, code, pin, choices): #registers a new post and returns the new entity
        return SwapPost(owner = owner, retailer = ret, card_val = val, card_code = code, card_pin = pin, looking_for = choices, num_bids = 0, status = "Active")

    @classmethod
    def by_id(cls, pid): #given an id return a post entity
        return SwapPost.get_by_id(pid)

    def render(self):  #renders post tempate for browse page
        return render_str("post_swap.html", p = self)

    def render_myposts(self):   #renders post for myposts page
        return render_str("post_swap_myposts.html", p = self)

    def render_prof(self):  #renders post template for myprofile page
        return render_str("post_swap_prof.html", p = self, type="swap")

    def render_bidpage(self, bids): #renders post template for mybids main page
        return render_str("post_swap_bidpage.html", p = self, bids = bids )

    def render_bidpop(self, bids):  #renders posts template for pop up window on mybids page
        return render_str("post_swap_bidpop.html", p = self, bids = bids )

    def getsortkey(post):   #use to get key to sort by date
        return post.created

    def sortretailer(post): #use to get key to sort alphabetically by retailer name
        return post.retailer.name

    def sortprice(post):    #use to get key to sort by price
        return int(post.card_val)
#-----------------------------------------------------------------------------------------------------------------#

#---------------------------------------------------SELL POST DB--------------------------------------------------#
#Model for sell post
class SellPost(db.Model):
    #attributes for sell post
    owner = db.ReferenceProperty(User,collection_name='user_sellposts') #refers to user model
    retailer = db.ReferenceProperty(Retailer, collection_name='ret_sellposts') #refers to retialer model
    card_val = db.StringProperty(required=True)
    card_code = db.StringProperty(required = True)
    card_pin = db.StringProperty()
    offer_for = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add = True)
    num_bids = db.IntegerProperty()

    #help functions
    @classmethod
    def register(cls, owner, ret, val, code, pin, val_offer): #register a  sell post and returns the new entity
        return SellPost(owner = owner, retailer = ret, card_val = val, card_code = code, card_pin = pin, offer_for = val_offer, num_bids = 0)

    @classmethod
    def by_id(cls, pid):    #given a id return the sell post entity
        return SellPost.get_by_id(pid)

    def render(self):   #render sell post on browse page
        return render_str("post_sell.html", p = self)

    def render_prof(self): #render posts on profile page
        return render_str("post_sell_prof.html", p = self)

    def getsortkey(post): #use for sorting by date
        return post.created
#-----------------------------------------------------------------------------------------------------------------#

#---------------------------------------------------REVIEWS DB----------------------------------------------------#
#model for user reviews
class Review(db.Model):
    reviewer = db.ReferenceProperty(User,collection_name='reviewer_rev') #reviewer
    reviewed = db.ReferenceProperty(User,collection_name='reviewed_rev') #person being reviewed
    revcontent = db.TextProperty(required = True) #main content of review
    title = db.StringProperty(required = True)  #short title
    created = db.DateTimeProperty(auto_now_add = True)
    rating = db.StringProperty(required = True) #moved to users model, not used

    @classmethod
    def register(cls, reviewer_u, reviewed_u, rev_cont_u, title_u, rating_u):
        return Review(reviewer = reviewer_u, reviewed = reviewed_u, revcontent = rev_cont_u, title = title_u, rating = rating_u)

    def render_users(self): #render reviews on myprofile page
        return render_str("reviews_myprof.html", r = self)

    def render_myprof(self): #render reviews on other users profile page
        return render_str("reviews_myprof.html", r = self)

    def getsortkey(rev): #get sort key to sort by date
        return rev.created
#-----------------------------------------------------------------------------------------------------------------#

#---------------------------------------------------SWAP BID DB---------------------------------------------------#
#model for bids submitted on swap post
class Bid_swap(db.Model):
    bidder = db.ReferenceProperty(User, collection_name = 'bidder_bids') #person bidding
    post_owner = db.ReferenceProperty(User, collection_name = 'owner_bids') #person whose post is bidded on
    on_post = db.ReferenceProperty(SwapPost, collection_name = 'post_bids') #post bidden on
    bid_retailer = db.ReferenceProperty(Retailer, collection_name='ret_swapbids') #retailer of bid offer
    card_val = db.StringProperty(required=True) #card value of bid offer
    card_code = db.StringProperty(required = True) #card code of bid offer
    card_pin = db.StringProperty() #card pin of bid offer
    created = db.DateTimeProperty(auto_now_add = True)
    status = db.StringProperty()

    @classmethod
    def register(cls, bidder, post_owner, post, bid_ret, card_val, card_code, card_pin):
        return Bid_swap(bidder = bidder, post_owner = post_owner, on_post = post, bid_retailer = bid_ret, card_val = card_val, card_code = card_code, card_pin = card_pin, status = "Pending")

    @classmethod
    def by_id(cls, bid):
        return Bid_swap.get_by_id(bid)

    def render(self): #render bids template for mybids page - bids by others
        return render_str("bid_swap_bidpage.html", b = self)

    def render_pop(self): #render bids template for pop up window on mybids page
        return render_str("bid_swap_bidpop.html", b = self)

    def render_mybid(self): #render bids template for mybids page - bids by me
        return render_str("bid_swap_mybid.html", b = self)

    def render_myprof(self): #render bids template for my profile page
        return render_str("bid_swap_myprof.html", b = self)

    def getsortkey(post): #used for sorting
        return post.created
#-----------------------------------------------------------------------------------------------------------------#

#---------------------------------------------------MAIN HANDLER--------------------------------------------------#
#main HTTP request and response handler, cookie hanlder
class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):  #write out a string to browser
        self.response.out.write(*a, **kw)
    
    def render_str(self, template, **params): #given a template and parameters, renders and returns a string with 
        t = jinja_env.get_template(template) #gets template
        return t.render(params)

    def render(self, template, **kw):
        kw.update(self.get_logintop()) #added to always render the login/logout div on top of all pages
        self.write(self.render_str(template, **kw))

    def error(self,err):    #error handler
        if (err == 404):
            self.render('404.html')
        elif (err == 500):
            self.render('500.html')

    def login(self, user):  #set user_id cookie upon login
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):   #removes user_od cookie val upon logout
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def set_secure_cookie(self, name, val): #creates a secure cookie
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name): #reades a cookie and validates
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def initialize(self, *a, **kw): #reads cookie and returns sets the assocated user entity as the current user
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))

    def get_user(self): #duplicate -- initialize() already does this, 
        uid = self.read_secure_cookie('user_id')
        return User.by_id(int(uid))

    def get_logintop(self): #for determining contents that go into the top login/logout div
        if not self.user:   #if not logged in, show sign in a register options
            return {"first":"SIGN IN", "second":"Don't have an account?","third":"CREATE ONE", "firstref":"/signin","secondref":"/register","arr1_disp":"inline-block"}
        else:
            u = self.get_user(); #if logged in, how sign out and myprofile options
            return {"first":"Hi, " + u.first_name + ". ", "second":"  Not " + u.first_name + "?","third":"Sign out","firstref":"/myprofile","secondref":"/logout","arr1_disp":"none"}
    def default_logintop(self):
        return {"first":"SIGN IN", "second":"Don't have an account?","third":"CREATE ONE", "firstref":"/signin","secondref":"/register","arr1_disp":"inline-block"}
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------SIGN UP PAGE HANDLER-----------------------------------------------#
#Handler for sign up page
class SignUpHandler(Handler):
    #render register form upon get request
    def get(self):
        self.render('register.html')

    #handle register form
    def post(self):
        have_error = False

        #Get from input
        self.first_name = self.request.get('first_name')
        self.last_name = self.request.get('last_name')
        self.user_name = self.request.get('user_name')     
        self.password = self.request.get('password')
        self.pass_verify = self.request.get('pass_verify')
        self.email = self.request.get('email')

        #save user inputs to keep them when re-rendering the page, password not included for safety
        params = dict(first_name = self.first_name, last_name = self.last_name, user_name = self.user_name, email = self.email)

        #first name error check
        if not self.first_name:
            params['error_first'] = "*required"
            have_error = True
        elif not valid_firstname(self.first_name):
            params['error_first'] = "*not a valid name"
            have_error = True

        #last name error check
        if not self.last_name:
            params['error_last'] = "*required"
            have_error = True
        elif not valid_lastname(self.last_name):
            params['error_last'] = "*not a valid name"
            have_error = True

        #user name error check
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

        #password and verify passoword error check
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

        #email error check
        if not self.email:
            params['error_email'] = "*required"
            have_error = True
        elif not valid_email(self.email):
            params['error_email'] = "*that's not a valid email."
            have_error = True

        #REGISTER OR RETURN ERROR
        if have_error:
            self.render('register.html', **params) #if error, render page with error messages and previous user inputs
        else:
            user = User.register(self.first_name, self.last_name, self.user_name, self.password, self.email) #register new user
            user.put()  #put new user in db
            self.logout() #logout out if any user is already logged in
            #self.login(user)
            #self.redirect("/browse")

            #send email verification 
            auth_url = 'http://reeegalo.appspot.com/confirm/%s?u=%s' % (user.auth_token,user.key().id()) #link user will click on to validate email address
            message = mail.EmailMessage()
            message.sender = "accounts@reeegalo.appspotmail.com"
            message.to = self.email
            message.subject = "Account Registeration Successful! - Reeegalo"
            #email content - includes email verifcation link - commented out
            #message.body = """ Welcome, %s!\n\nYour reeegalo.appspot.com account has been approved. Please got to the following link %s to veify your email adress.You can then visit http://reeegalo.appspot.com/ and sign in using your account to access its features.\n\nThe Reeegalo Team""" % (self.first_name, auth_url)
            #email content - without email verification link 
            message.body = """ Welcome, %s!\n\nYour reeegalo.appspot.com account has been approved. You can now visit http://reeegalo.appspot.com/ and sign in to your account and access its features.\n\nThe Reeegalo Team""" % (self.first_name)
            message.send()
            self.render('register-success.html')
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------SIGN IN PAGE HANDLER-----------------------------------------------#
#hanler for signin page
class SignInHandler(Handler):
    #render login form upon get request
    def get(self):
        if self.user: #if already logged in redirect to browse page
            self.redirect("/browse")
        else:
            self.render('signin.html')
       
    #signin form Handler
    def post(self):
        #get form inputs
        user_name = self.request.get('username')
        password = self.request.get('password')

        user = User.login(user_name, password) #attempt login
        if user: #if valid login user and redirect o browse page
            self.login(user)
            self.redirect("/browse")
        else: #if invalid re-render login page with error message
            err = 'Invalid username or password'
            self.render('signin.html', error_login = err)
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------CONFRIM EMAIL HANDLER----------------------------------------------#
#handler for email confirmation link
class ConfirmUserHandler(Handler):
    #confirm users email when they click on the link sent to their email address
    def get(self,token): #url is of type /confirm/token?u=29347601293847
        get_values = self.request.GET #get user id
        u_id = int(get_values['u'])
        u = User.by_id(u_id)    #verify if user id is valid
        if not u.confirmed and u and u.auth_token == str(token): #verify token in link is same as one stores in db
            u.confirmed = True
            u.put()
            self.render('email-confirmed.html')
        else:
            self.error(404) #if invalide return 404 error
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------FRONT PAGE HANDLER-------------------------------------------------#
#hanles the very front page of the website
class FrontPageHandler(Handler):
    def get(self):   
        if self.user:   #if already logged in redirect
            self.redirect('/browse')
        else:
            self.render("frontpage-home.html")
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------BRWoSE PAGE HANDLER------------------------------------------------#
#browse page handler
class BrowseHandler(Handler):
    def get(self):
        if self.user: #if not logged in redirects to sign in page
            get_values = self.request.GET 
            t = None #t is for swap or sell type, swap = 1, sell = 2
            s = None #s if for sort type- options are date, priceH, priceL, retialer
            try:
                t = get_values['type']
                s = get_values['s']
            except KeyError:
                pass #if no s or no t, t = 1 and s = date by default

            u = self.user
            posts_swap = SwapPost.all().filter('owner !=', u).filter('status ==', 'Active')
            posts_sell = SellPost.all().filter('owner !=', u)
            if not t or t == '1':   #render swap posts
                if not s or s == 'date': #default
                    self.render('browse_swap.html', posts = sorted(posts_swap, key=SwapPost.getsortkey, reverse=True))
                elif s == 'priceH': #sort by price high to low
                    self.render('browse_swap.html', posts = sorted(posts_swap, key=SwapPost.sortprice, reverse=True))
                elif s == 'priceL': #sort by price low to high
                    self.render('browse_swap.html', posts = sorted(posts_swap, key=SwapPost.sortprice))
                elif s == 'retailer': #sort by retilaer A to Z
                    self.render('browse_swap.html', posts = sorted(posts_swap, key=SwapPost.sortretailer))
                else:
                    self.error(404) #if invalid 's'
            elif t == '2':  #render sell posts
                self.render('browse_sell.html', posts = sorted(posts_sell, key=SellPost.getsortkey, reverse=True))
            else:
                self.error(404)
                return
        else:
            self.redirect('/signin')
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------MY PROFILE HANDLER-------------------------------------------------#
#myprofile page hanlder
class MyProfileHandler(Handler):
    def get(self):
        if self.user: 
            posts1 = sorted(self.user.user_swapposts, key=SwapPost.getsortkey, reverse=True)  #sort swap posts by user based on date
            posts2 = sorted(self.user.user_sellposts, key=SellPost.getsortkey, reverse=True)  #sort sell posts by user based on date

            bids = self.user.bidder_bids    #get bids by user using collection name reference propery from the Bid_swap db model
            bids = sorted(bids, key=Bid_swap.getsortkey, reverse=True) #sort by date

            rev = self.user.reviewed_rev    #get reviews on user using collection name reference propery from the Review db model
            rev = sorted(rev, key=Review.getsortkey, reverse=True) #sort by date

            #render my profile page with required parameters
            self.render("myprofile_default.html", u = self.user, posts = posts1, posts2 = posts2, reviews = rev, bids = bids, allow = 'yes', backtourl = "myprofile", backto = "My Profile")

        else: #if not logged in redirect
            self.redirect('/signin')
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------EDIT PROFILE HANDLER-----------------------------------------------#
#handler for editing profile page
class EditProfHandler(Handler):
    #render profile edit form upon get request
    def get(self):
        if self.user: #if logged in
            posts1 = sorted(self.user.user_swapposts, key=SwapPost.getsortkey, reverse=True) #get swap posts by current user
            posts2 = sorted(self.user.user_sellposts, key=SellPost.getsortkey, reverse=True) #get sell posts by current user

            bids = self.user.bidder_bids    #get bids by current user
            bids = sorted(bids, key=Bid_swap.getsortkey, reverse=True) #sort

            #render myprofile edit page
            self.render('myprofile_edit.html', u = self.user, posts = posts1, posts2 = posts2, bids = bids, allow = 'no')
        else:   #if not logged in redirect
            self.redirect('/signin')

    #profile edit from handler        
    def post(self):
        #get user inputs from form
        self.email = self.request.get('email')
        self.first_name = self.request.get('first_name')
        self.last_name = self.request.get('last_name')
        have_error = False

        #first name error check - first name is optional
        error_first = ""
        if self.first_name and not valid_firstname(self.first_name):
            error_first = "*not a valid name"
            have_error = True

        #last name error check - last name is optional
        error_last = ""
        if self.last_name and not valid_lastname(self.last_name):
            error_last = "*not a valid name"
            have_error = True

        #email error check - email is optional
        error_email = ""
        if self.email and not valid_email(self.email):
            error_email = "*that's not a valid email."
            have_error = True

        if have_error: #if error re-render page with error and other required parameters on the myprofile page
            posts1 = sorted(self.user.user_swapposts, key=SwapPost.getsortkey, reverse=True)
            posts2 = sorted(self.user.user_sellposts, key=SellPost.getsortkey, reverse=True)
            bids = self.user.bidder_bids
            bids = sorted(bids, key=Bid_swap.getsortkey, reverse=True)
            self.render('myprofile_edit.html', u = self.user, posts = posts1, posts2 = posts2, email = self.email, first_name = self.first_name, last_name = self.last_name, error_first = error_first, error_last = error_last, error_email = error_email, bids = bids, allow = 'no')
        else:   #if no error update information in db
            if self.email:
                self.user.email = self.email
            if self.first_name:
                self.user.first_name = self.first_name
            if self.last_name:
                self.user.last_name = self.last_name

            self.user.put() #put updated entity in db
            self.redirect('/myprofile') #rediect to myprofile page with update info
#-----------------------------------------------------------------------------------------------------------------#

#------------------------------------------------MY POSTS HANDLER-------------------------------------------------#
#handler for rendering my posts page with requried parameters
class MyPostsHandler(Handler):
    def get(self):
        if self.user:
            get_values = self.request.GET
            t = None #for rendering sell or swap post types
            s = None #for sorting
            try:
                t = get_values['type']
                s = get_values['s']
            except KeyError:
                pass
            u = self.user
            #fucntionality similat to browse page except filters out posts by other users
            if not t  or t == '1':  #render swap posts
                posts = u.user_swapposts
                if not s or s == 'date': #sort by date
                    self.render('myposts_swap.html', posts = sorted(posts, key=SwapPost.getsortkey, reverse=True))
                elif s == 'priceH': #sort by price high to low
                    self.render('myposts_swap.html', posts = sorted(posts, key=SwapPost.sortprice, reverse=True))
                elif s == 'priceL': #sort by price low to high  
                    self.render('myposts_swap.html', posts = sorted(posts, key=SwapPost.sortprice))
                elif s == 'retailer': #sort by retailer name A - Z
                    self.render('myposts_swap.html', posts = sorted(posts, key=SwapPost.sortretailer))
                else: #if invalid value of 's'
                    self.error(404)

            elif t == '2':  #render sell posts
                posts = u.user_sellposts
                self.render('myposts_sell.html', posts = sorted(posts, key=SellPost.getsortkey, reverse=True))
            else:
                self.error(404) #if invalid value o f't'
                return
        else:   #if not logged in redirect
            self.redirect('/signin')      
#-----------------------------------------------------------------------------------------------------------------#

#--------------------------------------------EDIT SWAP POSTS HANDLER----------------------------------------------#
#handler for editing posts
class EditSwapHandler(Handler):
    #render edit posts page upon get request
    def get(self):
        if self.user:
            get_values = self.request.GET
            self.post_id = get_values['id'] #get id of post to be editted
            p = SwapPost.by_id(int(self.post_id))

            if p.owner.key().id() != self.user.key().id(): #if you are not owner of the post with id - error 404
                self.error(404)
                return

            self.render("myposts_edit.html", retailers = retailers) #render edit form
        else:
            self.redirect('/signin')

    def post(self):
        have_error = False

        #get user inputs form form  - all inputs are optional
        self.code = self.request.get('code')
        self.pin = self.request.get('pin')

        #save user inputs to keep them when re-rendering page
        params = dict(code = self.code, pin = self.pin, retailers = retailers)

        #get selected retailers 
        self.selected_rets = self.request.get('choices', allow_multiple=True)
        num_choices = len(self.selected_rets)

        if self.selected_rets and num_choices > 3: #check max of 3 retailers selected
            params['error_retailers'] = "*select a maximum of three"
            have_error = True


        if have_error:  #if error re-render page with error meessage
            self.render("myposts_edit.html", **params)
        else: 
            choices = [0] * num_choices
            for i in range(0,num_choices):
                choices[i] = str(self.selected_rets).split(',')[i].split("'")[1] #put looking-for in a list

            get_values = self.request.GET
            self.post_id = get_values['id']

            p = SwapPost.by_id(int(self.post_id)) #get post entity
            if self.code:
                p.card_code = self.Code #update card code if provided
            if self.pin:
                p.card_pin  = self.pin #update card pin if provided
            if self.selected_rets:
                p.looking_for = choices #update looking-for if provided
            p.put()

            self.render("myposts_edit_submitted.html")
#-----------------------------------------------------------------------------------------------------------------#

#------------------------------------------------NEW POSTS HANDLER------------------------------------------------#
#new post handler for both swap and sell posts
class NewPostHandler(Handler):
    #render form upon get request
    def get(self):
        if self.user: #if logged in
            self.render("myposts_new.html", retailers = retailers)
        else:   #if not logged in redirect
            self.redirect('/signin')

    #new post form handler
    def post(self):
        have_error = False

        #get user inputs from form
        self.type = self.request.get('type')
        self.card_retailer = self.request.get('retailer')
        self.value = self.request.get('value')
        self.code = self.request.get('code')
        self.pin = self.request.get('pin')

        #save inputs to keep them when re-rendering the page
        params = dict(value = self.value, code = self.code, pin = self.pin, retailers = retailers)

        #error check for post tyep
        if not self.type:
           params['error_type'] = "*required" 
           have_error = True

        #error check for card value
        if not self.value:
            params['error_value'] = "*required"
            have_error = True

        #error chekc for card code
        if not self.code:
            params['error_code'] = "*required"
            have_error = True
        
        #error check for allowing only maximum of three retailers looking for - only for swap post
        if self.type == "swap":
            self.selected_rets = self.request.get('choices', allow_multiple=True)
            num_choices = len(self.selected_rets)
            if not self.selected_rets:
                params['error_retailers'] = "*required"
                have_error = True
            if num_choices > 3:
                params['error_retailers'] = "*select a maximum of three"
                have_error = True

        #error check for amount card offered for - only for sell post
        if self.type == "sell":
            self.val_offer = self.request.get('offer')
            if not self.val_offer:
                params['error_offer'] = "*required"
                have_error = True
            params['offer'] = self.val_offer


        if have_error: #if erro re-render page and how errors
            self.render("myposts_new.html", **params)
        else: 
            if self.type == "swap":
                choices = [0] * num_choices
                for i in range(0,num_choices):
                    choices[i] = str(self.selected_rets).split(',')[i].split("'")[1] #puts the looking for inputs in a list

                u = self.get_user() #get current user entity
                r = Retailer.by_ret_name(self.card_retailer) #get retailer entity using the name given
                p = SwapPost.register(u, r, self.value, self.code, self.pin, choices) #register new swap post entity
                p.put() #put entity in db

            elif self.type == "sell":
                u = self.get_user() #get current user entity
                r = Retailer.by_ret_name(self.card_retailer) #get retailer entilty using the name given
                p = SellPost.register(u, r, self.value, self.code, self.pin, self.val_offer) #register new sell post entity
                p.put()#put entity in db

            self.render("myposts_new_submitted.html") #render submission successful page
#-----------------------------------------------------------------------------------------------------------------#

#-------------------------------------------------MY BIDS HANDLER-------------------------------------------------#
#hanlder for rendering mybids page and  swapping gift cards between two users
class MyBidsHandler(Handler):
    def get(self):
        if self.user:
            posts = SwapPost.all().filter('owner =', self.user).filter('num_bids >', 0) #filter out posts with no bids
            posts = sorted(posts, key=SwapPost.getsortkey, reverse=True)

            bids = self.user.bidder_bids;   #get all bids by current user
            bids = sorted(bids, key=Bid_swap.getsortkey, reverse=True)

            self.render("mybids.html", posts = posts, bids = bids) #render page with bids and posts included
        else:   #if not logged in redirect
            self.redirect('/signin')

    #hanlder swap card form on pop up window
    def post(self):
        #no error check here, error checked by javascript
        b = self.request.get('selected_bid') #get the selected bid - radio button
        self.bid = Bid_swap.by_id(int(b))

        #get ownder of bid, bidder and post bidden on
        owner = self.bid.post_owner
        bidder = self.bid.bidder
        post_card = self.bid.on_post

        #set the status of winning bid and the post to swapped
        self.bid.on_post.status = 'Swapped' #change status of post
        self.bid.on_post.put()
        self.bid.status = 'Swapped' #chage status of bid
        self.bid.put()

        #decline all other bids
        others_bids = self.bid.on_post.post_bids #decline all other bids not picked by user
        for b in others_bids:
            if b.key().id() != self.bid.key().id():
                b.status = 'Declined' #update status to declined
                b.put()

        bidder.traded_with.append(owner.key().id()) #put bidder in owner's tradedwith list
        bidder.put()
        owner.traded_with.append(bidder.key().id()) #put ownder in bidder;s tradedwith list
        owner.put()

        #email both users for verifcation and include code and pin of new card
        message = mail.EmailMessage()
        message.sender = "accounts@reeegalo.appspotmail.com"
        message.to = bidder.email
        message.subject = "Transaction Successful! - Reeegalo"
        message.body = """Congratulations, %s!\n\nYou tranaction has been completed with %s. Here is the card info of the your new gift card\n\n\tRetailer: %s\n\tCard Code: %s \n\tCard PIN: %s\n\nThanks,\nThe Reeegalo Team""" % (bidder.user_name, owner.user_name, post_card.retailer.name, post_card.card_code, post_card.card_pin)
        message.send()
        message = mail.EmailMessage()
        message.sender = "accounts@reeegalo.appspotmail.com"
        message.to = owner.email
        message.subject = "Transaction Successful! - Reeegalo"
        message.body = """Congratulations, %s!\n\nYou tranaction has been completed with %s. Here is the card info of the your new gift card\n\n\tRetailer: %s\n\tCard Code: %s \n\tCard PIN: %s\n\nThanks,\nThe Reeegalo Team""" % (owner.user_name, bidder.user_name, self.bid.bid_retailer.name, self.bid.card_code, self.bid.card_pin)
        message.send()

        self.render('swap_sucess.html', b = self.bid) #render wap success page
#-----------------------------------------------------------------------------------------------------------------#

#---------------------------------------------------ABOUT HANDLER-------------------------------------------------#
#handler for about page, renders about page weather logged in or not
class AboutHandler(Handler):
    def get(self):
        if self.user: #if logged in - navigation bar
            self.render("about.html") 
        else:   #if not logged in - no navigation bar
            self.render("about-nouser.html")    
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------------HELP HANDLER-------------------------------------------------#
#handler for help page, renders help page weather logged in or not
class HelpHandler(Handler):
    #render help html page upon get request
    def get(self):
        if self.user:   #if logged if have naviagation bar
            self.render("help.html")
        else:   #if not logge in no navigation bar
            self.render("help-nouser.html")
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------------LOGOUT HANDLER-----------------------------------------------#
#logout handler class, uses login and logout function form Main handler class
class LogoutHandler(Handler):
    def get(self): #url /logout
        self.logout()   #remove cookie val
        self.redirect('/signin') #redirect
#-----------------------------------------------------------------------------------------------------------------#

#--------------------------------------------RETAILER REGISTRATION HANDLER----------------------------------------#
#retailer registration handler handler run once to register updates retailers to db
class RetRegHandler(Handler):
    def get(self):
        rets = Retailer.all()
        for r in rets:  #deletes the ones currently in db
           r.delete() 
        for ret in retailers:   #register and put all from the 'retailers' list defined above
            r = Retailer.register(ret)
            r.put()
        self.response.out.write("Retailers registered!")
#-----------------------------------------------------------------------------------------------------------------#

#-----------------------------------------------USERS PROFILE PAGE HANDLER----------------------------------------#
#handler for viewing other users profile page
class UsersPageHandler(Handler):
    def get(self, user_id):
        if not self.user:   #if not logged in redirect
            self.redirect('/signin')
        else:
            user = User.by_id(int(user_id)) #get user_id from permalink
            if not user:
                self.error(404)
                return

            if user.key().id() == self.user.key().id(): #if user_id is same as current user
                self.redirect('/myprofile')
                return 

            #determine which page to go back to when user clicks on back button on naviation bar
            get_values = self.request.GET
            backtourl = "browse"    #default
            backto = "Browse"   #default
            try:
                b = get_values['b']
                if b == 'mybids':
                    backtourl = "mybids"
                    backto = "My Bids"
                elif b == 'browse':
                    backtourl = "browse"
                    backto = "Browse"
                elif b == 'myprof':
                    backtourl = "myprofile"
                    backto = "My Profile"
            except KeyError:
                    backtourl = "browse" #default
                    backto = "Browse" #default

            allow_comment = 'no'   #allow comment is intially no
            traded_with = user.traded_with
            for u_id in traded_with:    #if you have already traded with the user you can see the 'add comment' button
                if self.user.key().id() == u_id:
                    allow_comment = 'yes'

            rev = user.reviewed_rev     #get reviews of user from db
            rev = sorted(rev, key=Review.getsortkey, reverse=True) 
            for r in rev: #even if you have already traded with, if you have already wrote a comment, 'add comment' button hidden
                if r.reviewer.key().id() == self.user.key().id():
                    allow_comment = 'no'

            posts1 = sorted(user.user_swapposts, key=SwapPost.getsortkey, reverse=True) 
            posts2 = sorted(user.user_sellposts, key=SellPost.getsortkey, reverse=True)

            self.render("users_page.html", u = user, posts = posts1, posts2 = posts2, backtourl = backtourl, backto = backto, allow = allow_comment, reviews = rev)

    #handles new review/comment form
    def post(self,u_id):
        user = User.by_id(int(u_id))
        if not user:
            self.error(404)
            return

        get_values = self.request.GET
        try:
            b = get_values['b']
            if b == 'mybids':
                backtourl = "mybids"
                backto = "My Bids"
            elif b == 'browse':
                backtourl = "browse"
                backto = "Browse"
            elif b == 'myprof':
                backtourl = "myprofile"
                backto = "My Profile"
        except KeyError:
            backtourl = "browse"
            backto = "Browse"

        allow_comment = 'no'

        rating = self.request.get('rate')
        title = self.request.get('rev_title')
        review = self.request.get('review_cont')

        r = Review.register(self.user, user, review, title, str(rating))
        r.put()

        if str(rating) == 'down':
            user.rating_d = user.rating_d + 1
        elif str(rating) == 'up':
            user.rating_u = user.rating_u + 1
        user.put()

        posts1 = sorted(user.user_swapposts, key=SwapPost.getsortkey, reverse=True) 
        posts2 = sorted(user.user_sellposts, key=SellPost.getsortkey, reverse=True)
        self.render('user_form_submitted.html', u = user, posts = posts1, posts2 = posts2, backtourl = backtourl, backto = backto, allow = allow_comment)
#-----------------------------------------------------------------------------------------------------------------#

#--------------------------------------------------SWAP BID PAGE HANDLER------------------------------------------#
#hanlder for a swap bid page where a user submites a new bid to a swap post
class SwapbidHandler(Handler):
    #render bid submission form upon get request
    def get(self):
        if not self.user: #if not logged in redirect
            self.redirect('/signin')
        else:
            try:
                get_values = self.request.GET
                self.post_id = get_values['p']  #get post id from url get parameters
            except KeyError:
                    self.error(404) #i no p, raise 404 error
                    return

            user = self.get_user(); #get currently logged in user
            self.post = SwapPost.by_id(int(self.post_id)) #get post entity from db using id given
            self.owner = self.post.owner    #get post owner

            if not self.owner or not self.post:
                self.error(404)
                return

            #render form
            self.render("bid_swap_form.html", o = self.owner, p = self.post, retailers = retailers)

    #new bid form handler
    def post(self):
        #get user inputs from form
        self.retailer = self.request.get('retailer')
        self.value = self.request.get('value')
        self.code = self.request.get('code')     
        self.pin = self.request.get('pin')

        have_error = False
        #save user inputs to keep them when re-rendering the page
        params = dict(value = self.value, code = self.code, pin = self.pin, retailers = retailers)

        #value and code are required - error check
        if not self.value or not self.code:
            have_error = True
            if not self.value:
                params['error_value'] = "*required"
            if not self.code:
                params['error_code'] = "*required"

        get_values = self.request.GET
        self.post_id = get_values['p']
        self.post = SwapPost.by_id(int(self.post_id))
        self.owner = self.post.owner

        if not self.owner or not self.post: #if post_id is invalid
            self.error(404)
            return

        self.ret = Retailer.by_ret_name(self.retailer) #get retailer
 
        if have_error: #if error re-render page
            params['o'] = self.owner
            params['p'] = self.post
            params['retailers'] = retailers
            self.render("bid_swap_form.html", **params)
        else:
            b = Bid_swap.register(self.user,self.owner,self.post,self.ret,self.value,self.code,self.pin) #register new bid by creating new entity
            b.put() #put new entity in db
            self.post.num_bids = self.post.num_bids + 1 #update # of bids submitted on current post
            self.post.put() #put post with update # of bids in db
            self.render("bid_swap_form_submitted.html") #render submission successful page
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------SWAP POPUP (AJAX) HANDLER------------------------------------------#
#handlers ajax load request during popup on mybids page
class SwapPopupHandler(Handler):
    def get(self):
        get_values = self.request.GET 
        p_id = get_values['id'] #get post_id from url
        p = SwapPost.by_id(int(p_id))
        self.response.out.write(p.render_bidpop(p.post_bids)) #return a string to be put in the pop up div
#-----------------------------------------------------------------------------------------------------------------#

#-----------------------------------------------RENDER REVIEWS(AJAX) HANDLER--------------------------------------#
#renders form for adding review
class RenderReviewFormHandler(Handler):
    def get(self):
        self.response.out.write(render_str('users_form.html')) #returns a html string - rete/review form

#//////////////////////////////////////////TEST/////////////////////////////////////
#test hanlder for handling incoming messages to server
class LogSenderHandler(InboundMailHandler):
    def receive(self, mail_message):
        logging.info("Received a message from: " + mail_message.sender)
#test application for recieving emails
app2 = webapp2.WSGIApplication([LogSenderHandler.mapping()], debug=True)
#//////////////////////////////////////TEST END/////////////////////////////////////


#attach urls to specific hanler classes 
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
    ('/logout', LogoutHandler),
    ('/retailersReg', RetRegHandler),
    ('/users/([0-9]+)', UsersPageHandler),
    ('/swapbid',SwapbidHandler),
    ('/popup-swap', SwapPopupHandler),
    ('/confirm/([a-zA-Z0-9]+)', ConfirmUserHandler),
    ('/usersform', RenderReviewFormHandler),
    ('/myprofile/edit', EditProfHandler),
    ('/myposts/editswap', EditSwapHandler)
    ], debug=True)


app.error_handlers[404] = handle_404
app.error_handlers[500] = handle_500

