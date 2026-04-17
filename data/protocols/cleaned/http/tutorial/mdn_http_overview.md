# Source Metadata
- protocol: http
- kind: tutorial
- source_file: mdn_http_overview.html
- source_url: https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview

Overview of HTTP - HTTP | MDN

 Skip to main content

 Skip to search

 MDN

 HTML

 HTML: Markup language

 HTML reference

 Elements

 Global attributes

 Attributes

 See all…

 HTML guides

 Responsive images

 HTML cheatsheet

 Date & time formats

 See all…

 Markup languages

 SVG

 MathML

 XML

 CSS

 CSS: Styling language

 CSS reference

 Properties

 Selectors

 At-rules

 Values

 See all…

 CSS guides

 Box model

 Animations

 Flexbox

 Colors

 See all…

 Layout cookbook

 Column layouts

 Centering an element

 Card component

 See all…

 JavaScript JS

 JavaScript: Scripting language

 JS reference

 Standard built-in objects

 Expressions & operators

 Statements & declarations

 Functions

 See all…

 JS guides

 Control flow & error handing

 Loops and iteration

 Working with objects

 Using classes

 See all…

 Web APIs

 Web APIs: Programming interfaces

 Web API reference

 File system API

 Fetch API

 Geolocation API

 HTML DOM API

 Push API

 Service worker API

 See all…

 Web API guides

 Using the Web animation API

 Using the Fetch API

 Working with the History API

 Using the Web speech API

 Using web workers

 All

 All web technology

 Technologies

 Accessibility

 HTTP

 URI

 Web extensions

 WebAssembly

 WebDriver

 See all…

 Topics

 Media

 Performance

 Privacy

 Security

 Progressive web apps

 Learn

 Learn web development

 Frontend developer course

 Getting started modules

 Core modules

 MDN Curriculum

 Check out the video course from Scrimba, our partner

 Learn HTML

 Structuring content with HTML module

 Learn CSS

 CSS styling basics module

 CSS layout module

 Learn JavaScript

 Dynamic scripting with JavaScript module

 Tools

 Discover our tools

 Playground

 HTTP Observatory

 Border-image generator

 Border-radius generator

 Box-shadow generator

 Color format converter

 Color mixer

 Shape generator

 About

 Get to know MDN better

 About MDN

 Advertise with us

 Community

 MDN on GitHub

 Blog

 Toggle sidebar

 Web

 HTTP

 Guides

 Overview of HTTP

 Theme

 OS default

 Light

 Dark

 English (US)

 Remember language

 Learn more

 Deutsch

 English (US)

 Español

 Français

 日本語

 한국어

 Português (do Brasil)

 Русский

 中文 (简体)

 Overview of HTTP

 HTTP is a protocol for fetching resources such as HTML documents.
It is the foundation of any data exchange on the Web and it is a client-server protocol, which means requests are initiated by the recipient, usually the Web browser.
A complete document is typically constructed from resources such as text content, layout instructions, images, videos, scripts, and more.

 Clients and servers communicate by exchanging individual messages (as opposed to a stream of data).
The messages sent by the client are called requests and the messages sent by the server as an answer are called responses .

 Designed in the early 1990s, HTTP is an extensible protocol which has evolved over time.
It is an application layer protocol that is sent over TCP , or over a TLS -encrypted TCP connection, though any reliable transport protocol could theoretically be used.
Due to its extensibility, it is used to not only fetch hypertext documents, but also images and videos or to post content to servers, like with HTML form results.
HTTP can also be used to fetch parts of documents to update Web pages on demand.

 In this article

 Components of HTTP-based systems
 Basic aspects of HTTP
 What can be controlled by HTTP
 HTTP flow
 HTTP Messages
 APIs based on HTTP
 Conclusion
 See also

 Components of HTTP-based systems

 HTTP is a client-server protocol: requests are sent by one entity, the user-agent (or a proxy on behalf of it).
Most of the time the user-agent is a Web browser, but it can be anything, for example, a robot that crawls the Web to populate and maintain a search engine index.

 Each individual request is sent to a server, which handles it and provides an answer called the response .
Between the client and the server there are numerous entities, collectively called proxies , which perform different operations and act as gateways or caches , for example.

 In reality, there are more computers between a browser and the server handling the request: there are routers, modems, and more.
Thanks to the layered design of the Web, these are hidden in the network and transport layers.
HTTP is on top, at the application layer.
Although important for diagnosing network problems, the underlying layers are mostly irrelevant to the description of HTTP.

 Client: the user-agent

 The user-agent is any tool that acts on behalf of the user.
