*****************
Used technologies
*****************

=======
Backend
=======

The following list of the most important technologies has been used to design Trapper: 

* Linux system

  As a base operating system under which Trapper was developed and tested is the stable
  version of `Debian <http://debian.org>`_

* PostgreSQL

  Database specific extensions that are used by Trapper determine
  `PostgreSQL <http://postgresql.org>`_ as the only supported database

* PostGIS

  This is one of the PostgreSQL extensions, that is used to work with geographic data

* Hstore

  This is one of the PostgreSQL extensions that is used to store more complex
  data in the database

* Gunicorn

  This pure-python application is used to serve Trapper project. More information
  about gunicorn can be found `here <http://gunicorn.org>`_

* Supervisor

  This application is used to control all project related applications
  like celery. More informations can be found `here <http://supervisord.org>`_

* Celery

  This python application is used to run various tasks in asnynchronous mode
  allowing Trapper to work faster. Celery is used to generate
  thumbnails from large files or videos, or to process uploaded collections
  by users. More information can be found `here <http://www.celeryproject.org>`_

* Django

  This is the base backend technology that allows serving a content to a end-user.
  With Django there are few modules worth mentioning as they change way of
  working with project:

  * django rest framework

    `Django application <http://www.django-rest-framework.org/>`_ that brings
    REST API to the project.

  * django taggit

    `Application <https://github.com/alex/django-taggit>`_ that gives ability
    to create tags to any content created in the project. Trapper uses it to
    give ability to comment on created resources and their classifications.

  * django allauth

    This `application <https://github.com/pennersr/django-allauth>`_ is used
    to automate registration and authentication process.

  * South

    Since django version used in the project doesn't support migrations itself yet,
    `South <http://south.aeracode.org/>`_ is used to give ability to maintain
    Django ORM changes

  * pykwalify

    This `small library <https://github.com/Grokzen/pykwalify>`_ is used
    to help working with YAML schemes easier. YAML scheme is used for collection
    uploading

  More about django can be found `here <http://djangoproject.com>`_


=========
Front-end
=========

Trapper's front-end is developed based on three independent solutions:

#1) HTML (version 5) templates and their CSS styles (powered by `SASS <http://sass-lang.com/>`_) 
#2) set of scripts written in pure JavaScript (ECMAscript 5).
#3) all the external libraries and frameworks included in the project:

* Twitter Bootstrap

  `Bootstrap Sass Official <https://github.com/twbs/bootstrap-sass>`_ which is
  official SASS version of `Twitter Bootstrap <http://getbootstrap.com/>`_.
  This library provides a set of HTML components and CSS styles used for
  Trapper scaffold creation.

* Font Awesome

  `Font Awesome <http://fortawesome.github.io/Font-Awesome/>`_ - webfont of
  vector icons used in the project.

* Angular JS

  `Angular JS <https://angularjs.org/>`_ all the grids/tables including their filters
  has been build on top of this Google's framework

* Angular Cookies

  Official `angular module <https://github.com/angular/bower-angular-cookies>`_
  for cookies management.

* Angular Sanitize

  Official `angular module <https://github.com/angular/bower-angular-sanitize>`_
  which improves angular templates data binding.

* Ng-table

  Non-official `angular module <http://bazalt-cms.com/ng-table/>`_ that extends
  HTML tables with multiple configurable features.

* Moment

  Extremaly powerful `library <http://momentjs.com/>`_ for date parsing & manipulation.

* Select2

  Complete `solution <https://select2.github.io/>`_ that extends default HTML select controls.

* Select2 Bootstrap CSS

  `CSS styles <https://github.com/t0m/select2-bootstrap-css>`_ for Select2 so it fits
  Twitter Bootstrap feel & look.

* Bootstrap WYSIHTML5

  `Javascript Plugin <https://github.com/Waxolunist/bootstrap3-wysihtml5-bower>`_ which
  brings WYSIWYG text editor to the table.

* Bootstrap Datepicker http://eternicode.github.io/bootstrap-datepicker/

  `Javascript Widget <http://eternicode.github.io/bootstrap-datepicker/>`_ - simple datepicker.

* Jquery Timepicker

  `Jquery Widget <http://jonthornton.github.io/jquery-timepicker/>`_ which is just a timepicker.

* Bootstrap Datetimepicker

  `Javascript Widget <http://eonasdan.github.io/bootstrap-datetimepicker/>`_ that
  combines both time and date picker.

* Video JS

  This `library <http://www.videojs.com/>`_ extends standard HTML5 video players.

* Video JS Rangeslider

  Video JS `plugin <https://github.com/danielcebrian/rangeslider-videojs>`_ that
  allows to set and get video sequences.
