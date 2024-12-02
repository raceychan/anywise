import typing as ty


class ICommandEnvelope(ty.Protocol):
    """
    Meta data of event
    encryption type, schema, key, and serialization format. etc.

    express the whole process chain of command

    command -> handler -> response | errors
    """

    headers: "CommandMeta"
    command: "ICommand"


class CommandMeta:
    # source: uri, post: users/sessions/chats
    command_source: ...  # commands/command/v1,
    answer: type
    errors: list[Exception]


class ICommand:
    entity_id: str
    command_id: str


class HttpSource: ...


class KafkaSource: ...


class GRPCSource: ...
