#!/usr/bin/python
"""
   Copyright 2012 23andMe, Inc.

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   
"""



import webbrowser
import requests
import flask
from flask import request

import getpass

from optparse import OptionParser

FLASK_PORT = 2323
DEFAULT_API_SERVER = "api.23andme.com"
BASE_CLIENT_URL = 'http://localhost:%s/'% FLASK_PORT
DEFAULT_REDIRECT_URI = '%safter_auth_landing/'  % BASE_CLIENT_URL
RSIDS_OF_INTEREST = ["rs12913832"]
DEFAULT_SCOPE = "names basic %s" % (" ".join(RSIDS_OF_INTEREST))
CLIENT_SECRET = None

parser = OptionParser(usage = "usage: %prog -i CLIENT_ID [options]")
parser.add_option("-i", "--client_id", dest="client_id",
                  help="Your client_id [REQUIRED]", default ='')

parser.add_option("-s", "--scope", dest="scope",
                  help="Your requested scope [%s]" % DEFAULT_SCOPE, default = DEFAULT_SCOPE)
parser.add_option("-r", "--redirect_uri", dest="redirect_uri",
                  help="Your client's redirect_uri [%s]" % DEFAULT_REDIRECT_URI, default = DEFAULT_REDIRECT_URI)
parser.add_option("-a", "--api_server", dest="api_server",
                  help="Almost always: [api.23andme.com]", default = DEFAULT_API_SERVER)
(options, args) = parser.parse_args()
BASE_API_URL = "https://%s/" % options.api_server
REDIRECT_URI = options.redirect_uri
CLIENT_ID = options.client_id

if not options.client_id:
    print "missing param: CLIENT_ID:"
    parser.print_usage()
    print "Please navigate to your developer dashboard [%sdashboard/] to retrieve your client_id.\n" % BASE_API_URL
    exit()

if not CLIENT_SECRET:
    print "Please navigate to your developer dashboard [%sdashboard/] to retrieve your client_secret." % BASE_API_URL
    CLIENT_SECRET = getpass.getpass("Please enter your client_secret:")

######## index ##############

#https://api.23andme.com/authorize/?redirect_uri=https://exampleapp.com/receive_code/&response_type=code&client_id=1&scope=basic


app = flask.Flask(__name__)

@app.route('/')
def index():
    auth_url = "%sauthorize/?response_type=code&redirect_uri=%s&client_id=%s&scope=%s" % (BASE_API_URL, REDIRECT_URI, CLIENT_ID, DEFAULT_SCOPE)
    return flask.render_template('index.html', auth_url = auth_url)

@app.route('/after_auth_landing/')
def after_auth_landing():
    parameters = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': request.args.get('code'),
        'redirect_uri': REDIRECT_URI,
        'scope': DEFAULT_SCOPE,
    }
    response = requests.post(
        "%s%s" % (BASE_API_URL, "token/"),
        data = parameters,
        verify=False,
    )

    if response.status_code == 200:
        #print response.JSON
        access_token, refresh_token = response.json['access_token'], response.json['refresh_token']
        #print "got the access & refresh token: %s %s" % (access_token, refresh_token)
        
        headers = {'Authorization': 'Bearer %s' % access_token}
        #print "get the genotypes"
        genotype_response = requests.get("%s%s" % (BASE_API_URL, "1/genotype/"),
                                         params = {'locations': ' '.join(RSIDS_OF_INTEREST)}, 
                                         headers=headers,
                                         verify=False)
        if genotype_response.status_code == 200:
            return flask.render_template('after_auth_landing.html', response_json = genotype_response.json)
        else:
            reponse_text = genotype_response.text
            response.raise_for_status()
    else:
        response.raise_for_status()
        
        
if __name__ == '__main__':
    print "A local client for the Personal Genome API is now initialized."
    app.run(debug=False, port=2323) 