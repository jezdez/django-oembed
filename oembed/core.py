import gzip
import logging
import os
import re
import urllib2
import urlparse
try:
    import json
except ImportError:
    from django.utils import simplejson as json
try:
    from urlparse import parse_qs
except ImportError:
    # (copied to urlparse from cgi in 2.6)
    from cgi import parse_qs
from heapq import heappush, heappop
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.conf import settings
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string

from .models import ProviderRule, StoredOEmbed

logger = logging.getLogger("oembed core")

END_OVERRIDES = (')', ',', '.', '>', ']', ';')
MAX_WIDTH = getattr(settings, "OEMBED_MAX_WIDTH", 320)
MAX_HEIGHT = getattr(settings, "OEMBED_MAX_HEIGHT", 240)
FORMAT = getattr(settings, "OEMBED_FORMAT", "json")

def fetch(url, user_agent="django-oembed/0.1"):
    """
    Fetches from a URL, respecting GZip encoding, etc.
    """
    request = urllib2.Request(url)
    request.add_header('User-Agent', user_agent)
    request.add_header('Accept-Encoding', 'gzip')
    opener = urllib2.build_opener()
    f = opener.open(request)
    result = f.read()
    if f.headers.get('content-encoding', '') == 'gzip':
        result = gzip.GzipFile(fileobj=StringIO(result)).read()
    f.close()
    return result

def re_parts(regex_list, text):
    """
    An iterator that returns the entire text, but split by which regex it
    matched, or none at all.  If it did, the first value of the returned tuple
    is the index into the regex list, otherwise -1.

    >>> first_re = re.compile('asdf')
    >>> second_re = re.compile('an')
    >>> list(re_parts([first_re, second_re], 'This is an asdf test.'))
    [(-1, 'This is '), (1, 'an'), (-1, ' '), (0, 'asdf'), (-1, ' test.')]

    >>> list(re_parts([first_re, second_re], 'asdfasdfasdf'))
    [(0, 'asdf'), (0, 'asdf'), (0, 'asdf')]

    >>> list(re_parts([], 'This is an asdf test.'))
    [(-1, 'This is an asdf test.')]

    >>> third_re = re.compile('sdf')
    >>> list(re_parts([first_re, second_re, third_re], 'This is an asdf test.'))
    [(-1, 'This is '), (1, 'an'), (-1, ' '), (0, 'asdf'), (-1, ' test.')]
    """
    def match_compare(x, y):
        return x.start() - y.start()
    prev_end = 0
    iter_dict = dict((r, r.finditer(text)) for r in regex_list)
    
    # A heapq containing matches
    matches = []
    
    # Bootstrap the search with the first hit for each iterator
    for regex, iterator in iter_dict.items():
        try:
            match = iterator.next()
            heappush(matches, (match.start(), match))
        except StopIteration:
            iter_dict.pop(regex)
    
    # Process matches, revisiting each iterator from which a match is used
    while matches:
        # Get the earliest match
        start, match = heappop(matches)
        end = match.end()
        if start > prev_end:
            # Yield the text from current location to start of match
            yield (-1, text[prev_end:start])
        # Yield the match
        yield (regex_list.index(match.re), text[start:end])
        # Get the next match from the iterator for this match
        if match.re in iter_dict:
            try:
                newmatch = iter_dict[match.re].next()
                heappush(matches, (newmatch.start(), newmatch))
            except StopIteration:
                iter_dict.pop(match.re)
        prev_end = end

    # Yield text from end of last match to end of text
    last_bit = text[prev_end:]
    if len(last_bit) > 0:
        yield (-1, last_bit)

def build_url(endpoint, url, max_width, max_height):
    # Split up the URL and extract GET parameters as a dictionary
    split_url = urlparse.urlsplit(endpoint)
    params = parse_qs(split_url[3])
    params.update({
        'url': url,
        'maxwidth': max_width,
        'maxheight': max_height,
        'format': FORMAT,
        })
    # Put the URL back together with the new params and return it
    params = urlencode(params, doseq=1)
    return urlparse.urlunsplit(split_url[:3] + (params,) + split_url[4:])

