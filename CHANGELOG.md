# ChangeLog

## Versions

### version 0.1.1

- contexted handler
- command guard

## version 0.1.2

replace GuardRegistry, ListenerRegistry, HandlerRegistry with a new `MessageRegistry`
reduce boilerplace code, make api easier to work with

now will build guards before send, now the order of anywise.include(guard_registry) does not matter

## version 0.1.3

- add `BaseGuard`, user can inherit from it then override `async def __call__`.
- update docs
- improve command resolve logic

## version 0.1.4

- add dependency injection to guard
- scoped send

## version 0.1.5

- pre-defined `Event` class
- docs
- global guard

## version 0.1.6

- refactory MessageRegistry
- add a source support

## version 0.1.7

register union types


## version 0.1.8

- new, `MessageRegistry.register` method
provides a flexible and versatile way to register handlers in an imperative manner.

```py
user_registry.register(
    LogginGuard,
    handler_create,
    handler_update,
    pre_hanldes=[validate_command, add_start_time],
    post_handles=[validate_result],
)
```


### version 1.0.0
