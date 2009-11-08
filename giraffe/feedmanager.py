
"""
A component that glues all of the components together so that we actually poll
feeds that are associated with the registered accounts and hand them off
to the feed parsing code.
"""

from giraffe import models
from giraffe import urlpoller

# TODO: Always call this on startup so that the urlpoller
# is always primed to poll?
# For now, we just explitly call this before we tell the urlpoller to
# poll in the admin command that actually runs a poll cycle.

def init():
    accounts = models.Account.objects.all()

    # Ultimately this will be replaced by a real callback
    # that feeds into the feed consumer code.
    def dummy_callback(url, result):
        print "We fetched the feed "+url+", though for now we're doing nothing with it."

    for account in accounts:
        feed_urls = account.activity_feed_urls()
        for feed_url in feed_urls:
            urlpoller.register_url(feed_url, dummy_callback)

def refresh_feeds():
    urlpoller.poll()


