from nextcord.message import Message
from analysis import Analyzer
from database import Server,BatchCache,build_file_path
from nextcord.ext import commands
import nextcord
from nextcord.abc import Messageable
import datetime
import os
from config import Config
class Scraper(commands.Bot):
    def __init__(self,cfg:Config):
        print("init")


        intents = nextcord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True
        super().__init__(intents=intents)


        self.cfg = cfg
        self.servers : dict[int,Server] = {}
        self.batch = BatchCache(cfg.database_directory)
        self.analysis = Analyzer(cfg)
    def flush_servers(self):
        for server in self.servers.values():
            server.db.flush()

    async def process_batch(self):
        self.batch.fill = 0
        for (server_id,channels)in self.batch.servers.items():
            db_server = self.servers.get(server_id)
            if not db_server:
                name = self.cfg.tracked_servers.get(str(server_id))
                if not name:
                    raise Exception("server not tracked")

                self.servers[server_id] = Server(os.path.join(self.cfg.database_directory,name))
                db_server = self.servers[server_id]
                print(f"{name}")
            db_server.db.update_last_day_to_now()

            for channel_id,unix_stamp in channels.items():
                channel = await self.fetch_channel(channel_id)
                if isinstance(channel,Messageable):
                    print(f"new messages in {channel.name}")

                    messages = channel.history(limit=None,after=datetime.datetime.fromtimestamp(unix_stamp))
                    i = 0
                    async for message in messages:
                        i += 1
                        user = message.author
                        print(f"{i}: {user.name}: {message.content}")
                        db_server.update_user_msg_count(user.id, user.name, message.created_at.hour, 1) # bit stupid i have to increment by one, could fix later by collecting all then storing, eh its python aint gonna be efficent
                        for reaction in message.reactions:
                            if isinstance(reaction.emoji,str):
                                emoji_name = reaction.emoji
                            else:
                                emoji_name = reaction.emoji.name
                            db_server.update_user_emoji_count(user.id, user.name, message.created_at.hour, emoji_name, reaction.count)

        print("batch processed")
        self.batch.servers.clear()
        self.flush_servers()

    async def on_ready(self):
        print("ready")

    async def on_disconnect(self):
        print("disconnected")
        self.batch.flush()
        self.flush_servers()

    async def on_message(self,message:Message):
        print(f"MESSAGE: {message.author.name}: {message.content}")
        if message.guild and not message.author.bot:
            self.batch.log_pointer(message.guild.id,message.channel.id,message.created_at.timestamp())
            self.batch.fill +=1
            if self.batch.fill > self.cfg.batch_size:
                print("processing batch")
                await self.process_batch()

        if message.content == f"{self.cfg.prefix}ping":
            await message.channel.send("pong!")
        elif message.content == f"{self.cfg.prefix}process":
            await self.process_batch()
            await message.channel.send("processed")
        elif message.content.startswith(f"{self.cfg.prefix}gen"):
            await self.analysis.generate_handler(message)
        elif message.content == f"{self.cfg.prefix}status":
            await message.channel.send(f"{self.batch.fill}/{self.cfg.batch_size}")
if __name__ == "__main__":
    cfg = Config()
    bot = Scraper(cfg)
    bot.run(cfg.token, reconnect=True)
