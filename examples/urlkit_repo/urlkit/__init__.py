"""Small URL utilities used to exercise the local agent workflow."""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def append_query(url, params):
    """Append key/value pairs to a URL without changing its other components."""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query.update(params)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
