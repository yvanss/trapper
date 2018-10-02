===
CSV
===

   Method listing of the CSV REST API. Replace example.com with your domain or IP address (with port if it necessary).


* **research_projects (GET)**

  Return all Research Projects.

  .. code-block:: bash

     curl --request GET http://example.com/api/research_projects/csv/

* **resources (GET)**

  Return all public Resources.

  .. code-block:: bash

     curl --request GET http://example.com/api/resources/csv/

* **collections (GET)**

  Return public Collections with public Resources.

  .. code-block:: bash

     curl --request GET http://example.com/api/collections/csv/

* **classification_projects (GET)**

  Return all Classification Projects.

  .. code-block:: bash

     curl --request GET http://example.com/api/classification_projects/csv/

* **locations (GET or POST)**

  If GET, return public Locations with Resources. If POST return logged user Locations with Resources.

  .. code-block:: bash

     curl --request GET http://example.com/api/locations/csv/

  .. code-block:: bash

     curl -D- -u alice@trapper.pl:alice --request POST http://example.com/api/locations/csv/

* **research_projects (GET: rproject_id)**

  Return single Research Project if user has permission.

  .. code-block:: bash

     curl -D- -u alice@trapper.pl:alice --request GET http://example.com/api/research_projects/<rproject_id>/csv/

* **resources (GET: user_id)**

  Return user Resources. ID value is compared with the owner ID.

  .. code-block:: bash

     curl -D- -u alice@trapper.pl:alice --request GET http://example.com/api/resources/filter/user/<user_id>/csv/

* **resources (GET: resource_id)**

  Return single Resource if user is a owner.

  .. code-block:: bash

     curl -D- -u alice@trapper.pl:alice --request GET http://example.com/api/resources/<resource_id>/csv/

* **collections (GET: user_id)**

  Return user public Collections with public Resources.

  .. code-block:: bash

     curl -D- -u alice@trapper.pl:alice --request GET http://example.com/api/collections/filter/user/<user_id>/csv/

* **collection (GET: collection_id)**

  Return single Collection with public Resources.

  .. code-block:: bash

     curl -D- -u alice@trapper.pl:alice --request GET http://example.com/api/collections/<collection_id>/csv/

* **classifications_projects (GET: cproject_id)**

  Return Classifications for Classification project if logged user is an Admin or Collabolator.

  .. code-block:: bash

     curl -D- -u alice@trapper.pl:alice --request GET http://example.com/api/classification_projects/results/<cproject_id>/csv/