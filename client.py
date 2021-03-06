#!/usr/bin/python

import getpass
import requests
import flask
from flask import request, session, redirect, url_for, render_template

from optparse import OptionParser
import os

PORT = int(os.environ.get('PORT', 5000))
API_SERVER = "api.23andme.com"
BASE_CLIENT_URL = 'http://localhost:%s/'% PORT
#BASE_CLIENT_URL = 'http://gb-23andme-testapp.herokuapp.com/'
DEFAULT_REDIRECT_URI = '%sreceive_code/'  % BASE_CLIENT_URL
SNPS = ["rs3751812","rs10871777","rs13130484","rs4788102","rs10838738","rs3101336", "rs925946"]
DEFAULT_SCOPE = "basic names email %s" % (" ".join(SNPS))

CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
APP_SECRET_KEY = os.environ.get('APP_SECRET_KEY')

RK_URL = 'https://runkeeper.com/apps/'
RK_CLIENT_ID = os.environ.get('RK_CLIENT_ID')
RK_CLIENT_SECRET = os.environ.get('RK_CLIENT_SECRET')
RK_REDIRECT_URI = '%sreceive_rk_code/'% BASE_CLIENT_URL

# For command line launch of app #

parser = OptionParser(usage = "usage: %prog -i CLIENT_ID [options]")
parser.add_option("-i", "--client_id", dest="client_id",
        help="Your client_id [REQUIRED]", default = CLIENT_ID)
parser.add_option("-s", "--scope", dest="scope",
        help="Your requested scope [%s]" % DEFAULT_SCOPE, default = DEFAULT_SCOPE)
parser.add_option("-r", "--redirect_uri", dest="redirect_uri",
        help="Your client's redirect_uri [%s]" % DEFAULT_REDIRECT_URI, default = DEFAULT_REDIRECT_URI)
parser.add_option("-a", "--api_server", dest="api_server",
        help="Almost always: [api.23andme.com]", default = API_SERVER)

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


# App Functions #

#def bmi_from_call(call):
#        """Given a call string, tabulate the bmi difference."""
#        return call.count(allele) * bmi

#def genetic_bmi(self):
#        """Calculates total bmi difference due to SNPs for this profile."""
#        total_bmi = 0.0
#        for i,snp in enumerate(self.BMI_SNPS):
#            total_bmi += snp.bmi_from_call(self.calls[i])
#        return total_bmi

#def genetic_weight(self, height):
#        """Given a height, calculate the amount of weight accounted for by SNPs."""
#        height = int(height)
#        return (self.genetic_bmi * (height ** 2)) / 703.0

#def result_interpret(resp):
#    for p in resp:
#        if p['rs12913832'] == 'AG':
#            return "Het!"
#        else:
#            return "I don't know"

def obesity(resp):
    for p in resp:
        if p['rs925946'] == 'TT':
            return "slightly higher odds of obesity."
        elif p['rs925946'] == 'GT':
            return "typical odds of obesity."
        else:
            return "slightly lower odds of obesity."

def convert_to_lbs(weights):
    kgs = []
    pounds = []
    for entry in weights:
        kgs.insert(0, entry['weight'])
    for weight in kgs:
        pounds.insert(0, round((weight*2.20462), 0))
    return pounds



app = flask.Flask(__name__)
app.secret_key = APP_SECRET_KEY

@app.route('/')
def index():
    auth_url = "%sauthorize/?response_type=code&redirect_uri=%s&client_id=%s&scope=%s" % (BASE_API_URL, REDIRECT_URI, CLIENT_ID, DEFAULT_SCOPE)
    if 'access_token' in session:
        return redirect(url_for('results'))
    else:
        return render_template('index.html', auth_url = auth_url)

@app.route('/receive_code/')
def receive_code():
    if request.args:
        parameters = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': request.args.get('code'),
            'redirect_uri': REDIRECT_URI,
            'scope': DEFAULT_SCOPE
        }

    else:
        parameters = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': session['refresh_token'],
            'redirect_uri': REDIRECT_URI,
            'scope': DEFAULT_SCOPE
        }

    response = requests.post(
        "%s%s" % (BASE_API_URL, "token/"),
        data = parameters,
        verify=False
    )

    if response.status_code == 200:
        access_token, refresh_token = response.json()['access_token'], response.json()['refresh_token']
        session['access_token'] = access_token
        session['refresh_token'] = refresh_token
        return redirect(url_for('results'))

    else:
        return redirect(url_for('index'))

