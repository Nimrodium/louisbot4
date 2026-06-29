from functools import reduce
from typing import cast

from nextcord.ext import commands
from nextcord.message import Message
from nextcord.types.channel import GuildChannel, TextChannel


class Bridge:
    NAME = "name"
    CHANNELS = "channels"

    def __init__(self, bridge: dict):
        # t.0: guildid; t.1: channelid
        def get_server_channel_pairs(channels: list[str]) -> list[tuple[str, str]]:
            return cast(
                list[tuple[str, str]],
                list(map(lambda s: tuple(s.split(".")), channels)),
            )

        self.name = bridge[self.NAME]
        self.channels: list[tuple[str, str]] = get_server_channel_pairs(
            bridge[self.CHANNELS]
        )

    @classmethod
    def get_bridges(cls, bridges: list[dict]) -> list["Bridge"]:
        return list(map(lambda a: cls(a), bridges))


class Bridges:
    def __init__(self, bridges: list[Bridge]):
        self.bridges = bridges

    # def get_channels(self) -> list[str]:
    #     flatmap = lambda f, xs: [y for ys in xs for y in f(ys)]
    #     return list(map(lambda b: b[1], flatmap(lambda a: a.channels, self.bridges)))

    def get_resident_bridge(self, message: Message) -> Bridge | None:

        for bridge in self.bridges:
            channels = list(map(lambda a: int(a[1]), bridge.channels))
            if message.channel.id in channels:
                return bridge
        return None

    def build_forwarded_message(self, m: Message) -> str:
        reply: str
        if m.reference is not None:
            # pass
            mr = m.reference.cached_message
            if mr is None:
                reply = "### ↪️ reply could not be loaded..."
            else:
                reply = f"### ↪️ {mr.author}\n> {mr.content}"
        else:
            reply = ""
        attachments: str = ""
        for a in m.attachments:
            attachments += f"{str(a)}\n"

        return f"{reply}\n## {m.author}\n{m.content}\n{attachments}"

    # looks into message details and sends an identical bot message to all other channels
    async def handle_bridges(self, client: commands.Bot, message: Message):
        if message.author.id == client.user.id:
            return

        bridge = self.get_resident_bridge(message)
        if bridge is not None:
            built_message = self.build_forwarded_message(message)
            for guild, channel in bridge.channels:
                if int(channel) != message.channel.id:
                    c = client.get_channel(int(channel))
                    await c.send(built_message)  # type: ignore