def fetch_dict(url, max_width=None, max_height=None):
    """
    Returns the response from the oEmbed provider as a dictionary for the 
    give oEmbeddable URL.
    
    Returns None if URL could not be matched to an oEmbed provider.
    
    This does not take advantage of the StoredOEmbed cache, since the cached
    objects don't contain all the information from the JSON. If you find
    yourself using this function a lot, consider rolling you own caching.
    """
    if not max_width:
        max_width = MAX_WIDTH
    if not max_height:
        max_height = MAX_HEIGHT
    rule = None
    for provider in ProviderRule.objects.only('regex'):
        if re.match(provider.regex, url):
            rule = provider
            break
    if rule is not None:
        oembedurl = build_url(rule.endpoint, url, max_width, max_height)
        # Fetch the link and parse the JSON.
        return json.loads(fetch(oembedurl))

def replace(text, max_width=None, max_height=None, template_dir='oembed'):
    """
    Scans a block of text, replacing anything matched by a ``ProviderRule``
    pattern with an OEmbed html snippet, if possible.
    
    Templates should be stored at {template_dir}/{format}.html, so for example:
        
        oembed/video.html
        or
        oembed/inline/video.html
        
    These templates are passed a context variable, ``response``, which is a 
    dictionary representation of the response.
    """
    if not max_width:
        max_width = MAX_WIDTH
    if not max_height:
        max_height = MAX_HEIGHT

    rules = list(ProviderRule.objects.all())
    patterns = [re.compile(r.regex, re.I | re.U) for r in rules] # Compiled patterns from the rules
    parts = [] # The parts that we will assemble into the final return value.
    indices = [] # List of indices of parts that need to be replaced with OEmbed stuff.
    indices_rules = [] # List of indices into the rules in order for which index was gotten by.
    urls = set() # A set of URLs to try to lookup from the database.
    stored = {} # A mapping of URLs to StoredOEmbed objects.
    index = 0
    # First we pass through the text, populating our data structures.
    for i, part in re_parts(patterns, text):
        if i == -1:
            parts.append(part)
            index += 1
        else:
            to_append = ""
            # If the link ends with one of our overrides, build a list
            while part[-1] in END_OVERRIDES:
                to_append += part[-1]
                part = part[:-1]
            indices.append(index)
            urls.add(part)
            indices_rules.append(i)
            parts.append(part)
            index += 1
            if to_append:
                parts.append(to_append)
                index += 1
    # Now we fetch a list of all stored patterns, and put it in a dictionary
    # mapping the URL to to the stored model instance.
    for stored_embed in StoredOEmbed.objects.filter(
            match__in=urls, max_width=max_width, max_height=max_height):
        stored[stored_embed.match] = stored_embed
    # Now we're going to do the actual replacement of URL to embed.
    for i, id_to_replace in enumerate(indices):
        rule = rules[indices_rules[i]]
        part = parts[id_to_replace]
        try:
            # Try to grab the stored model instance from our dictionary, and
            # use the stored HTML fragment as a replacement.
            parts[id_to_replace] = stored[part].html
        except KeyError:
            try:
                url = build_url(rule.endpoint, part, max_width, max_height)
                # Fetch the link and parse the JSON.
                json_string = fetch(url)
                resp = json.loads(json_string)
                # Depending on the embed type, grab the associated template and
                # pass it the parsed JSON response as context.
                replacement = render_to_string(
                    os.path.join(template_dir, '{0}.html'.format(resp['type'])),
                    {'response': resp, 'match': part, }
                )
                if replacement:
                    stored_embed = StoredOEmbed.objects.create(
                        match = part,
                        max_width = max_width,
                        max_height = max_height,
                        html = replacement,
                        json = json_string,
                    )
                    stored[stored_embed.match] = stored_embed
                    parts[id_to_replace] = replacement
                else:
                    raise ValueError
            except ValueError:
                parts[id_to_replace] = part
            except KeyError:
                parts[id_to_replace] = part
            except urllib2.HTTPError:
                parts[id_to_replace] = part
    # Combine the list into one string and return it.
    return mark_safe(u''.join(parts).replace('http://','//'))
