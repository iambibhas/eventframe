# -*- coding: utf-8 -*-

from functools import wraps
from datetime import datetime
from werkzeug.exceptions import NotFound
from flask import g, request, url_for, Response
from flask.ext.themes import get_theme, render_theme_template
from coaster.views import load_model, load_models
from eventframe import eventapp
from eventframe.models import db, Hostname, Folder, Page, PAGE_STATUS


def get_website(f):
    @wraps(f)
    def decorated_function(**kwargs):
        website = g.website if hasattr(g, 'website') else None
        if website is None:
            hostname = Hostname.query.filter_by(name=request.environ['HTTP_HOST']).first()
            if not hostname:
                return NotFound()
            else:
                g.website = hostname.website
        return f(website=g.website, **kwargs)
    return decorated_function


@eventapp.route('/')
def index():
    return page(folder=u'', page=u'')


@eventapp.route('/<folder>/<page>')
@get_website
@load_models(
    (Folder, {'name': 'folder', 'website': 'website'}, 'folder'),
    (Page, {'name': 'page', 'folder': 'folder'}, 'page')
    )
def page(folder, page):
    theme = get_theme(folder.theme)
    return render_theme_template(theme, page.template,
        website=folder.website, title=page.title, page=page)


@eventapp.route('/<folder>/')
@get_website
def folder(website, folder):
    try:
        return page(folder=folder, page=u'')
    except NotFound:
        return page(folder=u'', page=folder)

    # First, check if this folder is actually a page
    rootfolder = Folder.query.filter_by(name=u'', website=website).first()
    pageob = Page.query.filter_by(name=folder, folder=rootfolder).first()
    # Not a page? Now check if it's a folder
    if pageob is None:
        return page(folder=folder, page=u'')
    else:
        # It is a page. Render it
        theme = get_theme(folder.theme)
        return render_theme_template(theme, pageob.template,
            website=website, title=pageob.title, page=pageob)


def feedquery():
    return Page.query.filter_by(blog=True).filter_by(status=PAGE_STATUS.PUBLISHED).filter(
        Page.datetime <= datetime.utcnow()).order_by(db.desc('datetime'))


@eventapp.route('/feed')
@get_website
def feed(website):
    theme = get_theme(website.theme)
    folder_ids = [i[0] for i in db.session.query(Folder.id).filter_by(website=website).all()]
    pages = feedquery().filter(Page.folder_id.in_(folder_ids)).all()
    if pages:
        updated = pages[0].datetime.isoformat() + 'Z'
    else:
        updated = datetime.utcnow().isoformat() + 'Z'
    return Response(render_theme_template(theme, 'feed.xml',
            feedid=url_for('index', _external=True),
            website=website, title=website.title, pages=pages, updated=updated),
        content_type='application/atom+xml; charset=utf-8')


@eventapp.route('/<folder>/feed')
@get_website
@load_model(Folder, {'name': 'folder', 'website': 'website'}, 'folder')
def folder_feed(folder):
    theme = get_theme(folder.theme)
    pages = feedquery().filter_by(folder=folder).all()
    if pages:
        updated = pages[0].datetime.isoformat() + 'Z'
    else:
        updated = datetime.utcnow().isoformat() + 'Z'
    return Response(render_theme_template(theme, 'feed.xml',
            feedid=url_for('folder', folder=folder.name),
            website=folder.website, title=folder.website.title, pages=pages, updated=updated),
        content_type='application/atom+xml; charset=utf-8')