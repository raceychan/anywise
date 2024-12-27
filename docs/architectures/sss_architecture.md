# Source-Service-Sink Architecture

Message Source sends commnad to command handler,
command handler handles the command, mutate state and persist it to database,
then record the side-effect by emitting a event, which will be handled by event handles,
event handles will either handle the event directly, or forward it to other services
the event will eventually be stored in the event sink.

```mermaid
sequenceDiagram
    participant MS as Message Source
    box Service
        participant CH as Command Handler
        participant EH as Event Handlers
    end
    participant ES as Event Sink

    %% Command Flow
    alt command
        MS->>CH: Command Message
        Note right of CH: handle command
        Note right of CH: mutate state
        CH->>EH: Publish Events
        EH->>ES: Event Message
    else query
        %% Query Flow
        MS->>CH: Query Message
        CH-->>MS: Query Result 
    end
```