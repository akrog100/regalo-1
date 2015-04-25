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

#RETAILERS SUPPORTED
retailers=("Applebees", "Best-Buy","Body-Shop","Chipotle","CVS","Dominos-Pizza","Dunkin-Donuts","Forever-21","Papa-Johns","WalMart")

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

def make_email_hash(name, email):
    h = hashlib.sha256(name + email).hexdigest()
    return "%s" % (h)
#---------------------------------------
    
#------------------------------------------------ERROR HANDLER---------------------------------------------------#
def handle_404(request, response, exception):
    logging.exception(exception)
    response.write(render_str('404.html'));
    response.set_status(404)

def handle_500(request, response, exception):
    logging.exception(exception)
    response.write(render_str('500.html'));
    response.set_status(500)
#-----------------------------------------------------------------------------------------------------------------#

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
    traded_with = db.ListProperty(int, required = True)
    rating_u = db.IntegerProperty(required=True)
    rating_d = db.IntegerProperty(required=True)


    auth_token = db.StringProperty(required = True)
    confirmed = db.BooleanProperty(required = True)

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
        email_hash = make_email_hash(u_name, email)
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
    def login(cls, u_name, pw):
        user = cls.by_username(u_name)
        if user and user.confirmed and valid_pw(u_name, pw, user.pass_hash):
            return user
#-----------------------------------------------------------------------------------------------------------------#

#---------------------------------------------------SWAP POST DB--------------------------------------------------#
class SwapPost(db.Model):
    owner = db.ReferenceProperty(User,collection_name='user_swapposts')
    retailer = db.ReferenceProperty(Retailer, collection_name='ret_swapposts')
    card_val = db.StringProperty(required=True)
    card_code = db.StringProperty(required = True)
    card_pin = db.StringProperty()
    looking_for = db.ListProperty(str,required= True)
    created = db.DateTimeProperty(auto_now_add = True)
    num_bids = db.IntegerProperty()
    status = db.StringProperty()


    @classmethod
    def register(cls, owner, ret, val, code, pin, choices):
        return SwapPost(owner = owner, retailer = ret, card_val = val, card_code = code, card_pin = pin, looking_for = choices, num_bids = 0, status = "Active")

    @classmethod
    def by_id(cls, pid):
        return SwapPost.get_by_id(pid)

    def render(self):
        return render_str("post_swap.html", p = self)

    def render_myposts(self):
        return render_str("post_swap_myposts.html", p = self)

    def render_prof(self):
        return render_str("post_swap_prof.html", p = self, type="swap")

    def render_bidpage(self, bids):
        return render_str("post_swap_bidpage.html", p = self, bids = bids )

    def render_bidpop(self, bids):
        return render_str("post_swap_bidpop.html", p = self, bids = bids )

    def getsortkey(post):
        return post.created
#-----------------------------------------------------------------------------------------------------------------#

#---------------------------------------------------SWAP POST DB--------------------------------------------------#
class SellPost(db.Model):
    owner = db.ReferenceProperty(User,collection_name='user_sellposts')
    retailer = db.ReferenceProperty(Retailer, collection_name='ret_sellposts')
    card_val = db.StringProperty(required=True)
    card_code = db.StringProperty(required = True)
    card_pin = db.StringProperty()
    offer_for = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add = True)
    num_bids = db.IntegerProperty()



    @classmethod
    def register(cls, owner, ret, val, code, pin, val_offer):
        return SellPost(owner = owner, retailer = ret, card_val = val, card_code = code, card_pin = pin, offer_for = val_offer, num_bids = 0)

    @classmethod
    def by_id(cls, pid):
        return SellPost.get_by_id(pid)

    def render(self):
        return render_str("post_sell.html", p = self)

    def render_prof(self): #render posts on profile page
        return render_str("post_sell_prof.html", p = self)

    def getsortkey(post): #used for sorting
        return post.created
#-----------------------------------------------------------------------------------------------------------------#

