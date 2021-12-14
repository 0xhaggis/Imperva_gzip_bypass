# Imperva Web Application Firewall (WAF) POST Request Bypass 
Imperva-protected HTTP(S) servers are vulnerable to a trivial bypass that allows malicious POST payloads, such as unobfuscated SQL injection, to evade detection. 

## To Exploit it
Add the header `Content-Encoding: gzip` to your POST requests. Leave your POST data as-is. Don't encode it! That's it; you can put literally anything for the content encoding so long as the first four characters are `gzip`. Imperva just passes it through.

You can do this in Burp by using the proxy's Match & Replace feature:

![](https://i.imgur.com/bNPA1MW.png)

Add a new header like this:

![](https://i.imgur.com/fJtQ8A1.png)

That's it; you're good to go.

# Running the Test Script
Run `imperva_gzip.py` against a URL that supports POST requests like this:

Syntax:
	`./imperva_gzip.py [[-t] | [-r]] URL`

Guess the WAF type for a given URL:
```
$ ./imperva_gzip.py -t https://www.vulnerable.com/search
Imperva Incapsula
$ ./imperva_gzip.py -t https://www.wordpress-user.com/login
WordFence
$ ./imperva_gzip.py -t https://www.cloudflare-customer.com
Cloudflare
```

Check to see if the WAF is vulnerable to the gzip bypass:
```
$ ./imperva_gzip.py https://www.vulnerable.com/search
[+] Can we make POST requests to https://www.vulnerable.com/search?
[+] Checking for Imperva WAF...
[+] Attempting gzip bypass for UNIX trigger...
[+] Vulnerable! HTTP response code: 200
[+] Attempting gzip bypass for Windows trigger...
[+] Vulnerable! HTTP response code: 200
```

If you get this error:
```
$ ./imperva_gzip.py https://www.vulnerable.com/search
[+] Can we make POST requests to https://www.vulnerable.com/search?
[!] Can't POST to https://www.vulnerable.com/search. Try -r if 30x redirects are allowed. HTTP response code: 302
```

then try passing `-r` on the command line to enable relaxed mode. Relaxed mode is off by default, which means a POST request is expected to elicit an HTTP 200 response from the server. `-r` expands the acceptable responses to HTTP 2xx, 3xx.

## Scripting
The exit codes for `imperva_gzip.py` are as follows:

```
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
```

## Process to Manually Test for Vulnerability
Send three POST requests:

1. Establish a baseline POST request/response with a valid but harmless POST request
2. Trigger the Imperva WAF using the same POST request, but with extra “malicious” data such as `&test=../../../../../../../etc/shadow` in the body to verify that Imperva blocks it
3. Add the header `Content-Encoding: gzip` to the same malicious request and verify that Imperva doesn't block it

## Other Encodings
According to https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Encoding, there are four valid values for the `Content-Encoding` header:

* `compress`
* `deflate`
* `gzip`
* `br`

In testing, only `gzip` appears to work as a bypass. I wonder if gzip is whitelisted for performance reasons?

## Affected Versions
I don't know. Version information isn't obvious with Imperva's WAF. What we do know is that this bug has previously been identified in a separate Imperva product called SecureSphere. The [release notes for v12.6 of SecureSphere](https://docs.imperva.com/bundle/v12.6-release-notes/page/64973.htm) contain this paragraph:

> SPHR-58185: When SecureSphere failed to decompress POST body in requests with "Content-Encoding: gzip/deflate" header, it issued no alert and let the request through.

This sounds like exactly the same bug! The issue was resolved for SecureSphere in February 2021, but we don't know when it was introduced. It's possible that the vulnerability has been there for years. Moreover, the same bug in two products from the same company implies a common codebase between WAF and SecureSphere. It's likely that there are other common security bugs in the two products. 

## Config issue or legit bug?
I did some research to see if there are any gzip configuration options in Imperva WAFs, but I couldn't find anything (as of this post). Add to that the commonality of the bug between products and my best guess is that this is a bug, not a feature or a configuration issue.

## Mitigating
Put a WAF on your WAF?

## Contact
* Author: [@carllivitt](https://twitter.com/carllivitt)
* Bishop Fox: [@bishopfox](https://twitter.com/bishopfox)
* Continuous Offensive Security: [Cosmos](https://bishopfox.com/platform)
