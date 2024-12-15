class NetscapeCookieParser:
    """Parses Netscape cookies."""

    @staticmethod
    def parse(file_path):
        """Parse cookies from a Netscape file."""
        cookies = []
        with open(file_path, "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    parts = line.strip().split("\t")
                    cookies.append({
                        "domain": parts[0],
                        "flag": parts[1],
                        "path": parts[2],
                        "secure": parts[3],
                        "expiry": parts[4],
                        "name": parts[5],
                        "value": parts[6],
                    })
        return cookies