This role is primarily performed by the Web browser, but it may also be performed by programs used by engineers and Web developers to debug their applications.

 The browser is always the entity initiating the request.
It is never the server (though some mechanisms have been added over the years to simulate server-initiated messages).

 To display a Web page, the browser sends an original request to fetch the HTML document that represents the page.
It then parses this file, making additional requests corresponding to execution scripts, layout information (CSS) to display, and sub-resources contained within the page (usually images and videos).
The Web browser then combines these resources to present the complete document, the Web page.
Scripts executed by the browser can fetch more resources in later phases and the browser updates the Web page accordingly.

 A Web page is a hypertext document.
This means some parts of the displayed content are links, which can be activated (usually by a click of the mouse) to fetch a new Web page, allowing the user to direct their user-agent and navigate through the Web.
The browser translates these directions into HTTP requests, and further interprets the HTTP responses to present the user with a clear response.

 The Web server

 On the opposite side of the communication channel is the server, which serves the document as requested by the client.
A server appears as only a single machine virtually; but it may actually be a collection of servers sharing the load (load balancing), or other software (such as caches, a database server, or e-commerce servers), totally or partially generating the document on demand.

 A server is not necessarily a single machine, but several server software instances can be hosted on the same machine.
With HTTP/1.1 and the Host header, they may even share the same IP address.

 Proxies

 Between the Web browser and the server, numerous computers and machines relay the HTTP messages.
Due to the layered structure of the Web stack, most of these operate at the transport, network or physical levels, becoming transparent at the HTTP layer and potentially having a significant impact on performance.
Those operating at the application layers are generally called proxies .
These can be transparent, forwarding on the requests they receive without altering them in any way, or non-transparent, in which case they will change the request in some way before passing it along to the server.
Proxies may perform numerous functions:

 caching (the cache can be public or private, like the browser cache)

 filtering (like an antivirus scan or parental controls)

 load balancing (to allow multiple servers to serve different requests)

 authentication (to control access to different resources)

 logging (allowing the storage of historical information)

 Basic aspects of HTTP

 HTTP is simple

 HTTP is generally designed to be human-readable, even with the added complexity introduced in HTTP/2 by encapsulating HTTP messages into frames.
HTTP messages can be read and understood by humans, providing easier testing for developers, and reduced complexity for newcomers.

 HTTP is extensible

 Introduced in HTTP/1.0, HTTP headers make this protocol easy to extend and experiment with.
New functionality can even be introduced by an agreement between a client and a server about a new header's semantics.

 HTTP is stateless, but not sessionless

 HTTP is stateless: there is no link between two requests being successively carried out on the same connection.
This immediately has the prospect of being problematic for users attempting to interact with certain pages coherently, for example, using e-commerce shopping baskets.
But while the core of HTTP itself is stateless, HTTP cookies allow the use of stateful sessions.
Using header extensibility, HTTP Cookies are added to the workflow, allowing session creation on each HTTP request to share the same context, or the same state.

 HTTP and connections

 A connection is controlled at the transport layer, and therefore fundamentally out of scope for HTTP.
HTTP doesn't require the underlying transport protocol to be connection-based; it only requires it to be reliable , or not lose messages (at minimum, presenting an error in such cases).
Among the two most common transport protocols on the Internet, TCP is reliable and UDP isn't.
HTTP therefore relies on the TCP standard, which is connection-based.

 Before a client and server can exchange an HTTP request/response pair, they must establish a TCP connection, a process which requires several round-trips.
The default behavior of HTTP/1.0 is to open a separate TCP connection for each HTTP request/response pair.
This is less efficient than sharing a single TCP connection when multiple requests are sent in close succession.

 In order to mitigate this flaw, HTTP/1.1 introduced pipelining (which proved difficult to implement) and persistent connections : the underlying TCP connection can be partially controlled using the Connection header.
HTTP/2 went a step further by multiplexing messages over a single connection, helping keep the connection warm and more efficient.

 Experiments are in progress to design a better transport protocol more suited to HTTP.
For example, Google is experimenting with QUIC which builds on UDP to provide a more reliable and efficient transport protocol.

 What can be controlled by HTTP

 This extensible nature of HTTP has, over time, allowed for more control and functionality of the Web.
Cache and authentication methods were functions handled early in HTTP history.
The ability to relax the origin constraint , by contrast, was only added in the 2010s.

 Here is a list of common features controllable with HTTP:

 Caching :