#---------------------------------------------------REVIEWS DB----------------------------------------------------#
class Review(db.Model):
    reviewer = db.ReferenceProperty(User,collection_name='reviewer_rev') #reviewer
    reviewed = db.ReferenceProperty(User,collection_name='reviewed_rev') #person being reviewed
    revcontent = db.TextProperty(required = True)
    title = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    rating = db.StringProperty(required = True)

    @classmethod
    def register(cls, reviewer_u, reviewed_u, rev_cont_u, title_u, rating_u):
        return Review(reviewer = reviewer_u, reviewed = reviewed_u, revcontent = rev_cont_u, title = title_u, rating = rating_u)

    def render_users(self):
        return render_str("reviews_myprof.html", r = self)

    def render_myprof(self):
        return render_str("reviews_myprof.html", r = self)
#-----------------------------------------------------------------------------------------------------------------#

#---------------------------------------------------REVIEWS DB----------------------------------------------------#
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

    def render(self):
        return render_str("bid_swap_bidpage.html", b = self)

    def render_pop(self):
        return render_str("bid_swap_bidpop.html", b = self)

    def render_mybid(self):
        return render_str("bid_swap_mybid.html", b = self)

    def getsortkey(post): #used for sorting
        return post.created
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

    def error(self,err):
        if (err == 404):
            self.render('404.html')
        elif (err == 500):
            self.render('500.html')

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
            #self.login(user)
            #self.redirect("/browse")
            auth_url = 'http://reeegalo.appspot.com/confirm/%s?u=%s' % (user.auth_token,user.key().id())
            message = mail.EmailMessage()
            message.sender = "accounts@reeegalo.appspotmail.com"
            message.to = self.email
            message.subject = "Account Registeration Successful! - Reeegalo"
            message.body = """ Welcome, %s!\n\nYour reeegalo.appspot.com account has been approved. Please got to the following link %s to veify your email adress.You can then visit http://reeegalo.appspot.com/ and sign in using your account to access its features.\n\nThe Reeegalo Team""" % (self.first_name, auth_url)
            message.send()
            self.render('register-success.html')
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

#----------------------------------------------CONFRIM EMAIL HANDLER----------------------------------------------#
class ConfirmUserHandler(Handler):
    def get(self,token):
        get_values = self.request.GET
        u_id = int(get_values['u'])
        u = User.by_id(u_id)
        if not u.confirmed and u and u.auth_token == str(token):
            u.confirmed = True
            u.put()
            self.render('email-confirmed.html')
        else:
            self.error(404)
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------FRONT PAGE HANDLER-------------------------------------------------#
class FrontPageHandler(Handler):
    def get(self):   
        self.render("frontpage.html")
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------FRONT PAGE HANDLER-------------------------------------------------#
class BrowseHandler(Handler):
    def get(self):
        if self.user:
            get_values = self.request.GET
            t = None
            try:
                t = get_values['type']
            except KeyError:
                pass

            u = self.user
            posts_swap = SwapPost.all().filter('owner !=', u).filter('status ==', 'Active')
            posts_sell = SellPost.all().filter('owner !=', u)
            if not t or t == '1':
                self.render('browse_swap.html', posts = sorted(posts_swap, key=SwapPost.getsortkey, reverse=True))
            elif t == '2':
                self.render('browse_sell.html', posts = sorted(posts_sell, key=SellPost.getsortkey, reverse=True))
            else:
                self.error(404)
                return
        else:
            self.redirect('/signin')
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------MY PROFILE HANDLER-------------------------------------------------#
class MyProfileHandler(Handler):
    def get(self):
        if self.user: 
            posts1 = sorted(self.user.user_swapposts, key=SwapPost.getsortkey, reverse=True) 
            posts2 = sorted(self.user.user_sellposts, key=SellPost.getsortkey, reverse=True) 

            self.render("myprofile.html", u = self.user, posts = posts1, posts2 = posts2)
        else:
            self.redirect('/signin')
#-----------------------------------------------------------------------------------------------------------------#

