=======
History
=======

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
