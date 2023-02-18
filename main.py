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


import os, uuid, datetime, pytz

from flask import Flask, render_template, request, redirect, url_for
from google.cloud import vision, translate, storage, datastore


app = Flask(__name__)

MAX_PHOTOS = 20

project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
bucket_name = '{}.appspot.com'.format(project_id)
storage_path = 'https://storage.cloud.google.com/{}'.format(bucket_name)
tag_language = os.getenv('TAG_LANG', 'en')
timestamp_tz = os.getenv('TIMESTAMP_TZ', 'US/Pacific')


def get_tags():
    tags = []
    client = datastore.Client()
    query = client.query(kind='Photos')
    for e in query.fetch():
        for tag in e.get('tags'):
            tags.append(tag)
    tags = set(tags)
    return tags


def get_labels(photo_file):
    uri = 'gs://{}/{}'.format(bucket_name, photo_file)
    client = vision.ImageAnnotatorClient()
    image = vision.Image()
    image.source.image_uri = uri
    response = client.label_detection(image=image, max_results=3)
    return [label.description for label in response.label_annotations]


def translate_text(labels):
    if tag_language == 'en':
        return labels
    client = translate.TranslationServiceClient()
    response = client.translate_text(
        contents=labels, target_language_code=tag_language,
        parent='projects/{}'.format(project_id))
    return [label.translated_text for label in response.translations]


def get_photos(max_photos, tag='__all__'):
    client = datastore.Client()
    query = client.query(kind='Photos')
    if tag != '__all__':
        query.add_filter('tags', '=', tag)
    query.order = '-timestamp'
    photos = []
    for photo in query.fetch(limit=max_photos):
        ts = photo['timestamp'].astimezone(pytz.timezone(timestamp_tz))
        timestamp = datetime.datetime.strftime(ts, '%Y-%m-%d %H:%M:%S %Z')
        photo['timestamp'] = timestamp
        photos.append(photo)
    return photos


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/photos', methods=['GET', 'POST'])
def photos():
    tag = '__all__'
    if request.method == 'POST':
        tag = request.form.get('tag')
    photos = get_photos(MAX_PHOTOS, tag=tag)

    tag_choices = [('__all__', 'Show All')]
    for tag_name in get_tags():
        tag_choices.append((tag_name, tag_name))

    return render_template('photos.html', storage_path=storage_path,
                           tag_choices=tag_choices, photos=photos,
                           max_photos=MAX_PHOTOS, tag=tag)


@app.route('/delete', methods=['POST'])
def delete():
    filename = request.form.get('delete')

    client = datastore.Client()
    query = client.query(kind='Photos')
    query.add_filter('filename', '=', filename)
    for entity in query.fetch():
        client.delete(entity.key)

    bucket = storage.Client().bucket(bucket_name)
    blob = bucket.blob(filename)
    blob.delete()

    return redirect(url_for('photos'))


@app.route('/post', methods=['POST'])
def post():
    f = request.files.getlist('file')[0]
    if f.filename =='':
        return redirect(url_for('photos'))

    local_file = '/tmp/{}'.format(f.filename)
    target_file = str(uuid.uuid4())
    f.save(local_file)

    bucket = storage.Client().bucket(bucket_name)
    blob = bucket.blob(target_file)
    blob.upload_from_filename(local_file)
    blob.acl.reload() # reload the ACL of the blob
    acl = blob.acl
    acl.all_authenticated().grant_read()
    acl.save()
    os.remove(local_file)

    labels = get_labels(target_file)
    tags = translate_text(labels)
    ts = datetime.datetime.now().astimezone(pytz.timezone(timestamp_tz))

    client = datastore.Client()
    key = client.key('Photos')
    entity = datastore.Entity(key=key)
    entity['filename'] = target_file
    entity['tags'] = tags
    entity['timestamp'] = ts
    client.put(entity)

    timestamp=datetime.datetime.strftime(ts, '%Y-%m-%d %H:%M:%S %Z')
    return render_template(
            'post.html', storage_path=storage_path,
            filename=target_file, tags=tags, timestamp=timestamp)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
