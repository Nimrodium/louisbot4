from typing import Callable
import nextcord
from nextcord.guild import Guild
from nextcord.message import Message
import database as db
from config import Config
import os,datetime,json
import matplotlib.pyplot as plt
import copy,random
from dateutil import parser
class ColorConfig:
    def __init__(self,cfg:Config):
        self.cfg = cfg
        self.file_path = os.path.join(self.cfg.database_directory,'colors.json')
        self.file : dict[str,str] = json.load(open(self.file_path,'r'))

    def flush(self):
        with open(self.file_path,'w') as f:
            json.dump(self.file,f)

    def get_user_color(self,id:int) -> str|None:
        return self.file.get(str(id))

    def set_user_color(self,id:int,color:str):
        self.file[str(id)] = color
        self.flush()

    def get_color_list(self,users:list[db.User]):
        return [self.file[str(m.id)] if str(m.id) in self.file else f'#{hex(random.randint(0x333333,0xdddddd)).removeprefix('0x')}' for m in users]
class Analyzer:
    def __init__(self,cfg:Config):
        self.cfg = cfg
        self.colors = ColorConfig(cfg)



    # def get_start_file(self,fs:db.ROServerFS,):


    # in epoch days
    def collect_data_from_x_to_y(self,server:str,start:int,end:int) -> list[db.User]:
        # concatenate and truncate data from one or more file entries of a server
        #
        # get server, if first_day greater than start get last year, if last_day is less than end then enter into collected db stop once first_day is less than start

        users : dict[int,db.User] = {}

        fs = db.ROServerFS(os.path.join(self.cfg.database_directory,server))
        year = datetime.datetime.now().year

        while True:
            try:
                svr = fs.get_server(year)
            except:
                break
            if svr.meta["last_day"] < start or svr.meta["first_day"] > end:
                year -= 1
                continue
            for user_id,user in svr.users.items():
                # print(f"Collecting data on {user.name} during {year}, days: {user.days}")
                if user_id in users.keys():
                    users[user_id].concat(user,min=start,max=end)
                else:
                    users[user_id] = copy.deepcopy(user)
                    # print("users[user_id].days = ",users[user_id].days)
                    for day in list(users[user_id].days.keys()):
                        if day < start or day > end:
                            print(f"day {day} for {user.name} REJECTED {day} <= {start} or {day} >= {end}")
                            users[user_id].days.pop(day)
                        # else:
                        #     users[user_id].days[day] =
            if svr.meta['first_day'] <= start:
                break
            else:
                year -= 1
        return list(users.values())


    # def generate_generic_pie_chart(self):

    async def route_range(self,message:Message,cmd:list[str],fn:Callable):
        assert isinstance(message.guild,Guild)
        print(cmd)
        match cmd[0]:
            case "past":
                print(cmd[0])
                match cmd[2]:
                    case "days"|"day"|"d":
                        print(cmd[2])
                        if cmd[1].isdigit():
                            print(cmd[1])
                            start = db.datetime_to_epoch_day(datetime.datetime.now() - datetime.timedelta(days=int(cmd[1])))
                            end = db.datetime_to_epoch_day(datetime.datetime.now())
                            msg,attachment = fn(self.cfg.get_server_alias(message.guild.id),start,end)
                            await message.channel.send(msg,file=nextcord.File(attachment))
                        else:
                            await message.channel.send("not a number")
    def get_start_end(self,cmd:list[str]) -> tuple[int,int]:
        match cmd[0]:
            case "past"|"last":
                match cmd[2]:
                    case "day"|"days"|"d":
                        if cmd[1].isdigit():
                            start = db.datetime_to_epoch_day(datetime.datetime.now() - datetime.timedelta(days=int(cmd[1])))
                            end = db.datetime_to_epoch_day(datetime.datetime.now())
                            return (start,end)
                        else:
                            raise Exception("Value is not Digit")
            case "since":
                human_readable = " ".join(cmd[1:])
                start =  db.datetime_to_epoch_day(parser.parse(human_readable))
                end = db.datetime_to_epoch_day(datetime.datetime.now())
                return (start,end)
            case "from":
                start_human_readable_list = []
                for s in cmd[1:]:
                    if s == "to":
                        break
                    else:
                        start_human_readable_list.append(s)

                start = db.datetime_to_epoch_day(parser.parse(" ".join(start_human_readable_list)))
                end = db.datetime_to_epoch_day(parser.parse(" ".join(cmd[len(start_human_readable_list)+2:])))
                return (start,end)


        raise Exception("Command Syntax Invalid")

    async def generate_handler(self,message:Message):
        cmd = message.content.split()
        print(cmd)
        if message.guild == None:
            return await message.channel.send("Not in a server")
        server = self.cfg.get_server_alias(message.guild.id)
        try:
            match cmd[1]:
                case "pie":
                    match cmd[2]:
                        case "msgs":
                            # await self.route_range(message,cmd[3:],self.generate_message_pie_chart)
                            start,end = self.get_start_end(cmd[3:])
                            msg,attachment = self.generate_message_pie_chart(server,start,end)
                            await message.channel.send(msg,file=nextcord.File(attachment))
                        case "emoji":
                            start,end = self.get_start_end(cmd[4:])
                            msg,attachment = self.generate_emoji_pie_chart(server,cmd[3],start,end)
                            await message.channel.send(msg,file=nextcord.File(attachment))
                case "line":
                    match cmd[2]:
                        case "msgs":
                            pass
                            # await self.route_range(message,cmd[2:],self.generate_line_chart)
        except IndexError as e:
            await message.channel.send(f"Internal Error: Command Syntax Invalid ({e})")
        # except Exception as e:
        #     await message.channel.send(f"{e}")

        # msg,attachment = self.generate_message_pie_chart('louiscord',9,9)
        # await message.channel.send(msg,file=nextcord.File(attachment))



    def generate_message_pie_chart(self,server:str,start:int,end:int) -> tuple[str,str]:
        users = sorted(self.collect_data_from_x_to_y(server,start,end),key=lambda u: u.sum(),reverse=True)
        # print(users)
        labels = [u.name for u in users]
        values = [u.sum() for u in users]
        colors = self.colors.get_color_list(users)
        readout = "pie chart messages"
        suffix = "msgs"

        print(labels,values)
        return self.generic_pie_chart(readout,labels,values,colors,suffix)
    def generate_emoji_pie_chart(self,server:str,emoji:str,start:int,end:int) -> tuple[str,str]:
        users = sorted(self.collect_data_from_x_to_y(server,start,end),key=lambda u: u.sum_emoji(emoji),reverse=True)
        labels = [u.name for u in users]
        values = [u.sum_emoji(emoji) for u in users]
        colors = self.colors.get_color_list(users)
        readout = "pie chart emojis"
        suffix = f" {emoji}s"
        return self.generic_pie_chart(readout,labels,values,colors,suffix)

    def generic_pie_chart(self,readout:str,labels:list[str],values:list[int],colors:list[str],suffix:str) -> tuple[str,str]:
        all = sum(values)
        print("sum of all values: ",all)
        percents = [v/all*100 for v in values]
        print("percents: ",percents)
        CUTOFF_PERCENT : float = 2.0
        users_to_display = 0
        for user_percent in percents:
            if user_percent >= CUTOFF_PERCENT:
                users_to_display+=1
            else:
                break
        print('users to display: ',users_to_display)
        for n in range(users_to_display): # so no more redundant calls for total messages which could get expensive on albeit extremely large datasets
            readout += f"\t{labels[n]}: {values[n]}{suffix}\n"
        readout+='use `!setcolor #<hexcolor>` to set a custom color for your pie slice'
        figure,axes = plt.subplots()
        axes.pie(

            x=values[:users_to_display],
            labels=labels[:users_to_display],
            colors=colors[:users_to_display],
            shadow = True,
            radius = 1,
            labeldistance = 1.1,
            textprops={'size':'smaller'},
            autopct='%1.1f%%' # no clue what this is

        )
        path = os.path.join(os.environ['TEMP'] if os.name == 'nt' else '/tmp','louisbot4_pieplot.png')
        figure.savefig(path)
        print(f"{readout}\nplot saved at `{path}`")
        return (readout,path)
