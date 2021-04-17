# TODO

## Before next release

- DONE ADD add state and state message to callbacks, to allow more useful failure notifications.
- DONE ADD add state to AiohttpAction
- DONE ADD add observers to AiohttpAction, updated when action state is changed
- DONE CHANGE retry_limit to max_attempts

- DONE CHANGE Simplify worker factory, add some stat reporting (log)
  - Move test code to src
  - goal is to support consumers who can report on their stats.
  - make code less complicated. Make fewer assumptions.
  - use consumer class? can store state

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
