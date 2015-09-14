# -*- coding: utf-8 -*-
"""
Created on Mon Sep 14 13:02:05 2015

@author: appel

Originally copied from:
http://tools.cherrypy.org/wiki/AuthenticationAndAccessRestrictions
"""

import cherrypy
import urllib

def print_enter(name):
    print '-'*len(name)
    print name
    print '-'*len(name)

SESSION_KEY = '_cp_username'

def check_credentials(username, password, auth_file_fn):
    """Verifies credentials for username and password.
    Returns None on success or a string describing the error on failure"""
    print_enter('check_credentials')
    import md5
    users = {}
    try:
        print 'Reading user dict...'
        with open(auth_file_fn, 'r') as auth_file:
            for line in auth_file:
                try:
                    user, passwd = line.split()
                    users[user] = passwd
                except ValueError:
                    pass
    except IOError:
        print 'Auth file not found'
        return 'Auth file not found'
    print 'Username:', username
    if username in users:
        if users[username] == password:
            print 'User/pass matched'
            return None
        else:
            print 'Trying MD5 hash...'
            password = md5.new(password).hexdigest()
            if users[username] == password:
                print 'User/pass matched'
                return None
            else:
                print 'Incorrect password'
                return 'Incorrect password'
    else:
        print 'Unknown user'
        return 'Unknown user'

def check_auth(*args, **kwargs):
    """A tool that looks in config for 'auth.require'. If found and it
    is not None, a login is required and the entry is evaluated as alist of
    conditions that the user must fulfill"""
    print_enter('check_auth')
    conditions = cherrypy.request.config.get('auth.require', None)
    # format GET params
    get_params = urllib.quote(cherrypy.request.request_line.split()[1])
    if conditions is not None:
        username = cherrypy.session.get(SESSION_KEY)
        if username:
            cherrypy.request.login = username
            for condition in conditions:
                # A condition is just a callable that returns true orfalse
                if not condition():
                    # Send old page as from_page parameter
                    raise cherrypy.HTTPRedirect("/auth/login?from_page=%s" % get_params)
        else:
            # Send old page as from_page parameter
            raise cherrypy.HTTPRedirect("/auth/login?from_page=%s" % get_params) 
    
cherrypy.tools.auth = cherrypy.Tool('before_handler', check_auth)

def require(*conditions):
    """A decorator that appends conditions to the auth.require config
    variable."""
    def decorate(f):
        if not hasattr(f, '_cp_config'):
            f._cp_config = dict()
        if 'auth.require' not in f._cp_config:
            f._cp_config['auth.require'] = []
        f._cp_config['auth.require'].extend(conditions)
        return f
    return decorate

def member_of(groupname):
    def check():
        # replace with actual check if <username> is in <groupname>
        #return cherrypy.request.login == 'joe' and groupname == 'admin'
        return False
    return check

def name_is(reqd_username):
    return lambda: reqd_username == cherrypy.request.login

# These might be handy

def any_of(*conditions):
    """Returns True if any of the conditions match"""
    def check():
        for c in conditions:
            if c():
                return True
        return False
    return check

# By default all conditions are required, but this might still be
# needed if you want to use it inside of an any_of(...) condition
def all_of(*conditions):
    """Returns True if all of the conditions match"""
    def check():
        for c in conditions:
            if not c():
                return False
        return True
    return check


# Controller to provide login and logout actions

class AuthController(object):
    
    def __init__(self, auth_file = '', head='', foot='', staticdir=''):
        from worknoteBookServer import StaticDir
        self.auth_file = auth_file
        self.head = head
        self.foot = foot
        self.staticdir = staticdir
        cherrypy.tree.mount(StaticDir(), '/auth/static', config = {'/': {
                    'tools.staticdir.on': True,
                    'tools.staticdir.root': self.staticdir,
                    'tools.staticdir.dir': '.'
                }})
        self.logged_in = None
    
    def on_login(self, username):
        """Called on successful login"""
        self.logged_in = username
    
    def on_logout(self, username):
        """Called on logout"""
        self.logged_in = None
    
    def get_loginform(self, username, msg="Enter login information", from_page="/"):
        print_enter('AuthController.get_loginform')
        head = self.head.format(metadata='<title>worknoteBook - Login</title>\n')
        foot = self.foot.format()
        frame = """{head:s}
            <form method="post" action="/auth/login">
            <input type="hidden" name="from_page" value="{from_page:s}" />
            {msg:s}<br/>
            Username: <input type="text" name="username" value="{username:s}" /><br />
            Password: <input type="password" name="password" /><br />
            <input type="submit" value="Log in" />
        {foot:s}"""
        return frame.format(head=head, foot=foot, from_page=from_page, 
                            msg=msg, username=username)
    
    @cherrypy.expose
    def login(self, username=None, password=None, from_page="/"):
        print_enter('AuthController.login')
        from base64 import b64decode
        if 'Python-urllib' in cherrypy.request.headers['User-Agent']:
            print 'CLI client header found'
            if 'Authorization' in cherrypy.request.headers:
                print 'Authorization header found, parsing...'
                auth_header = cherrypy.request.headers['Authorization']
                auth_header = b64decode(auth_header)
                username, password = auth_header.split(':')
            cli_client = True
        else:
            cli_client = False
        if username is None or password is None:
            if not cli_client:
                return self.get_loginform("", from_page=from_page)
            else:
                raise cherrypy.HTTPError("403 Forbidden", "Login needed for this action")
        print 'Username:', username
        print 'Checking credentials...'
        error_msg = check_credentials(username, password, self.auth_file)
        if error_msg:
            print 'Login unsuccessful'
            if not cli_client:
                return self.get_loginform(username, error_msg, from_page)
            else:
                raise cherrypy.HTTPError("403 Forbidden", "Login needed for this action")
        else:
            print 'Login successful'
            cherrypy.session.regenerate()
            cherrypy.session[SESSION_KEY] = cherrypy.request.login = username
            self.on_login(username)
            if not cli_client:
                raise cherrypy.HTTPRedirect(from_page or "/")
    
    @cherrypy.expose
    def logout(self, from_page="/"):
        print_enter('AuthController.logout')
        sess = cherrypy.session
        username = sess.get(SESSION_KEY, None)
        sess[SESSION_KEY] = None
        if username:
            cherrypy.request.login = None
            self.on_logout(username)
        raise cherrypy.HTTPRedirect(from_page or "/")