@app.route('/results/')
def results():
    headers = {'Authorization': 'Bearer %s' % session['access_token']}
    genotype_response = requests.get("%s%s" % (BASE_API_URL, "1/genotype/"),
                                        params = {'locations': " ".join(SNPS)},
                                        headers=headers,
                                        verify=False)

    if genotype_response.status_code != 200:
        return redirect(url_for('receive_code'))

    #result = result_interpret(genotype_response.json)

    name_response = requests.get("%s%s" % (BASE_API_URL, "3/account/"),
                                        headers=headers,
                                        verify=False)

    rk_auth_url = "%sauthorize/?response_type=code&redirect_uri=%s&client_id=%s" % (RK_URL, RK_REDIRECT_URI, RK_CLIENT_ID)

    if genotype_response.status_code == 200:
        return render_template('landing.html', response_json = genotype_response.json(), name_json = name_response.json(), rk_auth_url = rk_auth_url)
        #return "It's the template stupid"
    else:
        return redirect(url_for('receive_code'))

@app.route('/badtoken/') #for testing refresh_token
def bad_token():
    session['access_token'] = '3eeefeff47cc3588d8a4979d3fbc56e7'
    # return redirect(url_for('receive_code'))
    return redirect(url_for('results'))

#Runkeeper

@app.route('/runkeeper/')
def runkeeper():
    #rk_auth_url = "%sauthorize/?response_type=code&redirect_uri=%s&client_id=%s" % (RK_URL, RK_REDIRECT_URI, RK_CLIENT_ID)
    #return render_template('index.html', rk_auth_url = rk_auth_url)
    return "delete the cookie"

@app.route('/receive_rk_code/')
def receive_rk_code():
    parameters = {
        'client_id': RK_CLIENT_ID,
        'client_secret': RK_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': request.args.get('code'),
        'redirect_uri': RK_REDIRECT_URI,
        }

    response = requests.post(
        "https://runkeeper.com/apps/token",
        data = parameters,
        verify=False
    )

    if response.status_code == 200:
        rk_access_token = response.json['access_token']
        session['rk_access_token'] = rk_access_token
        return redirect(url_for('combined_results'))
    else:
        return redirect(url_for('index'))

@app.route('/combined-results/')
def combined_results():
    rk_headers = {'Authorization': 'Bearer %s' % session['rk_access_token'], 'Accept': 'application/vnd.com.runkeeper.WeightSetFeed+json'}
    runkeeper_response = requests.get("https://api.runkeeper.com/weight/",
                                        headers=rk_headers,
                                        verify=False)

    rk_fit_headers = {'Authorization': 'Bearer %s' % session['rk_access_token'], 'Accept': 'application/vnd.com.runkeeper.FitnessActivityFeed+json'}
    runkeeper_fit_response = requests.get("https://api.runkeeper.com/fitnessActivities/",
                                        headers=rk_fit_headers,
                                        verify=False)

    headers = {'Authorization': 'Bearer %s' % session['access_token']}
    genotype_response = requests.get("%s%s" % (BASE_API_URL, "1/genotype/"),
                                        params = {'locations': " ".join(SNPS)},
                                        headers=headers,
                                        verify=False)

    name_response = requests.get("%s%s" % (BASE_API_URL, "1/names/"),
                                        headers=headers,
                                        verify=False)

    if genotype_response.status_code != 200:
        return redirect(url_for('receive_code'))

    items = runkeeper_response.json[u'items']
    fit_items = runkeeper_fit_response.json[u'items']
    obesity_results = obesity(genotype_response.json)
    weight_results = convert_to_lbs(items)


    if runkeeper_response.status_code == 200 and genotype_response.status_code == 200:
        #return "%s"% runkeeper_response.json[u'items'][0][u'weight']
        #return "%s%s" % (runkeeper_response.json, genotype_response.json)
        return render_template('combined.html', genotype_json = genotype_response.json, rk_items = items, name_json = name_response.json, obesity_results = obesity_results, weight_results = weight_results, fit_items = fit_items)


if __name__ == '__main__':
    print "A local client for the Personal Genome API is now initialized."
    app.run(debug=False, host='0.0.0.0', port=PORT)
