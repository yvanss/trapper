====
JSON
====

   Method listing of the JSON REST API. Replace example.com with your domain or IP address (with port if it necessary).

   For better results, use **Postman (Google chrome extension)** instead of curl.


* **research_projects (GET)**

  Return all Research Projects.

  .. code-block:: bash

     curl --request GET http://example.com/api/research_projects/json/

* **resources (GET)**

  Return all public Resources.

  .. code-block:: bash

     curl --request GET http://example.com/api/resources/json/

* **resources_file (GET or POST: resource_id)**

  Download single Resource file.

  .. code-block:: bash

     curl --request GET http://example.com/api/resources/file/<resource_id>/

  .. code-block:: bash

     curl -D- -u alice@trapper.pl:alice --request POST http://example.com/api/resources/file/<resource_id>/

* **collections (GET)**

  Return public Collections with public Resources.

  .. code-block:: bash

     curl --request GET http://example.com/api/collections/json/

* **classification_projects (GET)**

  Return all Classification Projects.

  .. code-block:: bash

     curl --request GET http://example.com/api/classification_projects/json/

* **locations (GET or POST)**

  If GET, return public Locations with Resources. If POST return logged user Locations with Resources.

  .. code-block:: bash

     curl --request GET http://example.com/api/locations/json/

  .. code-block:: bash

     curl -D- -u alice@trapper.pl:alice --request POST http://example.com/api/locations/json/

* **research_projects (GET: rproject_id)**

  Return single Research Project if user has permission.

  .. code-block:: bash

     curl -D- -u alice@trapper.pl:alice --request GET http://example.com/api/research_projects/<rproject_id>/json/

* **resources (GET: user_id)**

  Return user Resources. ID value is compared with the owner ID.

  .. code-block:: bash

     curl -D- -u alice@trapper.pl:alice --request GET http://example.com/api/resources/filter/user/<user_id>/json/

* **resources (GET: resource_id)**

  Return single Resource if user is a owner.

  .. code-block:: bash

     curl -D- -u alice@trapper.pl:alice --request GET http://example.com/api/resources/<resource_id>/json/

* **collections (GET: user_id)**

  Return user public Collections with public Resources.

  .. code-block:: bash

     curl -D- -u alice@trapper.pl:alice --request GET http://example.com/api/collections/filter/user/<user_id>/json/

* **collection (GET: collection_id)**

  Return single Collection with public Resources.

  .. code-block:: bash

     curl -D- -u alice@trapper.pl:alice --request GET http://example.com/api/collections/<collection_id>/json/

* **classifications_projects (GET: cproject_id)**

  Return Classifications for Classification project if logged user is an Admin or Collabolator.

  .. code-block:: bash

     curl -D- -u alice@trapper.pl:alice --request GET http://example.com/api/classification_projects/results/<cproject_id>/json/

* **add_classifications_results (PUT)**

  Add static and dynamic attribute sets values for existing Classification project and their Resources.

  .. code-block:: bash

     curl -D- -u alice@trapper.pl:alice -H "Accept: application/json" -H "Content-type: application/json" -X PUT -d '{"rproject_id":"2","cproject_id":"3","resources":[{"classification":{"attribut_sets":{"data_dynamic_form":[{"data_dynamic_form_row":{"Age":"Very old","Number":"666","Sex":"Female","annotations":"[]","comments":"test","species":""}},{"data_dynamic_form_row":{"hehe":"inny tekst","test":"jeszcze inne sprawy"}}],"data_static_form":{"EMPTY":"True","FTYPE":"3","Quality":"Bad"}}},"classification_project_collection_id":"4","resource_id":"107"}]}' http://example.com/api/classification_projects/results/add/