#------------------------------------------------MY POSTS HANDLER-------------------------------------------------#
class MyPostsHandler(Handler):
    def get(self):
        if self.user:
            get_values = self.request.GET
            t = None
            try:
                t = get_values['type']
            except KeyError:
                pass
            u = self.user
            if not t  or t == '1':
                #posts = Post.all().filter('owner =', u)
                posts = u.user_swapposts
                self.render('myposts_swap.html', posts = sorted(posts, key=SwapPost.getsortkey, reverse=True))

            elif t == '2':
                posts = u.user_sellposts
                self.render('myposts_sell.html', posts = sorted(posts, key=SellPost.getsortkey, reverse=True))
            else:
                self.error(404)
                return
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
        self.type = self.request.get('type')
        self.card_retailer = self.request.get('retailer')
        self.value = self.request.get('value')
        self.code = self.request.get('code')
        self.pin = self.request.get('pin')

        params = dict(value = self.value, code = self.code, pin = self.pin, retailers = retailers)
        if not self.type:
           params['error_type'] = "*required" 
           have_error = True

        if not self.value:
            params['error_value'] = "*required"
            have_error = True

        if not self.code:
            params['error_code'] = "*required"
            have_error = True
        
        if self.type == "swap":
            self.selected_rets = self.request.get('choices', allow_multiple=True)
            num_choices = len(self.selected_rets)
            if not self.selected_rets:
                params['error_retailers'] = "*required"
                have_error = True
            if num_choices > 3:
                params['error_retailers'] = "*select a maximum of three"
                have_error = True

        if self.type == "sell":
            self.val_offer = self.request.get('offer')
            if not self.val_offer:
                params['error_offer'] = "*required"
                have_error = True
            params['offer'] = self.val_offer


        if have_error:
            self.render("myposts_new.html", **params)
        else: 
            if self.type == "swap":
                choices = [0] * num_choices
                for i in range(0,num_choices):
                    choices[i] = str(self.selected_rets).split(',')[i].split("'")[1]

                u = self.get_user()
                r = Retailer.by_ret_name(self.card_retailer)
                p = SwapPost.register(u, r, self.value, self.code, self.pin, choices)
                p.put()

            elif self.type == "sell":
                u = self.get_user()
                r = Retailer.by_ret_name(self.card_retailer)
                p = SellPost.register(u, r, self.value, self.code, self.pin, self.val_offer)
                p.put()

            self.render("myposts_new_submitted.html")
#-----------------------------------------------------------------------------------------------------------------#

#-------------------------------------------------MY BIDS HANDLER-------------------------------------------------#
class MyBidsHandler(Handler):
    def get(self):
        if self.user:
            posts = SwapPost.all().filter('owner =', self.user).filter('num_bids >', 0)
            posts = sorted(posts, key=SwapPost.getsortkey, reverse=True)

            bids = self.user.bidder_bids;
            bids = sorted(bids, key=Bid_swap.getsortkey, reverse=True)

            self.render("mybids.html", posts = posts, bids = bids)
        else:
            self.redirect('/signin')

    def post(self):
        b = self.request.get('selected_bid')
        self.bid = Bid_swap.by_id(int(b))

        owner = self.bid.post_owner
        bidder = self.bid.bidder
        post_card = self.bid.on_post

        #set the status of winning bid and the post to swapped
        self.bid.on_post.status = 'Swapped'
        self.bid.on_post.put()
        self.bid.status = 'Swapped'
        self.bid.put()

        #decline all other bids
        others_bids = self.bid.on_post.post_bids
        for b in others_bids:
            if b.key().id() != self.bid.key().id():
                b.status = 'Declined'
                b.put()

        bidder.traded_with.append(owner.key().id())
        bidder.put()
        owner.traded_with.append(bidder.key().id())
        owner.put()

        #email both users
        message = mail.EmailMessage()
        message.sender = "accounts@reeegalo.appspotmail.com"
        message.to = bidder.email
        message.subject = "Transaction Successful! - Reeegalo"
        message.body = """Congratulations, %s!\n\nYou tranaction has been completed with %s. Here is the card info of the your new gift card\n\n\tRetailer:%s\n\tCard Code: %s \n\tCard PIN: %s\n\nThanks,\nThe Reeegalo Team""" % (bidder.user_name, owner.user_name, post_card.retailer.name, post_card.card_code, post_card.card_pin)
        
        message.send()
        message = mail.EmailMessage()
        message.sender = "accounts@reeegalo.appspotmail.com"
        message.to = owner.email
        message.subject = "Transaction Successful! - Reeegalo"
        message.body = """Congratulations, %s!\n\nYou tranaction has been completed with %s. Here is the card info of the your new gift card\n\n\tRetailer:%s\n\tCard Code: %s \n\tCard PIN: %s\n\nThanks,\nThe Reeegalo Team""" % (owner.user_name, bidder.user_name, self.bid.bid_retailer.name, self.bid.card_code, self.bid.card_pin)
        message.send()

        self.render('swap_sucess.html', b = self.bid)
