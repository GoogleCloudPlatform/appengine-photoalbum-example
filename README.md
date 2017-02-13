# Photo Album Example

Disclaimer: This is not an official Google product.

This is an example application demonstrating how Vision API and Translation
 API can be used to create a photo album application which automatically add
 appropriate tags to uploaded photos with various languages.

## Products
- [App Engine][1]

## Language
- [Python][2]

## APIs
- [NDB Datastore API][3]
- [Cloud Storage Client API][4]
- [Vision API][5]
- [Translation API][6]

[1]: https://cloud.google.com/appengine/docs
[2]: https://python.org
[3]: https://cloud.google.com/appengine/docs/python/ndb/
[4]: https://cloud.google.com/appengine/docs/python/googlecloudstorageclient/
[5]: https://cloud.google.com/vision/
[6]: https://cloud.google.com/translate/

## Prerequisites
1. A Google Cloud Platform Account
2. [A new Google Cloud Platform Project][7] for this lab with billing enabled
 (You can choose the region for App Engine deployment with advanced options.)
3. Enable the Cloud Vision API and Cloud Translation API from
 [the API Manager][8]

[7]: https://console.developers.google.com/project
[8]: https://console.developers.google.com

## Do this first
In this section you will start your [Google Cloud Shell][9] and clone the
 application code repository to it.

1. [Open the Cloud Console][10]

2. Click the Google Cloud Shell icon in the top-right and wait for your shell
 to open:

 ![](docs/img/cloud-shell.png)

3. Clone the lab repository in your cloud shell, then `cd` into that dir:

  ```shell
  $ git clone https://github.com/GoogleCloudPlatform/appengine-photoalbum-example.git
  Cloning into 'appengine-photoalbum-example'...
  ...

  $ cd appengine-photoalbum-example
  ```

[9]: https://cloud.google.com/cloud-shell/docs/
[10]: https://console.cloud.google.com/

## Customize the language used for tag names

Open 'app.yaml' with a text editor and replace the language code to your
 favorite one from the [supported languages][11].

You can replace the timezone code used for timestamps, too.

```yaml
env_variables:
  LANG_TAG: 'it'              <-- change to your favorite language code.
  TIMESTAMP_TZ: 'Europe/Rome' <-- change to your favorite timezone code.
```

[11]: https://cloud.google.com/translate/docs/languages

## Deploy the application

```shell
$ pip install -r requirements.txt -t lib
$ gcloud beta app create
$ gcloud datastore create-indexes index.yaml
$ gcloud app deploy
```

By executing these commands on the Cloud Shell, the project id is automatically
 applied to the application and the application URL will be
 https://\<project id\>.appspot.com.

You can see Datastore's index creation status from the Cloud Console. Once
 indexes have been created successfully, you can start using the application.

## Clean up
Clean up is really easy, but also super important: if you don't follow these
 instructions, you will continue to be billed for the project you created.

To clean up, navigate to the [Google Developers Console Project List][12],
 choose the project you created for this lab, and delete it. That's it.

[12]: https://console.developers.google.com/project
