# Microservice

## Introduction

In this chapter, we will talk about how to apply anywise in a microservice architecture
as well as event driven architecture

EDA is a superset of microservices, it focus on the communication between services.

### `Microservices Architecture`

Microservices architecture is a design pattern where a system is broken down into small, independent services that communicate over a network. Each service focuses on a specific business function, is loosely coupled, and is independently deployable.
These services can be developed, deployed, and scaled independently, enabling agility, flexibility, and fault tolerance.

### `Event-Driven Architecture` (EDA)

Event-driven architecture is a design pattern where systems react to events (changes in state or significant occurrences). In EDA, components (or services) produce, listen to, and react to events, typically through event brokers or message queues.
It allows for asynchronous communication between components, enabling highly decoupled and scalable systems. It is widely used in systems where real-time processing or loosely coupled interaction is needed.

### Orchestration

```mermaid
sequenceDiagram
    participant MS as Message Source
    participant D as Decoder
    box Anywise
        participant CG as Command Guards
        participant CH as Command Handler
        participant EH as Event Handlers
    end
    participant E as Encoder
    participant ES as Event Sink

    %% Command Flow
    alt command
        MS->>D: Raw Message
        Note right of D: decode as command
        D->>CG: Command Message
        Note right of CG: non-bussiness logic
        CG->>CH: Command Message
        Note right of CH: handle command
        Note right of CH: mutate state
        CH->>EH: Publish Events
        EH->>E: Event Message
        Note right of E: encode envents
        E->>ES: sink Events
        Note right of ES: persistent events
    else query
        %% Query Flow
        MS->>D: Raw Message
        Note right of D: decode as query
        D->>CG: Query Message
        Note right of CG: defined behaviors
        CG->>CH: Query  Message
        Note right of CH: execute Query
        CH-->>CG: Query Result
        Note left of CG: validate result
        CG-->>D: Validated Result 
        D-->>MS: Response
    end
```

### Choreography

```mermaid
sequenceDiagram
    participant MS as Message Source
    participant D as Decoder
    box Anywise
        participant EH as Event Handlers
        participant CG as Command Guards
        participant CH as Command Handler
    end
    participant ES as Event Sink

    MS->>D: Raw Message
    Note right of D: Decode as Event
    D->>EH: Event Message
    Note right of EH: react to event
    EH->>CG: Command Message
    Note right of CG: non-business logic
    CG->>CH: Command Message
    Note right of CH: Handle command
    Note right of CH: mutate state
    Note right of CH: emits event
    CH->>ES: Event-carried state transfer
```

In this case, Message source is often a message queue, e.g. kafka