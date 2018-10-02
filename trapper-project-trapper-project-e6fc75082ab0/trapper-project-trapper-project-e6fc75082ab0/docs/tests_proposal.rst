=============
Tests proposl
=============

Test proposal is written in more generic way, but based on this description
all unittests can be calculated, so task measurable.

* If action require selecting some item from list (i.e.) collection,
  then single extra test will be performed to validate that this list
  has proper values.

* If action requires to send valid pks list, then always invalid pks will
  be added and they will be checked for exclusion. This does not require
  more tests (single assert will do that)

.. note::
  If for given criteria test fails, it will be treated as bug and fixed.

.. warning::
  Please do not modify this file to avoid making mess.
  Add proposals in issue #252. Each test as single comment with number. After
  proposal test requirements has been approved, this document will be updated
  by author.

.. warning::
  Those tests won't test frontend. Purpose is to make sure that user can or
  cannot do when data is sent to server.

======
Actors
======

* `root` - sysadmin user
* `alice` - regular user
* `ziutek` - regular user
* `john` - regular user
* `eric` - inactive user
* `anon` - unauthenticated user

========
Accounts
========

* [DONE] mails are sent when user `amanda` register
* [DONE] `amanda` is inactive
* [DONE] mail is sent to `amanda` when `root` activate account
* [DONE] external directories are created when `root` activate account
* [DONE] `amanda` change password
* [DONE] `amanda` update profile

=========
Messaging
=========

* [DONE] test listing inbox, outbox messages for `alice`
* [DONE] `alice` checks message box in dashboard
* [DONE] send message from `alice` to: `ziutek`, `alice`, `eric`
* [DONE] test access `anon` to inbox, outbox, creating message

ADDITIONAL:
* [DONE] `alice` cannot access message details that `ziutek` sent to `john`
* [DONE] `anon` cannot access any message details


================
Resource request
================

* [DONE] test listing requests for `alice`
* [DONE] test approve request from `ziutek` by `alice`
* [DONE] test reject request from `ziutek` by `alice`
* [DONE] test revoke approve request from `ziutek` by `alice`
* [DONE] test access by `anon` to list, approve, reject, revoke


==================
Collection request
==================

* [DONE] test listing requests for `alice`
* [DONE] test approve request from `ziutek` by `alice`
* [DONE] test reject request from `ziutek` by `alice`
* [DONE] test revoke approve request from `ziutek` by `alice`
* [DONE] test access by `anon` to list, approve, reject, revoke

=========
Resources
=========

resource actions: details, create (uploaded file, preselected), update,
  delete (singe/multi), ask for permissions, bulk update, create collection,
  define prefix, add to collection

resource roles: owner, manager, no-roles

* [DONE] `anon` resources listing
* [DONE] `alice` resources listing
* [DONE] `anon` access for resource actions
* [DONE] `alice` perform all resource actions for resource roles
* [DONE] thumbnail generation for image, video (without celery)

NOTES:
* create action for roles has no meaning
* CREATE role has no meaning
* MANAGER role is not used


ADDITIONAL TESTS (for data, not permissions):
* [DONE] test for creation (with file upload)
* [DONE] test for creation (with file preselected)
* [DONE] test for update
* [DONE] test for delete
* [DONE] test for delete multiple
* [DONE] test for ask permissions
* [DONE] test for bulk update
* [DONE] test for define prefix

===========
Collections
===========

collection actions: create, details, update, delete (single/multi), ask for
  permissions, bulk update, add to collection

collection roles: as owner, manager, no-roles

* [DONE] `anon` collection listing
* [DONE] `alice` collection listing
* [DONE] `anon` access for collection actions
* [DONE] `alice` performs all collection actions for collection roles
* [DONE] resources listing in collection details
* [DONE] collection upload (without celery): with uploaded file and preselected one
* [DONE] `alice` checks collection box in dashboard

ADDITIONAL:
* [DONE] test for create collection
* [DONE] test for add to collection
* [DONE] test for update
* [DONE] test for delete single
* [DONE] test for delete multi
* [DONE] test for ask for permissions
* [DONE] test for bulk update

NOTES:
* create action for roles has no meaning
* CREATE role has no meaning
* MANAGER role is not used

=================
Research projects
=================

research project actions: details, create, update, delete (single/multi),
  add collection to research project,
research project roles: owner, admin, expert, collaborator, no-roles


