# Architecture

we will talk about how to use anywise for applying architectural patterns in event driven microservices

## Terms and concepts

Before we start, let's clearify some terms and concept, so that you know what do we mean when we use these words.

- A `Message` is a pure data object that is used to carry data that is needed for our application to respond. Also known as data transfer object.

- A `Message` class often contains no behavior(method), and is immutable.

### Command, Query and Event

- `Command` carries pre-define intend, each command should have a corresponding `handler` that will mutate state, in the context of DDD, each command will always trigger a behavior of an aggregate root.

- `Query` is a subclass of Command, where it also carry pre-define intend, but instead of mutate state, it will be responded by a present state of the application.

In other words, command and query corresponds to write and read.

- `Event` carries a record of an interested domain-related activity, often captures the side effect caused by a `Command`. an `Event` can have zero to many `listener`s