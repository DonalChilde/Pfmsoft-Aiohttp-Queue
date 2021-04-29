# TODO

## Before next release

- CHANGE make do action runner singular, add do_sequential to handle multiple actions no queue.
- DONE New AiohttpAction interface
  - test
  - translate callbacks
- CHANGE option to Use safe_substitute for template paths? https://docs.python.org/3/library/string.html#template-strings
- CHANGE add repr of context to fail logging
- FIX add observers to action init
- CHANGE catch callback exceptions, and fail callbacks in the success, retry, fail maethods.
  - if a callback does not want to have callbackstate.fail on exception, it should catch them inside.

## testing

- make a list of actions to fill queue
  - 10 20 50 ?
  - some actions should fail.
- test for failed callbacks.

## Future releases

- write tests to cover all the callbacks.
  - check file output
- Document all the modules

- get 100% coverage
