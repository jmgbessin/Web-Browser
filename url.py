import socket
# encrypted HTTPS connections
import ssl

class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https"]
        if self.scheme == "http":
            self.port = 80
        if self.scheme == "https":
            self.port = 443
        
        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        
        # support for custom ports
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)
        
        self.path = "/" + url
        
    def __repr__(self):
        return f"{self.scheme}://{self.host}:{str(self.port)}{self.path}"
    
    def __str__(self):
        port_part = ":" + str(self.port)
        if self.scheme == "https" and self.port == 443:
            port_part = ""
        if self.scheme == "http" and self.port == 80:
            port_part = ""
        return self.scheme + "://" + self.host + port_part + self.path
        
    # resolve a relative url
    def resolve(self, url):
        if "://" in url: return URL(url)
        if not url.startswith("/"):
            dir, _ = self.path.rsplit("/", 1)
            while url.startswith("../"):
                _, url = url.split("/", 1)
                if "/" in dir:
                    dir, _ = dir.rsplit("/", 1)
            url = dir + "/" + url
        if url.startswith("//"):
            return URL(self.scheme + ":" + url)
        else:
            return  URL(self.scheme + "://" + self.host + \
                ":" + str(self.port) + url)
        
    def request(self):
        # create socket
        s = socket.socket(
            family = socket.AF_INET,
            type = socket.SOCK_STREAM,
            # computer can send arbitrary amounts of data
            proto = socket.IPPROTO_TCP,
        )
        
        # connect socket to host
        s.connect((self.host, self.port))
        # requires host and port - port depends on protocol used
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname = self.host)
        
        # request data from host
        request = "GET {} HTTP/1.0\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
        request += "\r\n"
        s.send(request.encode("utf8"))
        
        # get server response
        response = s.makefile("r", encoding = "utf8", newline = "\r\n")
        """ the makefile method abstracts the loop that collects bytes as they 
        arrive from the server """
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)
        
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
            """ headers are case-sensitive - this normalizes them on our side 
            if they come from server with capitals - and whitespace is 
            insignificant in HTTP header values """
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers
        # indicates data is being sent in an unusual way
        
        content = response.read()
        s.close()
        return content
