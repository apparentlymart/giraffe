from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from google.appengine.api import users
from openid.consumer import consumer, discover
from openid.extensions import sreg

from library.auth import auth_required, auth_forbidden, log
from library.auth import make_person_from_response
from library.auth import AnonymousUser, OpenIDStore


@auth_forbidden
def signin(request, nexturl=None):
    return render_to_response(
        'library/signin.html',
        {},
        context_instance=RequestContext(request),
    )


@auth_forbidden
def start_openid(request):
    openid_url = request.POST.get('openid_url', None)
    if not openid_url:
        username = request.POST.get('openid_username', None)
        pattern = request.POST.get('openid_pattern', None)
        if username and pattern:
            openid_url = pattern.replace('{name}', username)
    if not openid_url:
        request.flash.put(loginerror="An OpenID as whom to sign in is required.")
        return HttpResponseRedirect(reverse('login'))
    log.debug('Attempting to sign viewer in as %r', openid_url)

    csr = consumer.Consumer(request.session, OpenIDStore())
    try:
        ar = csr.begin(openid_url)
    except discover.DiscoveryFailure, exc:
        request.flash.put(loginerror=exc.message)
        return HttpResponseRedirect(reverse('login'))

    ar.addExtension(sreg.SRegRequest(optional=('nickname', 'fullname', 'email')))

    def whole_reverse(view):
        return request.build_absolute_uri(reverse(view))

    return_to = whole_reverse('library.views.auth.complete_openid')
    redirect_url = ar.redirectURL(whole_reverse('home'), return_to)
    return HttpResponseRedirect(redirect_url)


@auth_forbidden
def complete_openid(request):
    csr = consumer.Consumer(request.session, OpenIDStore())
    resp = csr.complete(request.GET, request.build_absolute_uri())
    if isinstance(resp, consumer.CancelResponse):
        return HttpResponseRedirect(reverse('home'))
    elif isinstance(resp, consumer.FailureResponse):
        request.flash.put(loginerror=resp.message)
        return HttpResponseRedirect(reverse('login'))
    elif isinstance(resp, consumer.SuccessResponse):
        make_person_from_response(resp)
        request.session['openid'] = resp.identity_url
        return HttpResponseRedirect(reverse('home'))


@auth_required
def signout(request):
    del request.session['openid']
    del request.user
    return HttpResponseRedirect(reverse('home'))