How documents are cached can be controlled by HTTP.
The server can instruct proxies and clients about what to cache and for how long.
The client can instruct intermediate cache proxies to ignore the stored document.

 Relaxing the origin constraint :
To prevent snooping and other privacy invasions, Web browsers enforce strict separation between websites.
Only pages from the same origin can access all the information of a Web page.
Though such a constraint is a burden to the server, HTTP headers can relax this strict separation on the server side, allowing a document to become a patchwork of information sourced from different domains; there could even be security-related reasons to do so.

 Authentication :
Some pages may be protected so that only specific users can access them.
Basic authentication may be provided by HTTP, either using the WWW-Authenticate and similar headers, or by setting a specific session using HTTP cookies .

 Proxy and tunneling :
Servers or clients are often located on intranets and hide their true IP address from other computers.
HTTP requests then go through proxies to cross this network barrier.
Not all proxies are HTTP proxies.
The SOCKS protocol, for example, operates at a lower level.
Other protocols, like FTP, can be handled by these proxies.

 Sessions :
Using HTTP cookies allows you to link requests with the state of the server.
This creates sessions, despite basic HTTP being a state-less protocol.
This is useful not only for e-commerce shopping baskets, but also for any site allowing user configuration of the output.

 HTTP flow

 When a client wants to communicate with a server, either the final server or an intermediate proxy, it performs the following steps:

 Open a TCP connection: The TCP connection is used to send a request, or several, and receive an answer.
The client may open a new connection, reuse an existing connection, or open several TCP connections to the servers.

 Send an HTTP message: HTTP messages (before HTTP/2) are human-readable.
With HTTP/2, these messages are encapsulated in frames, making them impossible to read directly, but the principle remains the same.
For example:

 http
 GET / HTTP/1.1
Host: developer.mozilla.org
Accept-Language: fr

 Read the response sent by the server, such as:

 http
 HTTP/1.1 200 OK
Date: Sat, 09 Oct 2010 14:28:02 GMT
Server: Apache
Last-Modified: Tue, 01 Dec 2009 20:18:22 GMT
ETag: "51142bc1-7449-479b075b2891b"
Accept-Ranges: bytes
Content-Length: 29769
Content-Type: text/html

<!doctype html>… (here come the 29769 bytes of the requested web page)

 Close or reuse the connection for further requests.

 If HTTP pipelining is activated, several requests can be sent without waiting for the first response to be fully received.
HTTP pipelining has proven difficult to implement in existing networks, where old pieces of software coexist with modern versions.
HTTP pipelining has been superseded in HTTP/2 with more robust multiplexing requests within a frame.

 HTTP Messages

 HTTP messages, as defined in HTTP/1.1 and earlier, are human-readable.
In HTTP/2, these messages are embedded into a binary structure, a frame , allowing optimizations like compression of headers and multiplexing.
Even if only part of the original HTTP message is sent in this version of HTTP, the semantics of each message is unchanged and the client reconstitutes (virtually) the original HTTP/1.1 request.
It is therefore useful to comprehend HTTP/2 messages in the HTTP/1.1 format.

 There are two types of HTTP messages, requests and responses, each with its own format.

 Requests

 An example HTTP request:

 Requests consist of the following elements:

 An HTTP method , usually a verb like GET , POST , or a noun like OPTIONS or HEAD that defines the operation the client wants to perform.
