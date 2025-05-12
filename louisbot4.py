import asyncio
import datetime
import signal
from itertools import filterfalse
import json
import os
import nextcord
from nextcord.abc import Messageable
from nextcord.ext import commands
from nextcord.file import File
from nextcord.message import Message
from nextcord.types.channel import GuildChannel, TextChannel
from math import ceil
import time
import threading
from config import Config
from processor import StatBuilder, make_file_name,week_of_month
from datastructures import Server,MemberLog


def get_file_name(stamp:datetime.datetime) -> str:
    date = stamp.date()
    return make_file_name(date.year,date.month,week_of_month(stamp))
    return f"{date.year}y-{date.month}m-{week_of_month(stamp)}w.json"

async def send_message_maybe_attachment(channel,msg:str,attachment:str) -> None: # channel is MessageableChannel python is being stupid though and i cant import it
    if os.path.exists(attachment):
        await channel.send(msg,file=nextcord.File(attachment))
    else:
        await channel.send(msg)
    return

class Scraper(commands.Bot):
    KEY_DATA="data"
    KEY_BATCH="batch"
    KEY_COUNTER="counter"
    def __init__(self,cfg:Config):
        # self.first_message_toggle=True
        self.cfg = cfg
        self.statistics = StatBuilder(cfg)

        self.data: dict[int,Server] = {}
        # counter until processing is done again
        self.batch_size = cfg.batch_size
        self.counter = 0
        self.batch : dict[int,dict[int,float]] = {} # dict[guild_id:[channel_id:message_id]]

        intents = nextcord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True
        super().__init__(intents=intents)
        self.loop.create_task(self.auto_save_coroutine())

    async def auto_save_coroutine(self):
        await self.wait_until_ready()
        interval_seconds = self.cfg.dump_interval_minutes*60
        while not self.is_closed():
            print("autosaving")
            # await self.process_batch()
            self.dump_to_file()
            await asyncio.sleep(interval_seconds)

    def get_save_file(self) -> str:
        if os.path.exists(self.cfg.time_stamp_file):
            with open(self.cfg.time_stamp_file,'r') as f:
                unix_raw = float(f.read())
                timestamp : datetime.datetime = datetime.datetime.fromtimestamp(unix_raw)
                now = datetime.datetime.now()
                delta = now - timestamp
                if delta.days < 7:
                    # new
                    return os.path.join(self.cfg.database_data,get_file_name(now))
                else:
                    # old
                    return os.path.join(self.cfg.database_data,get_file_name(timestamp))
        else:
            print("timestamp file missing, assuming first run")
            with open(self.cfg.time_stamp_file,"x") as f:
                timestamp = datetime.datetime.now()
                f.write(str(timestamp.timestamp()))
                return os.path.join(self.cfg.database_data,get_file_name(timestamp))

    def load_batch(self,json:dict) -> None:
        batch : dict[int,dict[int,float]] = {} # dict[guild_id:[channel_id:message_id]]
        for (gid,entry) in json.items():
            new : dict[int,float] = {}
            for (cid,timestamp) in entry.items():
                new.update({int(cid):float(timestamp)})
            batch.update({int(gid):new})
        self.batch = batch
        return None

    def load_file(self,json:dict) -> None:
        try:
            data = json[self.KEY_DATA]
            new_data : dict[int,Server] = {}
            for (server_id,server_raw) in data.items():
                assert isinstance(server_id,str)
                new_data.update({int(server_id):Server(server_raw)})

            self.load_batch(json[self.KEY_BATCH])
            self.counter = int(json[self.KEY_COUNTER])
            # print(type(self.counter),self.counter)
            # assert isinstance(self.counter,int)
        except KeyError as e:
            print(f"malformed json missing key `{e}`")
            exit()
        self.data = new_data


    def dump_to_file(self):
        jsonned = json.dumps({self.KEY_DATA:self.data,self.KEY_BATCH:self.batch,self.KEY_COUNTER:self.counter},indent=2)
        with open(self.get_save_file(),"w") as f:
            f.write(jsonned)
            print("wrote to file")

    async def on_ready(self):
        print("connected")

    def get_server(self,id:int) -> Server:

        if id in self.data.keys():
            return self.data[id]
        else:
            if str(id) in self.cfg.server_names.keys():
                print(self.cfg.server_names)
                std_name = self.cfg.server_names[str(id)]
            else:
                std_name = "unknown"

            self.data.update({id:Server.new(id,std_name)})
            return self.data[id]

    async def process_batch(self):
        self.counter = 0
        if self.batch:
            print("processing batch")
        else:
            return

        for (guild_id,channels) in self.batch.items():
            # print(self.data)
            server = self.get_server(guild_id)
            for (channel_id,unix_stamp) in channels.items():
                channel = await self.fetch_channel(channel_id)
                if isinstance(channel,Messageable):
                    print(f"new messages in `{channel.name}`")
                    # msg_ptr = await channel.fetch_message(message_ptr_id)
                    messages = channel.history(limit=None,after=datetime.datetime.fromtimestamp(unix_stamp))
                    async for message in messages:
                        # message in scope

                        author = await server.get_member(self,message.author.id)
                        print(f"name: {author.name()}")
                        author.add_to_count(1)

                        for reaction in message.reactions:
                            if isinstance(reaction.emoji,str):
                                emoji_name = reaction.emoji

                            else:
                                emoji_name = reaction.emoji.name
                            for _ in range(reaction.count):
                                author.inc_emoji(emoji_name)
        self.batch = {}
    def log_pointer(self,message:Message):
        if message.guild:
            if message.guild.id not in self.batch.keys():
                self.batch.update({message.guild.id:{}})
            if message.channel.id not in self.batch[message.guild.id]:
                ptr = {message.channel.id:message.created_at.timestamp()}
                print(f"log pointer {ptr}")
                self.batch[message.guild.id].update(ptr) # log message
            else:
                pass # print(f"message by {message.author.name} in channel {message.channel.name} already has a pointer : `{message.content}`")
        else:
            print(f"message by {message.author.name} had no associated server: `{message.content}`")

    async def on_message(self,message:Message):
        if not message.author.bot:
            if self.counter == self.batch_size:
                # print(f"processing batch:  {self.batch}")
                # self.counter = 0
                await self.process_batch()
                # self.batch = {}
                self.dump_to_file()

            else:
                # print("ignoring message")
                self.log_pointer(message)
                self.counter+=1
                print(f"bc:{self.counter}")

            if message.content.startswith(self.cfg.prefix):
                await self.handle_cmd(message)
        else:
            print("bot user")


    async def handle_cmd(self,message:Message):
        cmd = message.content.removeprefix(self.cfg.prefix).strip().split()
        match cmd[0]:
            case 'ping':
                await message.channel.send("pong!")
            case 'sheepy':
                await message.channel.send(file=nextcord.File(os.path.join(self.cfg.database_directory,'sheepy.gif')))
            case 'louis':
                await message.channel.send("louis")
            case 'spoink':
                await message.channel.send("spoink")
            case 'flush':
                self.dump_to_file()
                await message.channel.send(f"state flushed to file `{self.get_save_file()}`")
            case 'process':
                await self.process_batch()
                self.dump_to_file()
                await message.channel.send(f"current batch manually triggered for processing")
            case 'status':
                await message.channel.send(f"filling batch {self.counter}/{self.batch_size} messages\nworking file: `{self.get_save_file()}`")
            case 'pie':
                if not message.guild:
                    await message.channel.send("this place is not associated with a server")
                    return
                #pie <m|e:str> </e/:name:str> <range:int=1>

                if not len(cmd)>1:
                    mode = 'm'
                    weeks = 1
                    msg,attachment = self.statistics.message_pie(message.guild.id,weeks)
                    await send_message_maybe_attachment(message.channel,msg,attachment)
                else:
                    # if cmd[1] not in ('m','e'):
                        # await message.channel.send(f"invalid pie mode `{cmd[1]}`")
                        # return
                    mode = cmd[1]
                    match mode:
                        case 'm':
                            if not len(cmd)>2:
                                weeks = 1
                            else:
                                if not cmd[2].isdigit():
                                    await message.channel.send(f"{self.cfg.prefix}`pie >>{cmd[2]}<<` not digit")
                                    return
                                weeks = int(cmd[2])

                            msg,attachment = self.statistics.message_pie(message.guild.id,weeks)
                            await send_message_maybe_attachment(message.channel,msg,attachment)
                        case 'e':
                            if not len(cmd)>2:
                                await message.channel.send(f"{self.cfg.prefix}`pie e >>_<<` missing emoji")
                                return
                            else:
                                emoji = cmd[2].removeprefix('<:').removesuffix('>').rsplit(':',1)[0] # cleans <:emojiname:0123456789> to emojiname
                            if not len(cmd)>3:
                                weeks = 1
                            else:
                                if not cmd[3].isdigit():
                                    await message.channel.send(f"{self.cfg.prefix}`pie >>{cmd[3]}<<` not digit")
                                    return
                                weeks = int(cmd[3])
                            msg,attachment = self.statistics.emoji_pie(message.guild.id,weeks,emoji)
                            await send_message_maybe_attachment(message.channel,msg,attachment)

                        case _:
                            await message.channel.send(f"invalid pie mode `{cmd[1]}`")
                            return

            #     if len(cmd)>1:
            #         if cmd[1].isdigit():
            #             weeks = int(cmd[1])
            #         else:
            #             await message.channel.send(f"{self.cfg.prefix}pie >>{cmd[1]}<< not digit")
            #             return
            #     else:
            #         weeks = 1


            #     if not message.guild:
            #         await message.channel.send("this place is not associated with a server")
            #         return
            #     msg,attachment = self.statistics.message_pie(message.guild.id,weeks)
            #     await message.channel.send(msg.replace('_', r'\_'),file=nextcord.File(attachment))


            case 'getcolor':
                if len(cmd)>1:
                   print(f"cmd[1]:: {cmd[1]}")
                   uid = message.author.id
                else:
                    uid = message.author.id
                color = self.statistics.get_user_color(uid)

                if color:
                    await message.channel.send(f"your color is {color}")
                else:
                    await message.channel.send(f"no color configured, use {self.cfg.prefix}setcolor with hex formatting to set a color to be used in statistics")
            case 'setcolor':
                if len(cmd)>1:
                    if self.statistics.set_user_color(message.author.id,cmd[1]):
                        await message.channel.send(f'set color to {cmd[1]}')
                    else:
                        await message.channel.send(f'color rejected {cmd[1]}')
                else:
                    await message.channel.send('missing color field')

                # self.statistics.update_user_color(uid,)
        # if trimmed.startswith('stat'):
        #     self.stat_builder.process(trimmed.split())
            # args = trimmed.removeprefix('run').strip().split()
            # if not args[0].isdigit():
            #     await message.channel.send(f"{self.cfg.prefix}run >{args[0]}<... must be digit")
            # else:
            #     range_raw = int(args[0])
            #     match args[1]:
            #         case 'weeks':
            #             weeks = range_raw
            #         case 'months':
            #             weeks = range_raw*4
            #         case 'years':
            #             weeks = range_raw*52
            #         case _:
            #             weeks = range_raw
            #     if message.guild:
            #         msg,attachment = self.stat_builder.message_stats(weeks,message.guild.id)
            #         await message.channel.send(msg,file=nextcord.File(attachment))
            #     else:
            #         await message.channel.send("this place is not associated with a serve")
    async def on_disconnect(self):
        self.dump_to_file()

    def cleanup(self):
        print("cleanup...")
        self.dump_to_file()






cfg = Config()
scraper = Scraper(cfg)
path = scraper.get_save_file()
print(path)
if os.path.exists(path):
    with open(path,'r') as f :
        print(f"initializing with file `{path}`")
        scraper.load_file(json.load(f))

signal.signal(signal.SIGTERM,lambda _,__: scraper.cleanup())

# timer_dump_thread = threading.Thread(target=scraper.dump_to_file(),)

# timer_dump_thread.run()

try:
    scraper.run(cfg.token,reconnect=True)
except KeyboardInterrupt:
    scraper.cleanup()
    exit()
