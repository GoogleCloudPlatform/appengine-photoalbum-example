# -*- coding: utf-8 -*-

# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os, uuid

from flask import Flask, render_template, request, redirect, url_for
from flask_wtf.file import FileField
from pytz import timezone, utc
from wtforms import Form, validators, ValidationError, SelectField
from werkzeug.utils import secure_filename
from werkzeug.datastructures import CombinedMultiDict

import cloudstorage as gcs
from google.appengine.api import app_identity
from google.appengine.ext import ndb
from google.cloud import vision, translate


app = Flask(__name__)

MAX_PHOTOS = 20
content_types = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                 'png': 'image/png', 'gif': 'image/gif'}
extensions = sorted(content_types.keys())

bucket_name = app_identity.get_default_gcs_bucket_name()
storage_path = 'https://storage.cloud.google.com/%s' % bucket_name
tag_language = os.getenv('LANG_TAG', 'en')
timestamp_tz = os.getenv('TIMESTAMP_TZ', 'US/Pacific')


class Tags(ndb.Model):
    timestamp = ndb.DateTimeProperty(auto_now_add=True)
    count = ndb.IntegerProperty(required=True)

    @classmethod
    def all(cls):
        user = ndb.Key('User', 'default')
        return cls.query(ancestor=user)


class Photo(ndb.Model):
    timestamp = ndb.DateTimeProperty(auto_now_add=True)
    tags = ndb.StringProperty(repeated=True)

    @classmethod
    def tag_filter(cls, tag):
        user = ndb.Key('User', 'default')
        return cls.query(ancestor=user).filter(cls.tags == tag).order(
               -cls.timestamp)

    @classmethod
    def all(cls):
        user = ndb.Key('User', 'default')
        return cls.query(ancestor=user).order(-cls.timestamp)


@app.template_filter('local_tz')
def local_tz_filter(timestamp):
    tz = timezone(timestamp_tz)
    local_timestamp = utc.localize(timestamp).astimezone(tz)
    return local_timestamp.strftime("%Y/%m/%d %H:%M:%S")


def is_image():
    def _is_image(form, field):
        if not field.data:
            raise ValidationError()
        elif field.data.filename.split('.')[-1] not in extensions:
            raise ValidationError()
    return _is_image


def get_labels(photo_file):
    vision_client = vision.Client()
    image = vision_client.image(
                source_uri = 'gs://%s/%s' % (bucket_name, photo_file))
    return image.detect_labels(limit=3)


def translate_text(text):
    if tag_language == 'en':
        return text
    translate_client = translate.Client()
    result = translate_client.translate(text, target_language=tag_language)
    return result['translatedText']


class PhotoForm(Form):
    input_photo = FileField(
        'Photo file (File extension should be: %s)' % ', '.join(extensions),
        validators=[is_image()])


class TagForm(Form):
    tag = SelectField('Tag')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/photos', methods=['GET', 'POST'])
def photos():
    tag = '__all__'
    if request.method == 'POST':
        tag = request.form['tag']
    if tag == '__all__':
        photos = Photo.all().fetch(MAX_PHOTOS)
    else:
        photos = Photo.tag_filter(tag).fetch(MAX_PHOTOS)

    photo_form = PhotoForm(request.form)
    tag_form = TagForm(request.form, select=tag)
    choices = [('__all__', 'Show All')]
    for tag in Tags.all().fetch():
        tag_id = unicode(tag.key.id(), 'utf8')
        choices.append((tag_id, tag_id))
    tag_form.tag.choices = choices

    return render_template('photos.html', storage_path=storage_path,
                           photo_form=photo_form, tag_form=tag_form,
                           photos=photos, max_photos=MAX_PHOTOS)


@app.route('/delete', methods=['POST'])
def delete():
    filename = request.form.keys()[0]
    photo = ndb.Key('User', 'default', 'Photo', filename).get()
    for tag in photo.tags:
        entity = ndb.Key('User', 'default', 'Tags', tag).get()
        if entity:
            entity.count -= 1
            if entity.count == 0:
                entity.key.delete()
            else:
                entity.put()
    photo.key.delete()
    gcs.delete('/%s/%s' % (bucket_name, filename))
    return redirect(url_for('photos'))


@app.route('/post', methods=['POST'])
def post():
    form = PhotoForm(CombinedMultiDict((request.files, request.form)))
    if request.method == 'POST' and form.validate():
        filename = '%s.%s' % (str(uuid.uuid4()),
                              secure_filename(form.input_photo.data.filename))
        content_type = content_types[filename.split('.')[-1]]
        write_retry_params = gcs.RetryParams(backoff_factor=1.1)
        gcs_file = gcs.open('/%s/%s' % (bucket_name, filename), 'w',
                            retry_params=write_retry_params,
                            content_type=content_type,
                            options={'x-goog-acl': 'authenticated-read'})
        for _ in form.input_photo.data.stream:
            gcs_file.write(_)
        gcs_file.close()

        labels = get_labels(filename)
        tags = [translate_text(label.description) for label in labels]
        entity = Photo(id=filename, tags=tags,
                       parent=ndb.Key('User', 'default'))
        entity.put()

        for tag in tags:
            entity = ndb.Key('User', 'default', 'Tags', tag).get()
            if entity:
                entity.count += 1
            else:
                entity = Tags(count=1, id=tag,
                              parent=ndb.Key('User', 'default'))
            entity.put()
        return render_template('post.html', storage_path=storage_path,
                               filename=filename, tags=tags)
    else:
        return redirect(url_for('photos'))
