from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from api.decorators import allowed_methods
from library.auth.decorators import auth_required, admin_only
from library.models import Person, Asset, Action


def stream(request, openid, template=None, content_type=None):
    try:
        me = Person.all().filter(openid=openid)[0]
    except IndexError:
        raise Http404

    blog = Action.all().filter(person=me, verb=Action.verbs.post)
    blog.filter(privacy_groups="public")
    blog.order('-when')
    actions = blog[0:10]

    return render_to_response(
        template or 'library/stream.html',
        {
            'blogger': me,
            'actions': actions,
        },
        context_instance=RequestContext(request),
        mimetype=content_type or settings.DEFAULT_CONTENT_TYPE,
    )


def profile(request, slug, template=None, content_type=None):
    person = Person.get(slug=slug)
    if person is None:
        raise Http404

    profile = Action.all().filter(person=person)
    profile.order('-when')
    actions = profile[0:10]

    return render_to_response(
        template or 'library/profile.html',
        {
            'person': person,
            'actions': actions,
        },
        context_instance=RequestContext(request),
        mimetype=content_type or settings.DEFAULT_CONTENT_TYPE,
    )


def asset(request, slug):
    asset = Asset.get(slug=slug)
    if asset is None:
        raise Http404

    actions = asset.actions.filter(person=asset.author, verb=Action.verbs.post)
    thread = asset.thread_members

    return render_to_response(
        'library/asset.html',
        {
            'asset': asset,
            'blogger': asset.author,
            'actions': actions,
            'thread': thread,
        },
        context_instance=RequestContext(request),
    )


@auth_required
@allowed_methods("POST")
def comment(request, slug):
    asset = Asset.get(slug=slug)
    if asset is None:
        raise Http404

    content = request.POST.get('content')

    comment = Asset(author=request.user, in_reply_to=asset)
    comment.content = content
    comment.content_type = 'text/markdown'
    if asset.thread:
        comment.thread = asset.thread
    else:
        comment.thread = comment.in_reply_to
    comment.save()

    act = Action(person=request.user, verb=Action.verbs.post, asset=comment, when=comment.published)
    act.save()

    return HttpResponseRedirect(asset.get_permalink_url())


def by_method(**views_by_method):
    @allowed_methods(*[meth.lower() for meth in views_by_method.keys()])
    def invoke(request, *args, **kwargs):
        view = views_by_method[request.method.lower()]
        return view(request, *args, **kwargs)
    return invoke


@admin_only
def post_page(request):
    return render_to_response(
        'library/post.html',
        {
            'blogger': request.user,
        },
        context_instance=RequestContext(request),
    )


@admin_only
def save_post(request):
    return HttpResponseRedirect(reverse('home'))


post = by_method(get=post_page, post=save_post)
