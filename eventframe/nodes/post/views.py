# -*- coding: utf-8 -*-
from datetime import datetime
from flask import url_for, Response, request
from flask.ext.themes import get_theme, render_theme_template
from coaster.views import load_model
from eventframe import eventapp
from eventframe.models import db, Folder, Node
from eventframe.nodes import get_website
from eventframe.nodes.content import ContentHandler
from eventframe.nodes.post.models import Post

__all__ = ['PostHandler', 'rootfeed', 'folderfeed', 'register']


class PostHandler(ContentHandler):
    model = Post
    title_new = u"New blog post"
    title_edit = u"Edit blog post"

    def make_form(self):
        form = super(PostHandler, self).make_form()
        if request.method == 'GET' and not self.node:
            form.template.data = 'post.html'
        return form


def feedquery():
    return Post.query.filter_by(is_published=True).order_by(db.desc('node.published_at'))


def rootfeed(website, limit=20):
    query = feedquery().filter(Node.folder_id.in_(website.folder_ids()))
    if limit:
        query = query.limit(limit)
    return query.all()


def folderfeed(folder, limit=20):
    query = feedquery().filter(Node.folder == folder)
    if limit:
        query = query.limit(limit)
    return query.all()


@eventapp.route('/feed')
@get_website
def feed(website):
    theme = get_theme(website.theme)
    posts = rootfeed(website)
    if posts:
        updated = max(posts[0].revisions.published.updated_at, posts[0].published_at).isoformat() + 'Z'
    else:
        updated = datetime.utcnow().isoformat() + 'Z'
    return Response(render_theme_template(theme, 'feed.xml',
            feedid=url_for('index', _external=True),
            website=website, title=website.title, posts=posts, updated=updated),
        content_type='application/atom+xml; charset=utf-8')


@eventapp.route('/<folder>/feed')
@get_website
@load_model(Folder, {'name': 'folder', 'website': 'website'}, 'folder')
def folder_feed(folder):
    theme = get_theme(folder.theme)
    posts = folderfeed(folder)
    if posts:
        updated = posts[0].published_at.isoformat() + 'Z'
    else:
        updated = datetime.utcnow().isoformat() + 'Z'
    return Response(render_theme_template(
            theme, 'feed.xml',
            feedid=url_for('folder', folder=folder.name),
            website=folder.website,
            title=u"%s — %s" % (folder.title or folder.name, folder.website.title),
            posts=posts, updated=updated),
        content_type='application/atom+xml; charset=utf-8')


def register(registry):
    registry.register(Post, PostHandler, render=True)
