**********
Deployment
**********

1. Deployment assumptions

  a) system user that is used to run django application: **web**
  b) home directory is: **/home/web/trapper**
  c) database user is: **trapper**
  d) database password is: **trapper**
  e) for nginx setup **trapper.pl** servername is used. This needs to be changed!
  f) for nginx configuration it's assumed that ssl keys are generated

  Those parameters can be changed, but changing it would require changes in config files

2. System info

  Debian stable with latest update (state on 12.03.2015)
  Setup proper locale

   .. code-block:: text

      locale-gen en_US.UTF-8

3. System packages (install with dependencies suggested from aptitude)

   Those dependencies require *root* priviledges

   .. code-block:: text

      aptitude install postgresql-9.1 postgresql-contrib-9.1 postgresql-9.1-postgis postgresql-server-dev-9.1 python-virtualenv python-dev libxml2-dev libjpeg8-dev libxslt1-dev libgeos-dev libproj-dev libgdal-dev nginx supervisor rabbitmq-server libav-tools

4. Postgis manual installation 101:

   Compilation postgis requires *root* priviledges

   .. code-block:: text

      wget http://download.osgeo.org/postgis/source/postgis-2.1.5.tar.gz
      tar zxvf postgis-2.1.5.tar.gz
      cd postgis*
      ./configure
      make
      make install

   For further details see README.postgis

5. Configure database

   Database configuration is done as user *postgres*

   .. code-block:: text

      su postgres

      # as a pass set "trapper"
      createuser trapper -R -d -S -E -P

      psql -d template1 -c 'create extension postgis;'
      psql -d template1 -c 'create extension hstore;'

6. Setup django

   This section is done by *web* user

   .. code-block:: text

      bin/devel.sh
      bin/reset_database.sh

   After project has been configured it is required to configure email
   backend settings, so project is able to send emails to users (especially
   for authentication process)

   This is done by modifying settings:

   .. code-block:: python

     * EMAIL_HOST
     * EMAIL_HOST_PASSWORD
     * EMAIL_HOST_USER
     * EMAIL_PORT

   .. warning::
Those settings should not be changed in `settings.py` file, because
      it can be accidently pushed to repository. Instead of `settings_local.py`
      should be used (this file is excluded from git and read by `settings.py`)

  .. note::
If local SMTP server is used, it has to be configured to be able to send
      messages. Configuration of SMTP server is out of scope of this
      documentation

  Additionaly when new user or new research project is created, mail is sent to
  admins defined in standard django setting `settings.ADMINS`.

  .. note::
It is preffered to define admin list in `settings_local.py` to protect
    emails from being publicly available in repository.

  .. warning::
Users registered in a system with admin status aren't taken into account,
    because in general django doesn't require users to have valid email at all,
    and admins should be defined outside database scope, when issues with
    database occur, then then `ADMINS` will get notification about it.


7. Nginx

   Instruction described in this section requires *root* priviledges

   Copy or symlink **conf/trapper.nginx.conf** into nginx config directory
   (by default it's */etc/nginx/sites-available*), then symlink to
   */etc/nginx/sites-enabled*)

   Configuration assumes that you have already generated SSL certificates.
   You can get free SSL certificates i.e. from startssl.com

   Restart nginx

   .. code-block:: text

      /etc/init.d/nginx restart

   If you're using default configuration then you can edit */etc/hosts* and add entry:

   .. code-block:: text

      127.0.0.1  trapper.pl

   and then test your website deployment under:

   .. code-block:: text

      https://trapper.pl

   **WARNING** You should not use *trapper.pl* in your production unless you are an owner
   of this domain. Also most probably the browser will inform you about wrong ssl certificate.


8. Supervisor

   Instruction described in this section requires *root* priviledges

   Copy or symlink **conf/supervisor.conf** into **/etc/supervisor/conf.d**
   and restart supervisor

  .. code-block:: text

     /etc/init.d/supervisor restart

  If everything is setup correctly then supervisorctl should look like this:

  .. code-block:: text

      # supervisorctl
      trapper                          RUNNING    pid 30969, uptime 0:01:26
      trapper-celery-beat              RUNNING    pid 30970, uptime 0:01:26
      trapper-celery-cam               RUNNING    pid 30968, uptime 0:01:26
      trapper-celery-worker            RUNNING    pid 30971, uptime 0:01:26
