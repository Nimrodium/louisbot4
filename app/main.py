from nextcord.message import Message
from analysis import Analyzer
from database import Server,BatchCache,DB
from nextcord.ext import commands
import nextcord
from nextcord.abc import Messageable
import datetime
import os
import psutil
from config import Config

db_lock_file = "db.lock"

# returns True for safe to delete and proceed, False for lock file is valid
def can_delete_lock(lock:str) -> bool:
    with open(lock) as f:
        raw = f.read()
        pid : int
        if raw.isdigit():
            pid = int(raw)
        else:
            raise Exception(f"could not read database lock file: {lock} contained a non-integer PID")
        if os.getpid() == pid:
            print("lock file was spawned by this process")
            return True
        elif not psutil.pid_exists(pid):
            print(f"lock file {lock} found but the owner process has since died, safe to proceed")
            return True
        else:
            print(f"lock file {lock} exists and is not stale, process {pid} is still running!\nCannot run two instances of louisbot on the same database!!")
            return False

def lock_db(db_dir:str) -> None:
    lock = os.path.join(db_dir,db_lock_file)
    # check if lock.db already exists and if the lock is valid, gets rid of lock.db or leaves
    if os.path.exists(lock):
        if can_delete_lock(lock):
            print(f"deleting stale lock file: {lock}")
            delete_lock(lock)
        else:
           exit(1)
    with open(lock,"w") as f:
        self_pid = os.getpid()
        print(f"writing lock file: {lock} with pid {self_pid}")
        f.write(str(self_pid))

def delete_lock(lock:str):
    os.remove(lock)

class Scraper(commands.Bot):
    def __init__(self,cfg:Config):
        print("init")


        intents = nextcord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True
        super().__init__(intents=intents)


        self.cfg = cfg
        self.servers : DB = {}
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
        print("flushing batch to database")
        self.batch.flush()
        self.flush_servers()
        print("unlocking database")
        delete_lock(os.path.join(self.cfg.database_directory,db_lock_file))
        print("bye!")

    async def message_handler(self,message:Message):
        if message.content == f"{self.cfg.prefix}ping":
            await message.channel.send("pong!")
        elif message.content == f"{self.cfg.prefix}process":
            await self.process_batch()
            await message.channel.send("processed")
        elif message.content.startswith(f"{self.cfg.prefix}gen"):
            await self.analysis.generate_handler(self,message)
        elif message.content == f"{self.cfg.prefix}status":
            await message.channel.send(f"{self.batch.fill}/{self.cfg.batch_size}")

    async def on_message(self,message:Message):
        print(f"MESSAGE: {message.author.name}: {message.content}")
        if message.guild and not message.author.bot:
            self.batch.log_pointer(message.guild.id,message.channel.id,message.created_at.timestamp())
            self.batch.fill +=1
            if self.batch.fill > self.cfg.batch_size:
                print("processing batch")
                await self.process_batch()

        if message.content.startswith(self.cfg.prefix):
            await self.message_handler(message)



if __name__ == "__main__":
    cfg = Config()
    bot = Scraper(cfg)
    lock_db(cfg.database_directory)
    bot.run(cfg.token, reconnect=True)
