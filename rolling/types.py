from dataclasses import dataclass
import typing

# TODO : replace everywhere
WorldRowI = typing.NewType("WorldRowI", int)
WorldColI = typing.NewType("WorldRowI", int)
WorldPoint = typing.NewType("WorldPoint", typing.Tuple[WorldRowI, WorldColI])

MessageAge = typing.NewType("MessageAge", int)
MessageTimestamp = typing.NewType("MessageTimestamp", int)
MessageAuthorId = typing.NewType("MessageAuthorId", str)
MessageContent = typing.NewType("MessageContent", str)

CharacterId: typing.NewType("CharacterId", str)
ResourceId: typing.NewType("ResourceId", str)
Quantity: typing.NewType("Quantity", float)
StuffType: typing.NewType("StuffType", str)


@dataclass
class CachedMessage:
    timestamp: MessageTimestamp
    author_id: MessageAuthorId
    message: MessageContent
