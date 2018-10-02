**********
X-Sendfile
**********

X-Sendfile allows permission verification from django before specific content
is sent to a user. Django however, won't serve the content - it is done by web
server that handles it more efficient. 

.. note::

   This documentation uses configuration taken from
   :doc:`Deployment <deployment>`

-----
Logic
-----

Basic X-Sendfile flow:

* Request from nginx is sent to trapper application
* Django determines if user has right permissions to see the content

  - if access is granted special headers will be passed in response to inform nginx how to proceed

  - if access is not granted negative (forbidding) response is returned (or any other logic
    like serving special image)
* response is received back by nginx
* proper content is sent to user by nginx

--------
Settings
--------

.. code-block:: python

  # Base place for media that should be served through x-sendfile
  SENDFILE_ROOT = MEDIA_URL

  # Default directory within SENDFILE_ROOT for files served through x-sendfile
  SENDFILE_MEDIA_PREFIX = 'protected/'

  # Used by middleware to fake sendfile on development instances
  # DO NOT USE IT ON PRODUCTION
  SENDFILE_DEV_SERVER_ENABLED = False

  # Header that will be added to response. Differes between web servers.
  # This one is for nginx
  SENDFILE_HEADER = 'X-Accel-Redirect'


---------
Resources
---------

Resources part of storage application uses X-Sendfile to limit the access to:

- file
- file thumbnail
- extra file

Trapper doesn't use direct urls to images/movies/audio. All it's media is
stored in `SENDFILE_ROOT` + `SENDFILE_MEDIA_PREFIX` and each handled field
has its own method responsible for returning proper url.
Instead of direct url to the media, special serve view url is returned.

In that view requested file for given resource is verified against currently
logged in user. If a user can view details of a resource, then media can be
served by nginx and django will add special headers, otherwise default image
is served.

.. note::

   This view uses `Resource.can_view` method which is also used to determine
   if a user can access details page.

   No new logic for accessing is defined for x-sendfile validation.

-----
nginx
-----

Nginx configuration is minimalistic to use X-Sendfile:

.. code-block:: text

    location /media/protected/ {
         alias /home/web/trapper/trapper/media/protected/;
         internal;
    }

Using `internal` flag allows files from a specified location to be served
only by nginx.

-----
Admin
-----

Since nginx won't serve media directly, admin panel has to be altered
to allow using fileinput widget (which shows url to actual media url if
given field is not empty).

Widget combined with special view allows user to see media from protected
directory directly but **only** if request is made by user that **is staff**
or **is superuser** (in django). Otherwise forbidden response is returned.

Urls for direct access looks like:


.. code-block:: text

   /serve/direct/?file=protected/storage/resource/example_image.jpg

GET parameter `file` contains relative path to media (`MEDIA_URL` is ommited)

--------
Examples
--------

Assumming that

* Resource `R1` has pk=5 and is `image`
* `alice` is regular user that owns resource `R1`
* `staff11 is regular user with no access to resource `R1`
* `sysadmin` is django superuser (or staff)


* Anonymous user or `staff1`:

  - will see **default** image on url

    .. code-block:: text

       /storage/resource/media/5/file/

  - will see **default** image thumbnail on url

    .. code-block:: text

       /storage/resource/media/5/tfile/

  - will see **default** extra media file (if specified) on url

    .. code-block:: text

       /storage/resource/media/5/efile/

  - will have **no access** to direct serve like:

    .. code-block:: text

       /serve/direct/?file=protected/storage/resource/example_image.jpg

  - will have **no access** to media path:

    .. code-block:: text

       /media/protected/storage/resource/example_image.jpg


* `alice` user:

  - will see **real** image on url

    .. code-block:: text

       /storage/resource/media/5/file/

  - will see **real** image thumbnail on url

    .. code-block:: text

       /storage/resource/media/5/tfile/

  - will see **real** extra media file (if specified) on url

    .. code-block:: text

       /storage/resource/media/5/efile/

  - will have **no access** to direct serve like:

    .. code-block:: text

       /serve/direct/?file=protected/storage/resource/example_image.jpg

  - will have **no access** to media path:

    .. code-block:: text

       /media/protected/storage/resource/example_image.jpg


* `sysadmin`:

   - will **have access** to direct serve like:

    .. code-block:: text

       /serve/direct/?file=protected/storage/resource/example_image.jpg

   - will have **no access** to media path:

    .. code-block:: text

       /media/protected/storage/resource/example_image.jpg


   - Other urls will be available depend if `sysadmin` has permissions to view
     details (like `alice`) or not (like `staff1`).

.. note::

  **default** image can be customized at will and is located here:

  trapper/trapper/apps/storage/static/trapper_storage/img/thumb_forbidden.jpg