#-----------------------------------------------------------------------------------------------------------------#

#---------------------------------------------------ABOUT HANDLER-------------------------------------------------#
class AboutHandler(Handler):
    def get(self):
        if self.user:
            self.render("about.html") 
        else:
            self.render("about-nouser.html")    
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------------HELP HANDLER-------------------------------------------------#
class HelpHandler(Handler):
    def get(self):
        if self.user:
            self.render("help.html")
        else:
            self.render("help-nouser.html")
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------------LOGOUT HANDLER-----------------------------------------------#
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
        self.response.out.write("Retailers registered!")
#-----------------------------------------------------------------------------------------------------------------#

#-----------------------------------------------USERS PROFILE PAGE HANDLER----------------------------------------#
class UsersPageHandler(Handler):
    def get(self, user_id):
        user = User.by_id(int(user_id))
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
        traded_with = user.traded_with
        for u_id in traded_with:
            if self.user.key().id() == u_id:
                allow_comment = 'yes'

        rev = user.reviewed_rev
        for r in rev:
            if r.reviewer.key().id() == self.user.key().id():
                allow_comment = 'no'

        posts1 = sorted(user.user_swapposts, key=SwapPost.getsortkey, reverse=True) 
        posts2 = sorted(user.user_sellposts, key=SellPost.getsortkey, reverse=True)

        self.render("users_page.html", u = user, posts = posts1, posts2 = posts2, backtourl = backtourl, backto = backto, allow = allow_comment, reviews = rev)

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
class SwapbidHandler(Handler):
    def get(self):
        if not self.user:
            self.redirect('/signin')
        else:
            user = self.get_user();
            get_values = self.request.GET
            self.post_id = get_values['p']
            self.owner_id = get_values['o']
            self.owner = User.by_id(int(self.owner_id))
            self.post = SwapPost.by_id(int(self.post_id))
            if not self.owner or not self.post:
                self.error(404)
                return
            self.render("bid_swap_form.html", o = self.owner, p = self.post, retailers = retailers)

    def post(self):
        self.retailer = self.request.get('retailer')
        self.value = self.request.get('value')
        self.code = self.request.get('code')     
        self.pin = self.request.get('pin')

        have_error = False
        params = dict(value = self.value, code = self.code, pin = self.pin, retailers = retailers)

        if not self.value or not self.code:
            have_error = True
            if not self.value:
                params['error_value'] = "*required"
            if not self.code:
                params['error_code'] = "*required"

        get_values = self.request.GET
        self.post_id = get_values['p']
        self.owner_id = get_values['o']
        self.owner = User.by_id(int(self.owner_id))
        self.post = SwapPost.by_id(int(self.post_id))

        if not self.owner or not self.post:
            self.error(404)
            return

        self.ret = Retailer.by_ret_name(self.retailer)

        if have_error:
            params['o'] = self.owner
            params['p'] = self.post
            params['retailers'] = retailers
            self.render("bid_swap_form.html", **params)
        else:
            b = Bid_swap.register(self.user,self.owner,self.post,self.ret,self.value,self.code,self.pin)
            b.put()
            self.post.num_bids = self.post.num_bids + 1
            self.post.put()
            self.render("bid_swap_form_submitted.html")
#-----------------------------------------------------------------------------------------------------------------#

#----------------------------------------------------SWAP POPUP HANDLER-------------------------------------------#
class SwapPopupHandler(Handler):
    def get(self):
        get_values = self.request.GET
        p_id = get_values['id']
        p = SwapPost.by_id(int(p_id))
        self.response.out.write(p.render_bidpop(p.post_bids))
#-----------------------------------------------------------------------------------------------------------------#

class RenderReviewFormHandler(Handler):
    def get(self):
        self.response.out.write(render_str('users_form.html'))

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

app2 = webapp2.WSGIApplication([LogSenderHandler.mapping()], debug=True)
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
    ('/swapbid',SwapbidHandler),
    ('/popup-swap', SwapPopupHandler),
    ('/confirm/([a-zA-Z0-9]+)', ConfirmUserHandler),
    ('/usersform', RenderReviewFormHandler)
    ], debug=True)


app.error_handlers[404] = handle_404
app.error_handlers[500] = handle_500

