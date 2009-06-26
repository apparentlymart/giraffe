from functools import wraps
import logging
import re
import time

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from google.appengine.api import users
from openid.consumer import consumer
from openid.extensions import sreg
from openid.store import interface, nonce

import library.models as models


log = logging.getLogger('library.auth')


class _AnonymousUserClass(object):

    class Error(Exception):
        pass

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = object.__new__(cls)
        return cls.instance

    def _cant_do_that(*args, **kwargs):
        raise _AnonymousUserClass.Error("That's an anonymous user, silly")

    for x in ('user_id', 'email', 'nickname', 'openid'):
        locals()[x] = _cant_do_that

    is_anonymous = True


AnonymousUser = _AnonymousUserClass()


class AuthenticationMiddleware(object):

    def process_request(self, request):
        try:
            openid = request.session['openid']
            person = models.Person.get(openid=openid)
            if person is None:
                raise ValueError()
        except (KeyError, ValueError):
            request.user = AnonymousUser
        else:
            request.user = person
            request.user.is_anonymous = False


def auth_forbidden(fn):
    @wraps(fn)
    def check_for_anon(request, *args, **kwargs):
        if request.user is AnonymousUser:
            return fn(request, *args, **kwargs)
        return HttpResponseRedirect(reverse('home'))

    return check_for_anon


def auth_required(fn):
    @wraps(fn)
    def check_for_auth(request, *args, **kwargs):
        if request.user is AnonymousUser:
            return HttpResponseRedirect(reverse('signin'))
        return fn(request, *args, **kwargs)

    return check_for_auth


def admin_only(fn):
    @wraps(fn)
    def check_for_admin(request, *args, **kwargs):
        if getattr(request.user, 'is_admin', False):
            return fn(request, *args, **kwargs)
        return HttpResponseRedirect(reverse('home'))

    return check_for_admin


def make_person_from_response(resp):
    if not isinstance(resp, consumer.SuccessResponse):
        raise ValueError("Can't make a Person from an unsuccessful response")

    # Find the person.
    openid = resp.identity_url
    p = models.Person.get(openid=openid)
    if p is None:
        p = Person(openid=openid)

    sr = sreg.SRegResponse.fromSuccessResponse(resp)
    if sr is not None:
        if 'nickname' in sr:
            p.name = sr['nickname']
        if 'email' in sr:
            p.email = sr['email']

    if p.name is None:
        name = resp.identity_url
        # Remove the leading scheme, if it's http.
        name = re.sub(r'^http://', '', name)
        # If it's just a domain, strip the trailing slash.
        name = re.sub(r'^([^/]+)/$', r'\1', name)
        p.name = name

    if openid == "http://markpasc.org/mark/":
        p.is_admin = True

    p.save()


class OpenIDStore(interface.OpenIDStore):

    def storeAssociation(self, server_url, association):
        a = models.Association(server_url=server_url)
        for key in ('handle', 'secret', 'issued', 'lifetime', 'assoc_type'):
            setattr(a, key, getattr(association, key))
        a.save()
        log.debug('Stored association %r %r %r %r %r for server %s (expires %r)',
            association.handle, association.secret, association.issued,
            association.lifetime, association.assoc_type, server_url, a.expires)

    def getAssociation(self, server_url, handle=None):
        q = models.Association.all().filter(server_url=server_url)
        if handle is not None:
            q.filter(handle=handle)

        # No expired associations.
        q.filter(expires__gte=int(time.time()))

        # Get the futuremost association.
        q.order('-expires')

        try:
            a = q[0]
        except IndexError:
            log.debug('Could not find requested association %r for server %s)',
                handle, server_url)
            return
        else:
            log.debug('Found requested association %r for server %s',
                handle, server_url)
            return a.as_openid_association()

    def removeAssociation(self, server_url, handle):
        q = models.Association.all().filter(server_url=server_url, handle=handle)
        try:
            a = q[0]
        except IndexError:
            log.debug('Could not find requested association %r for server %s to delete',
                handle, server_url)
            return False
        else:
            a.delete()
            log.debug('Found and deleted requested association %r for server %s',
                handle, server_url)
            return True

    def useNonce(self, server_url, timestamp, salt):
        now = int(time.time())
        if timestamp < now - nonce.SKEW or now + nonce.SKEW < timestamp:
            return False

        data = dict(server_url=server_url, timestamp=timestamp, salt=salt)

        q = models.Squib.all(keys_only=True).filter(**data)
        try:
            s = q[0]
        except IndexError:
            pass
        else:
            log.debug('Discovered squib %r %r for server %s was already used',
                timestamp, salt, server_url)
            return False

        s = models.Squib(**data)
        s.save()
        log.debug('Noted new squib %r %r for server %s',
            timestamp, salt, server_url)
        return True

    def cleanup(self):
        self.cleanupAssociations()
        self.cleanupNonces()

    def cleanupAssociations(self):
        now = int(time.time())
        q = models.Association.all(keys_only=True).filter(expires__lt=now - nonce.SKEW)
        db.delete(q.fetch(100))

    def cleanupNonces(self):
        now = int(time.time())
        q = models.Squib.all(keys_only=True).filter(timestamp__lt=now - nonce.SKEW)
        db.delete(q.fetch(100))