Typically, a client wants to fetch a resource (using GET ) or post the value of an HTML form (using POST ), though more operations may be needed in other cases.

 The path of the resource to fetch; the URL of the resource stripped from elements that are obvious from the context, for example without the protocol ( http:// ), the domain (here, developer.mozilla.org ), or the TCP port (here, 80 ).

 The version of the HTTP protocol.

 Optional headers that convey additional information for the servers.

 A body, for some methods like POST , similar to those in responses, which contain the resource sent.

 Responses

 An example response:

 Responses consist of the following elements:

 The version of the HTTP protocol they follow.

 A status code , indicating if the request was successful or not, and why.

 A status message, a non-authoritative short description of the status code.

 HTTP headers , like those for requests.

 Optionally, a body containing the fetched resource.

 APIs based on HTTP

 The most commonly used API based on HTTP is the Fetch API , which can be used to make HTTP requests from JavaScript. The Fetch API replaces the XMLHttpRequest API.

 Another API, server-sent events , is a one-way service that allows a server to send events to the client, using HTTP as a transport mechanism.
Using the EventSource interface, the client opens a connection and establishes event handlers.
The client browser automatically converts the messages that arrive on the HTTP stream into appropriate Event objects. Then it delivers them to the event handlers that have been registered for the events' type if known, or to the onmessage event handler if no type-specific event handler was established.

 Conclusion

 HTTP is an extensible protocol that is easy to use.
The client-server structure, combined with the ability to add headers, allows HTTP to advance along with the extended capabilities of the Web.

 Though HTTP/2 adds some complexity by embedding HTTP messages in frames to improve performance, the basic structure of messages has stayed the same since HTTP/1.0.
Session flow remains basic, allowing it to be investigated and debugged with a HTTP network monitor .

 See also

 Evolution of HTTP

 Glossary terms:

 HTTP

 HTTP/2

 QUIC

 Help improve MDN

 Was this page helpful to you?

 Yes

 No

 Learn how to contribute
 This page was last modified on Jan 26, 2026 by MDN contributors .

 View this page on GitHub • Report a problem with this content

 Filter sidebar

 HTTP
 Guides
 Overview of HTTP
 Evolution of HTTP
 A typical HTTP session
 HTTP messages
 Media types Common types

 Compression in HTTP
 HTTP caching
 HTTP authentication
 Using HTTP cookies
 Redirections in HTTP
 Conditional requests
 Range requests
 Client hints
 User-Agent reduction
 Compression Dictionary Transport
 Experimental

 Network Error Logging
 Experimental

 Content negotiation Default Accept values

 Browser detection using the UA string
 Connection management in HTTP/1.x
 Protocol upgrade mechanism
 Proxy servers and tunneling Proxy Auto-Configuration (PAC) file

 Security and privacy HTTP Observatory
 Practical implementation guides
 Permissions Policy
 Experimental

 Cross-Origin Resource Policy (CORP)
 IFrame credentialless
 Experimental

 Fetch metadata
 Cross-Origin Resource Sharing (CORS)
 CORS errors Reason: CORS disabled
 Reason: CORS header 'Access-Control-Allow-Origin' does not match 'xyz'
 Reason: CORS header 'Access-Control-Allow-Origin' missing
 Reason: CORS header 'Origin' cannot be added
 Reason: CORS preflight channel did not succeed
 Reason: CORS request did not succeed
 Reason: CORS request external redirect not allowed
 Reason: CORS request not HTTP
 Reason: Credential is not supported if the CORS header 'Access-Control-Allow-Origin' is '*'
 Reason: Did not find method in CORS header 'Access-Control-Allow-Methods'
 Reason: expected 'true' in CORS header 'Access-Control-Allow-Credentials'
 Reason: invalid token 'xyz' in CORS header 'Access-Control-Allow-Headers'
 Reason: invalid token 'xyz' in CORS header 'Access-Control-Allow-Methods'
 Reason: missing token 'xyz' in CORS header 'Access-Control-Allow-Headers' from CORS preflight channel
 Reason: Multiple CORS header 'Access-Control-Allow-Origin' not allowed

 Content Security Policy (CSP) Errors and warnings

 Reference
 HTTP headers Accept
 Accept-CH
 Accept-Encoding
 Accept-Language
 Accept-Patch
 Accept-Post
 Accept-Ranges
 Access-Control-Allow-Credentials
 Access-Control-Allow-Headers
 Access-Control-Allow-Methods
 Access-Control-Allow-Origin
 Access-Control-Expose-Headers
 Access-Control-Max-Age
 Access-Control-Request-Headers
 Access-Control-Request-Method
 Activate-Storage-Access
 Age
 Allow
 Alt-Svc
 Alt-Used
 Attribution-Reporting-Eligible
 Deprecated

 Attribution-Reporting-Register-Source
 Deprecated

 Attribution-Reporting-Register-Trigger
 Deprecated

 Authorization
 Available-Dictionary
 Experimental

 Cache-Control
 Clear-Site-Data
 Connection
 Content-Digest
 Content-Disposition
 Content-DPR
 Non-standard

 Deprecated

 Content-Encoding
 Content-Language
 Content-Length
 Content-Location
 Content-Range
 Content-Security-Policy
 Content-Security-Policy-Report-Only
 Content-Type
 Cookie
 Critical-CH
 Experimental

 Cross-Origin-Embedder-Policy
 Cross-Origin-Embedder-Policy-Report-Only
 Cross-Origin-Opener-Policy
 Cross-Origin-Resource-Policy
 Date
 Device-Memory
 Non-standard

 Deprecated

 Dictionary-ID
 Experimental

 DNT
 Non-standard

 Deprecated

 Downlink
 Experimental

 DPR
 Non-standard

 Deprecated

 Early-Data
 Experimental

 ECT
 Experimental

 ETag
 Expect
 Expect-CT
 Deprecated

 Expires
 Forwarded
 From
 Host
 Idempotency-Key
 Experimental

 If-Match
 If-Modified-Since
 If-None-Match
 If-Range
 If-Unmodified-Since
 Integrity-Policy
 Integrity-Policy-Report-Only
 Keep-Alive
 Last-Modified
 Link
 Location
 Max-Forwards
 NEL
 Experimental

 No-Vary-Search
 Experimental

 Observe-Browsing-Topics
 Non-standard

 Deprecated

 Origin
 Origin-Agent-Cluster
 Permissions-Policy
 Experimental

 Pragma
 Deprecated

 Prefer
 Preference-Applied
 Priority
 Proxy-Authenticate
 Proxy-Authorization
 Range
 Referer
 Referrer-Policy
 Refresh
 Report-To
 Non-standard

 Deprecated

 Reporting-Endpoints
 Repr-Digest
 Retry-After
 RTT
 Experimental

 Save-Data
 Experimental

 Sec-Browsing-Topics
 Non-standard

 Deprecated

 Sec-CH-Device-Memory
 Experimental

 Sec-CH-DPR
 Experimental

 Sec-CH-Prefers-Color-Scheme
 Experimental

 Sec-CH-Prefers-Reduced-Motion
 Experimental

 Sec-CH-Prefers-Reduced-Transparency
 Experimental

 Sec-CH-UA
 Experimental

 Sec-CH-UA-Arch
 Experimental

 Sec-CH-UA-Bitness
 Experimental

 Sec-CH-UA-Form-Factors
 Experimental

 Sec-CH-UA-Full-Version
 Deprecated

 Sec-CH-UA-Full-Version-List
 Experimental

 Sec-CH-UA-Mobile
 Experimental

 Sec-CH-UA-Model
 Experimental

 Sec-CH-UA-Platform
 Experimental

 Sec-CH-UA-Platform-Version
 Experimental

 Sec-CH-UA-WoW64
 Experimental

 Sec-CH-Viewport-Height
 Experimental

 Sec-CH-Viewport-Width
 Experimental

 Sec-CH-Width
 Experimental

 Sec-Fetch-Dest
 Sec-Fetch-Mode
 Sec-Fetch-Site
 Sec-Fetch-Storage-Access
 Sec-Fetch-User
 Sec-GPC
 Experimental

 Sec-Private-State-Token
 Experimental

 Sec-Private-State-Token-Crypto-Version
 Experimental

 Sec-Private-State-Token-Lifetime
 Experimental

 Sec-Purpose
 Sec-Redemption-Record
 Experimental

 Sec-Speculation-Tags
 Experimental

 Sec-WebSocket-Accept
 Sec-WebSocket-Extensions
 Sec-WebSocket-Key
 Sec-WebSocket-Protocol
 Sec-WebSocket-Version
 Server
 Server-Timing
 Service-Worker
 Service-Worker-Allowed
 Service-Worker-Navigation-Preload
 Set-Cookie
 Set-Login
 SourceMap
 Speculation-Rules
 Experimental

 Strict-Transport-Security
 Supports-Loading-Mode
 Experimental

 TE
 Timing-Allow-Origin
 Tk
 Non-standard

 Deprecated

 Trailer
 Transfer-Encoding
 Upgrade
 Upgrade-Insecure-Requests
 Use-As-Dictionary
 Experimental

 User-Agent
 Vary
 Via
 Viewport-Width
 Non-standard

 Deprecated

 Want-Content-Digest
 Want-Repr-Digest
 Warning
 Deprecated

 Width
 Non-standard

 Deprecated

 WWW-Authenticate
 X-Content-Type-Options
 X-DNS-Prefetch-Control
 Non-standard

 X-Forwarded-For
 Non-standard

 X-Forwarded-Host
 Non-standard

 X-Forwarded-Proto
 Non-standard

 X-Frame-Options
 X-Permitted-Cross-Domain-Policies
 Non-standard

 X-Powered-By
 Non-standard

 X-Robots-Tag
 Non-standard

 X-XSS-Protection
 Non-standard

 Deprecated

 HTTP request methods CONNECT
 DELETE
 GET
 HEAD
 OPTIONS
 PATCH
 POST
 PUT
 TRACE

 HTTP response status codes 100 Continue
 101 Switching Protocols
 102 Processing
 103 Early Hints
 200 OK
 201 Created
 202 Accepted
 203 Non-Authoritative Information
 204 No Content
 205 Reset Content
 206 Partial Content
 207 Multi-Status
 208 Already Reported
 226 IM Used
 300 Multiple Choices
 301 Moved Permanently
 302 Found
 303 See Other
 304 Not Modified
 307 Temporary Redirect
 308 Permanent Redirect
 400 Bad Request
 401 Unauthorized
 402 Payment Required
 403 Forbidden
 404 Not Found
 405 Method Not Allowed
 406 Not Acceptable
 407 Proxy Authentication Required
 408 Request Timeout
 409 Conflict
 410 Gone
 411 Length Required
 412 Precondition Failed
 413 Content Too Large
 414 URI Too Long
 415 Unsupported Media Type
 416 Range Not Satisfiable
 417 Expectation Failed
 418 I'm a teapot
 421 Misdirected Request
 422 Unprocessable Content
 423 Locked
 424 Failed Dependency
 425 Too Early
 426 Upgrade Required
 428 Precondition Required
 429 Too Many Requests
 431 Request Header Fields Too Large
 451 Unavailable For Legal Reasons
 500 Internal Server Error
 501 Not Implemented
 502 Bad Gateway
 503 Service Unavailable
 504 Gateway Timeout
 505 HTTP Version Not Supported
 506 Variant Also Negotiates
 507 Insufficient Storage
 508 Loop Detected
 510 Not Extended
 511 Network Authentication Required

 CSP directives base-uri
 block-all-mixed-content
 Deprecated

 child-src
 connect-src
 default-src
 fenced-frame-src
 Experimental

 font-src
 form-action
 frame-ancestors
 frame-src
 img-src
 manifest-src
 media-src
 object-src
 prefetch-src
 Non-standard

 Deprecated

 report-to
 report-uri
 Deprecated

 require-trusted-types-for
 sandbox
 script-src
 script-src-attr
 script-src-elem
 style-src
 style-src-attr
 style-src-elem
 trusted-types
 upgrade-insecure-requests
 worker-src

 Permissions-Policy directives
 Experimental
 accelerometer
 Experimental

 ambient-light-sensor
 Experimental

 aria-notify
 Experimental

 attribution-reporting
 Deprecated

 autoplay
 Experimental

 bluetooth
 Experimental

 browsing-topics
 Non-standard

 Deprecated

 camera
 Experimental

 captured-surface-control
 Experimental

 ch-ua-high-entropy-values
 Experimental

 compute-pressure
 Experimental

 cross-origin-isolated
 Experimental

 deferred-fetch
 Experimental

 deferred-fetch-minimal
 Experimental

 display-capture
 Experimental

 encrypted-media
 Experimental

 fullscreen
 Experimental

 gamepad
 Experimental

 geolocation
 Experimental

 gyroscope
 Experimental

 hid
 Experimental

 identity-credentials-get
 Experimental

 idle-detection
 Experimental

 language-detector
 Experimental

 local-fonts
 Experimental

 magnetometer
 Experimental

 microphone
 Experimental

 midi
 Experimental

 on-device-speech-recognition
 Experimental

 otp-credentials
 Experimental

 payment
 Experimental

 picture-in-picture
 Experimental

 private-state-token-issuance
 Experimental

 private-state-token-redemption
 Experimental

 publickey-credentials-create
 Experimental

 publickey-credentials-get
 Experimental

 screen-wake-lock
 Experimental

 serial
 Experimental

 speaker-selection
 Experimental

 storage-access
 Experimental

 summarizer
 Experimental

 translator
 Experimental

 usb
 Experimental

 web-share
 Experimental

 window-management
 Experimental

 xr-spatial-tracking
 Experimental

 HTTP resources and specifications

 MDN

 Your blueprint for a better internet.

 MDN

 About

 Blog

 Mozilla careers

 Advertise with us

 MDN Plus

 Product help

 Contribute

 MDN Community

 Community resources

 Writing guidelines

 MDN Discord

 MDN on GitHub

 Developers

 Web technologies

 Learn web development

 Guides

 Tutorials

 Glossary

 Hacks blog

 Mozilla

 Website Privacy Notice

 Telemetry Settings

 Legal

 Community Participation Guidelines

 Visit Mozilla Corporation’s not-for-profit parent, the Mozilla Foundation .
 Portions of this content are ©1998–2026 by individual mozilla.org contributors. Content available under a Creative Commons license .
