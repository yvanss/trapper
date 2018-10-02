*****************
External services
*****************

Besides the internal, built in functionalities, there are a few external services used in Trapper, that are either required or preffered to be used for
users convenience.

=============
Email service
=============

Email service is the only one that is required for trapper to work. Access to
SMTP server is required for notification about:

* user email account creation - for user, who created account
* user email account creation - for admins
* research project creation - for user, who created project
* research project creation - for admins

It is the **most preferable** to have email service configured, otherwise users and
admins won't get email notifications and working with projects may become time-consuming and unmenagable.

:doc:`Deployment <deployment>` section of the documentation contains required
project configuration settings for email service to work.

.. warning::
SMTP server configuration is not documented here. Project administrator
  is free to use the most suitable solution and refer to it's
  documentation.

======
Celery
======

`Celery <http://celery.readthedocs.org/en/latest/index.html>`_ is a external
service used for asynchronous task running. This is especially useful when a
user wants to upload large files, that have to be processed, and processing
them could consume a lot of time. By using `Celery`, this process can be much more
efficient, because a user gets only notification that the data has been received
and the process will be running in background.

There are settings that can change thumbnail generation process:

* :envvar:`CELERY_DATA_ROOT` - base directory where celery store processed files
* :envvar:`CELERY_ENABLED` - if set to False then all tasks will be launched
  synchronously (default is `True`)

Trapper uses celery in two core places:

------------------------------
Resource thumbnails generation
------------------------------

Each resource can have a thumbnail assigned. For audio files there is default one
assigned, but for images and videos the thumbnail is generated from given media.
Genrating this media can take a lot of time (i.e. for very large images), that's
why this generation process is moved to separate asynchronous task and done by
celery.

Thumbnail generation uses additional settings:

* :envvar:`CELERY_MIN_IMAGE_SIZE` - minimal image size in `Bytes` above which celery
  will be used (if enabled). Default is `10MB`
* :envvar:`DEFAULT_THUMBNAIL_SIZE` - thumbnail image dimensions. By default it's  `96x96` px
* :envvar:`VIDEO_THUMBNAIL_ENABLED` if set to `False` then thumbnails won't be generated
  for video files.

.. note::
Generating thumbnails for images uses `PIL`

.. note::
Generating thumbnails for video uses external tool `avconv` which has to be installed
  within the operating system.

----------------------------
Collection upload processing
----------------------------

Collection upload action allow users to upload (or preselect) previously
uploaded zip files to be processed. After collection upload, new resources and collections
will be registered in the project.

Because archives that users want to process can be very large and processing them
could be time consuming, this process is delegated to celery which will
process them asynchronously without blocking user interaction with the project.

Upload processing has no custom settings to control celery. Tasks are always
delegated to celery unless celery is disabled with :envvar:`CELERY_ENABLED`


==========================
Alternative upload methods
==========================

Because users may want to upload very large files, and uploading them using
browser could be inefficient (i.e. no reasume is supported), alternative
method for assigning files has been implemented.

Alternative method is implemented to support three actions:

* recource creation (either for `file` and `extra file`)
* collection upload (for `archive file`)
* for `gpx` files in location upload


Base directory to look for uploaded files is defined by setting
:envvar:`EXTERNAL_MEDIA_ROOT`.

For paths used in :doc:`deployment <deployment>` section base directory for
altenrative uploaded files defaults to: :file:`/home/web/trapper/trapper/external_media`.

Each user has few own directories that are automaticaly created when user
account is activated. For user `alice` and above base path following paths will
be created:

* :file:`/home/web/trapper/trapper/external_media/alice/resources/`

  for storing files used with resource create action.

  Processed files will be moved into celery data directory.

* :file:`/home/web/trapper/trapper/external_media/alice/collections/`

  for storing files used with collection upload action.

  Processed files will be moved into celery data directory.

* :file:`/home/web/trapper/trapper/external_media/alice/locations/`

  for storing files used with location upload action.

  Processed files will be **removed**.

------------------
Example for (s)ftp
------------------

Assume :doc:`deployment <deployment>` section paths.

If system administrator wants to enable alternative upload through (s)ftp server
for user `alice`, he needs to configure `alice` account credentials and
point home directory to :file:`/home/web/trapper/trapper/external_media/alice/
    and give credentials to the user.

    The user connecting through (s)ftp will see `resources`, `collections` and
`locations` directory and will be able to upload files there.

---------------
Example for ssh
---------------

Assume :doc:`deployment <deployment>` section paths.

If the system administrator wants to enable alternative upload through ssh server
for user `alice`, it is required to configure `alice` account credentials and
point shell home directory to :file:`/home/web/trapper/trapper/external_media/alice/
    and give credentials to a user. For ssh `authorized_keys` can be used.


The user connecting through ssh will see `resources`, `collections` and
`locations` directory and wil be able to upload files there.

.. note::
This implementation is a alternative upload method, but system administrator
  has to make sure that users **will have access to their directories** and
  user which is used to run projects **can read them**.

.. warning::
Configuring external services for alternative upload like (s)ftp, ssh or other
  is out of scope of this documentation. System administrator has to decide what
  method will be used and refer to it's documentation.