
handler_for_domain = {}

DEFAULT_HANDLER = None

class AccountHandler:
    """
    Abstract base class for classes that handle accounts.
    """

    @classmethod
    def for_domain(cls, domain):
        if domain in handler_for_domain:
            return handler_for_domain[domain]
        else:
            return DEFAULT_HANDLER

    @classmethod
    def register(cls, handler):
        # FIXME: Should detect if we get a domain collision
        # between two handlers.
        domains = handler.handled_domains()
        for domain in domains:
            handler_for_domain[domain] = handler

    def handled_domains(self):
        return []

    def provider_name(self):
        return None

    def profile_url_for_account(self, account):
        return None

    def display_username_for_account(self, account):
        return account.username

    def activity_feed_urls_for_account(self, account):
        return []

DEFAULT_HANDLER = AccountHandler()

# TODO: Make a generic accounthandler that can easily be seeded from
# a configuration file like MT Action Streams does.
# For now it's just code.

class WebsiteAccountHandler(AccountHandler):

    def profile_url_for_account(self, account):
        return account.user_id

    def activity_feed_urls_for_account(self, account):
        # FIXME: Do autodiscovery here?
        return []

class TwitterAccountHandler(AccountHandler):

    def provider_name(self):
        return "Twitter"

    def handled_domains(self):
        return [ "twitter.com" ]

    def profile_url_for_account(self, account):
        return "http://twitter.com/%s" % account.username

    def activity_feed_urls_for_account(self, account):
        return [ "http://twitter.com/statuses/user_timeline/%s.atom" % account.username ]

AccountHandler.register(TwitterAccountHandler());


class TypePadProfilesAccountHandler(AccountHandler):

    def provider_name(self):
        return "TypePad"

    def handled_domains(self):
        return [ "profile.typepad.com" ]

    def profile_url_for_account(self, account):
        return "http://profile.typepad.com/%s" % account.username

    def activity_feed_urls_for_account(self, account):
        return [ "http://profile.typepad.com/%s/activity/atom.xml" % account.username ]

AccountHandler.register(TypePadProfilesAccountHandler());


class FacebookAccountHandler(AccountHandler):

    def provider_name(self):
        return "Facebook"

    def handled_domains(self):
        return [ "facebook.com" ]

    def profile_url_for_account(self, account):
        return "http://www.facebook.com/profile.php?id=%s" % account.user_id

AccountHandler.register(FacebookAccountHandler());


