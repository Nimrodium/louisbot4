from typing import Callable
import nextcord
import string,itertools
from nextcord.ext import commands
from nextcord.guild import Guild
from nextcord.member import Member
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
            smallest = 1000000000000000000 # huge fucking sentinel change
            for user_id,user in svr.users.items():
                # print(f"Collecting data on {user.name} during {year}, days: {user.days}")
                if user_id in users.keys():
                    users[user_id].concat(user,min=start,max=end)
                else:
                    users[user_id] = copy.deepcopy(user)
                    # print("users[user_id].days = ",users[user_id].days)
                    for day in list(users[user_id].days.keys()):
                        if day < start or day > end:
                            # print(f"day {day} for {user.name} rejected as {f"day is less than start ({start})" if day < start else f"day greater than end ({end})"}")
                            if day < smallest:
                                smallest = day
                            users[user_id].days.pop(day)
                        # else:
                        #     users[user_id].days[day] =
            if svr.meta['first_day'] <= start:
                break
            else:
                year -= 1
        print(f"smallest day {smallest}")
        return list(users.values())

    def get_start_end(self,cmd:list[str]) -> tuple[int,int]:
        print(f"time select : {cmd}")
        match cmd[0]:
            case "past"|"last"|'p'|'l':
                match cmd[2]:
                    case "day"|"days"|"d":
                        if cmd[1].isdigit():
                            start = db.datetime_to_epoch_day(datetime.datetime.now() - datetime.timedelta(days=int(cmd[1])))
                            end = db.datetime_to_epoch_day(datetime.datetime.now())
                            return (start,end)
                        else:
                            raise Exception("Value is not Digit")
            case "since"|'s':
                human_readable = " ".join(cmd[1:])
                start =  db.datetime_to_epoch_day(parser.parse(human_readable))
                end = db.datetime_to_epoch_day(datetime.datetime.now())
                return (start,end)
            case "from"|'f':
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

    async def generate_handler(self,ctx:commands.Bot,message:Message):
        cmd = message.content.split()
        print(cmd)
        if message.guild == None:
            return await message.channel.send("Not in a server")
        server = self.cfg.get_server_alias(message.guild.id)
        # try:
        match cmd[1]:
            case "pie"|'p':
                match cmd[2]:
                    case "msgs"|'m':
                        # await self.route_range(message,cmd[3:],self.generate_message_pie_chart)
                        start,end = self.get_start_end(cmd[3:])
                        msg,attachment = self.generate_message_pie_chart(server,start,end)
                        await message.channel.send(msg,file=nextcord.File(attachment))
                    case "emoji"|'e':
                        start,end = self.get_start_end(cmd[4:])
                        msg,attachment = self.generate_emoji_pie_chart(server,cmd[3],start,end)
                        await message.channel.send(msg,file=nextcord.File(attachment))
            case "line"|'l':
                print("line")
                user : Member|None = None
                data_select = cmd[2]
                granularity = cmd[3]
                match cmd[4]:
                    case 'total'|'t':
                        start,end = self.get_start_end(cmd[5:])

                    case 'all'|'a':
                        start,end = self.get_start_end(cmd[5:])
                        users = message.guild.humans
                        match cmd[2]:
                            case "messages"|'msgs'|'m':
                                msg,attachment = self.generate_line_message_chart(server,users,start,end,granularity)
                                await message.channel.send(msg,file=nextcord.File(attachment))
                            #case "emojis"|"emoji"|"e":
                                #msg,attachment = self.generate_line_emoji_chart(server,users,start,end)
                            case _:
                                await message.channel.send(f"{cmd[2]} not valid")
                    # case 'user'|'u':

                    #     for member in message.guild.humans:
                    #         if member.name == cmd[4]:
                    #             user = member
                    #             break
                    #     start,end = self.get_start_end(cmd[5:])
                    case 'users'|'user'|'u':
                        raw_users : list[str] = []

                        users : list[Member] = []
                        for word in cmd[5:]:
                            # check if valid name to avoid searching entire server and early catch user error
                            if len(word) > 32:
                                await message.channel.send(f"{word} is an invalid username (too long {len(word)}>32)")
                                return
                            if word == ';':
                                break
                            else:
                                for c in word:
                                    if c not in string.ascii_lowercase and c not in string.digits and c not in ['_','.']:
                                        await message.channel.send(f"{word} is an invalid username (invalid character {c})")
                                        return
                                raw_users.append(word)
                        print(raw_users)

                        for member in message.guild.humans:
                            if member.name in raw_users:
                                users.append(member)
                        print(cmd)
                        start,end = self.get_start_end(cmd[5+len(raw_users)+1:])
                        match cmd[2].split(':')[0]:
                            case "messages"|'msgs'|'m':
                                msg,attachment = self.generate_line_message_chart(server,users,start,end,granularity)
                                await message.channel.send(msg,file=nextcord.File(attachment))
                            case "emojis"|"emoji"|"e":
                                emoji = cmd[2].split(':')[1]
                                msg,attachment = self.generate_line_emoji_chart(server,users,start,end,granularity,emoji)
                                await message.channel.send(msg,file=nextcord.File(attachment))

                            case _:
                                await message.channel.send(f"{cmd[2]} not valid")
                    case _:
                        print(f"invalid user select {cmd[4]}")
                # match cmd[2]:
                #     case "msgs"|'m':
                #         pass
                #         await self.route_range(message,cmd[2:],self.generate_line_chart)
    # except IndexError as e:
    #     await message.channel.send(f"Internal Error: Command Syntax Invalid ({e})")
    # except Exception as e:
    #     await message.channel.send(f"{e}")

        # msg,attachment = self.generate_message_pie_chart('louiscord',9,9)
        # await message.channel.send(msg,file=nextcord.File(attachment))

    def generate_line_message_chart(self,server:str,users:list[db.User],start:int,end:int,granularity:str) -> tuple[str,str|None]:
        # names = [m.name for m in members]

        # ids = [m.id for m in members]
        # all_users = self.collect_data_from_x_to_y(server,start,end)
        # users: list[db.User] = []
        # for user in all_users:
        #     if user.id in ids:
        #         # print(f"comparing {user.id} with {ids}")
        #         users.append(user)
        users = sorted(users,key=lambda u: u.sum(),reverse=True)
        names = [u.name for u in users]
        #
        # print(f"users: {users}")
        #
        print(f"db user: {names}")
        match granularity:
            case 'hours'|'hr':
                # list of users hours flattened, using length of flattened list, display ig is all of day logic + :hr
                users_y : list[list[int]] = [] # list[list[hour]]
                for user_i,user in enumerate(users):
                    print(f"collecting y for {user.name}")
                    users_y.append(user.get_day(start).msg_hours)
                    for day_i in range(start+1,end+1):
                        users_y[user_i].extend(user.get_day(day_i).msg_hours)
                users_x : list[int] = list(range(len(users_y[0])))

                return self.generate_line_chart(f"Mesasges over Hours from {db.epoch_to_unix(start).strftime("%m/%d/%Y")} to {db.epoch_to_unix(end).strftime("%m/%d/%Y")}","" ,"Hours","Messages",names,users_x,users_y)
            case 'days'|'d':
                users_y : list[list[int]] = [] # list[list][day]
                for user_i,user in enumerate(users):
                    print(f"collecting y for {user.name}")
                    users_y.append([user.get_day(start).total()])
                    for day in range(start+1,end+1):
                        users_y[user_i].append(user.get_day(day).total())
                users_x : list[int] = list(range(len(users_y[0])))
                return self.generate_line_chart(f"Mesasges over Days from {db.epoch_to_unix(start).strftime("%m/%d/%Y")} to {db.epoch_to_unix(end).strftime("%m/%d/%Y")}","" ,"Days","Messages",names,users_x,users_y)
                # list of users day sum flattened, using start and end display converted to datetime and then to compact date format
            case _:
                raise Exception(f"invalid granularity {granularity}")


    def generate_line_emoji_chart(self,server:str,users:list[db.User],start:int,end:int,granularity,emoji:str) -> tuple[str,str|None]:
        # names = [m.name for m in members]

        # ids = [m.id for m in members]
        # users = 
        # users: list[db.User] = []
        # for user in all_users:
        #     if user.id in ids:
        #         # print(f"comparing {user.id} with {ids}")
        #         users.append(user)
        users = sorted(self.collect_data_from_x_to_y(server,start,end),key=lambda u: u.sum(),reverse=True)
        
        names = [u.name for u in users]
        #
        # print(f"users: {users}")
        #
        print(f"db user: {names}")
        match granularity:
            case 'hours'|'hour'|'hr':
                # list of users hours flattened, using length of flattened list, display ig is all of day logic + :hr
                users_y : list[list[int]] = [] # list[list[hour]]
                for user_i,user in enumerate(users):
                    print(f"collecting y for {user.name}")
                    users_y.append(user.get_day(start).get_emoji(emoji))
                    for day_i in range(start+1,end+1):
                        users_y[user_i].extend(user.get_day(day_i).msg_hours)
                users_x : list[int] = list(range(len(users_y[0])))

                return self.generate_line_chart(f"Mesasges over Hours from {db.epoch_to_unix(start).strftime("%m/%d/%Y")} to {db.epoch_to_unix(end).strftime("%m/%d/%Y")}","" ,"Hours",f"{emoji}s",names,users_x,users_y)
            case 'days'|'d':
                users_y : list[list[int]] = [] # list[list][day]
                for user_i,user in enumerate(users):
                    print(f"collecting y for {user.name}")
                    users_y.append([sum(user.get_day(start).get_emoji(emoji))])
                    for day in range(start+1,end+1):
                        users_y[user_i].append(user.get_day(day).total())
                users_x : list[int] = list(range(len(users_y[0])))
                return self.generate_line_chart(f"Mesasges over Days from {db.epoch_to_unix(start).strftime("%m/%d/%Y")} to {db.epoch_to_unix(end).strftime("%m/%d/%Y")}","" ,"Days",f"{emoji}s",names,users_x,users_y)
                # list of users day sum flattened, using start and end display converted to datetime and then to compact date format
            case _:
                raise Exception(f"invalid granularity {granularity}")

    def generate_line_chart(self,title:str,readout:str,xlabel:str,ylabel:str,line_labels:list[str],x:list[int],y:list[list[int]]) -> tuple[str,str|None]:
        fig,ax = plt.subplots()
        print(f"generating line chart {title} x: {xlabel} y:{ylabel} lbls:{line_labels}")
        print(f"x: {x} \n\nys: {y}")
        for i in range(len(y)):
            ax.plot(x,y[i],label=line_labels[i])
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)

        ax.legend()
        path = get_fig_path()
        fig.savefig(path)
        print(f"generated line chart at {path}")
        return readout,path
    def get_users_list(self,all_users:list[db.User],included_users:list[db.User]) -> list[db.User]:
        return [u for u in all_users if u.name in map(lambda u: u.name,included_users)]

    def generate_message_pie_chart(self,server:str,users:list[db.User],start:int,end:int) -> tuple[str,str|None]:
        all_users = sorted(self.collect_data_from_x_to_y(server,start,end),key=lambda u: u.sum(),reverse=True)
        users = self.get_users_list(all_users,users)
        print(f"users included: {list(map(lambda u: u.name,users))}")
        labels = [u.name for u in users]
        values = [u.sum() for u in users]
        colors = self.colors.get_color_list(users)
        readout = "pie chart messages"
        suffix = "msgs"

        print(labels,values)
        return self.generic_pie_chart(readout,labels,values,colors,suffix)
    def generate_emoji_pie_chart(self,server:str,emoji:str,users:list[db.User],start:int,end:int) -> tuple[str,str|None]:
        all_users = sorted(self.collect_data_from_x_to_y(server,start,end),key=lambda u: u.sum_emoji(emoji),reverse=True)
        users = self.get_users_list(all_users,users)
        labels = [u.name for u in users]
        values = [u.sum_emoji(emoji) for u in users]
        colors = self.colors.get_color_list(users)
        readout = "pie chart emojis"
        suffix = f" {emoji}s"
        return self.generic_pie_chart(readout,labels,values,colors,suffix)

    def generic_pie_chart(self,readout:str,labels:list[str],values:list[int],colors:list[str],suffix:str) -> tuple[str,str|None]:
        print(f"labels: {labels}")
        all_values = sum(values)
        print("sum of all values: ",all_values)
        if all_values == 0:
            return ("Empty graph",None)
        percents = [v/all_values*100 for v in values]
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
        path = get_fig_path()
        figure.savefig(path)
        print(f"{readout}\nplot saved at `{path}`")
        return (readout,path)


def get_fig_path() -> str:
    return os.path.join(os.environ['TEMP'] if os.name == 'nt' else '/tmp','.louisbot_plot.png')