* [DONE] `anon` research project listing
* [DONE] `alice` research project listing for research project roles
* [DONE] `anon` access for research project actions
* [DONE] `alice` performs all research project actions for research project roles
* [DONE] collection listing in research project details
* [DONE] classification projects listing in research project details
* [DONE] `alice` checks research projects box in dashboard

ADDITIONAL:
* [DONE] test for create
* [DONE] test for update
* [DONE] test for delete single
* [DONE] test for delete multi
* [DONE] test for adding collection to research project
* [DONE] test for removing collection from research project
* [DONE] test for removing multiple collections from research project
* [DONE] `alice` performs all research project actions for research project roles

  - remove collection from research project
  - remove multiple collections from research project


NOTES:
* Roles have no influence for research project list
* Roles have no influence for creating project


=======================
Classification projects
=======================

classification project actions: details, create, update, delete (single/multi),
    activate/deactivate sequences, activate/deactivate crowdsourcing,
    ongoing/finished status, remove collection from project
    add collection to classification project,
classification project roles: owner, admin, expert, collaborator, no-roles


* [DONE] `anon` classification project listing
* [DONE] `alice` classification project listing for clasification project roles
* [DONE] `anon` access for classification project actions
* [DONE] `alice` performs all classification project actions for classification project roles
* [DONE] collection listing in classification project details
* [DONE] remove classification project with approved classification behaviour
* [DONE] `alice` checks classification projects box in dashboard

ADDITIONAL:
* [DONE] test for create
* [DONE] test for update
* [DONE] test for delete single
* [DONE] test for delete multi
* [DONE] test for adding collection to classification project
* [DONE] test for removing collection from classification project
* [DONE] test for removing multiple collections from classification project

==============
Classificators
==============

classificator actions: details, create, update, delete (single/multi), clone

* [DONE] `anon` classificator listing
* [DONE] `alice` classificator listing
* [DONE] `anon` access for classificator actions
* [DONE] `alice` performs all classificator actions

ADDITIONAL:
* [DONE] test for create: clean, only static, only dynamic, both
* [DONE] test for update: name/template, static form, dynamic form
* [DONE] test for delete single classificator
* [DONE] test for delete single classifficator  with at least one project with approved classification
* [DONE] test for delete multi
* [DONE] test for cloning

=========
Sequences
=========

sequence actions: create, update, delete
sequence roles: the same as classification project roles

* [DONE] `anon` classificator listing
* [DONE] `alice` classificator listing
* [DONE] `anon` access for classificator actions
* [DONE] `alice` performs all classificator actions for all roles

ADDITIONAL:
* [DONE] test for create
* [DONE] test for update
* [DONE] test for delete

NOTES:
- details for sequence is not implemented

===============
Classifications
===============

classification actions: details, delete, create tags
classification roles: the same as classification project roles

* [DONE] `anon` classification listing
* [DONE] `alice` classification listing
* [DONE] `anon` access for classificator actions
* [DONE] `alice` performs all classification access actions

ADDITIONAL:
* [DONE] test for accessing details
* [DONE] test for delete
* [DONE] test for creating tags


================
Classify process
================

classify actions: details, create, update, approve, create multiple
classify classification box actions: approve

classify roles: the same as classification project roles

* [DONE] `anon` classify access
* [DONE] `anon` access for classify actions + classify classification box actions
* `alice` performs all classification access actions for classify roles
* `alice` checks access for all classify classification box actions for classify
  roles
* `alice` performs approve action from classify classification box actions for
  classify roles

MOVED FROM CLASSIFICATION PROJECT
* remove classificator from classification project - and try to classify
  resource

ADDITIONAL:
* test for creating new classification with static and dynamic data
* test for update classification
* test for approve classification
* test for create multiple classifications
* test for approve from classification box

NOTE:
* Details is checking for rendering classify form before before create/update
* classification box details action was tested in classification list
* Update and classification box edit actions are the same


==================
Geomap - Locations
==================

location actions: delete, activate/deactivate locations

* [DONE] `anon` location listing
* [DONE] `alice` location listing
* [DONE] `anon` access for location actions
* [DONE] `alice` access for location actions
* [DONE] `alice` performs all location actions

Testing locations in map interface, map interface is out of scope

===============
Technical tests
===============

This secion could be updated even when test is is already approved.

* [DONE] Test for security in SafeTextField (stripping dangerous code)
* [DONE] parse_int function

* [DONE] Update all 'action' tests where 'pks' is used to include invalid value and test it