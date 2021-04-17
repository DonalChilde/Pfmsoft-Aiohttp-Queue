=======
History
=======

0.1.8 (2021-04-17)
------------------

* ADD add state and state message to callbacks, to allow more useful failure notifications.
* ADD add state to AiohttpAction
* ADD add observers to AiohttpAction, updated when action state is changed
* CHANGE retry_limit to max_atttempts
* CHANGE Simplify worker, add some stat reporting (log)


0.1.7 (2021-04-15)
------------------

* ADD repr to all classes
* ADD logging to action success, retry, fail
* CHANGE drop log callbacks as redundant
* FIXED csv callback not respecting path templates


0.1.6 (2021-04-06)
------------------

* changed file callback template args name to path_values

0.1.5 (2021-04-05)
------------------

* added pyyaml to requirements_dev.txt

0.1.4 (2021-04-05)
------------------

* added CheckForPages callback - If an action detects paged data, makes more actions to retieve that data and appends it to the parent action.result

0.1.3 (2021-04-01)
------------------

* fixed missing . in file_ending

0.1.2 (2021-04-01)
------------------

* added option to process file path as a string.Template, with provided arguments, to file saving callbacks.
* added SaveListOfDictResultToCSVFile callback.

0.1.1 (2021-03-29)
------------------

* Dropped ResponseMetaToJson callback, and added response_meta_to_json() to AiohttpAction in its stead.

0.1.0 (2021-03-29)
------------------

* First release on PyPI.
