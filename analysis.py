import nextcord
from nextcord.message import Message
import database as db
from config import Config
import os,datetime,json
import matplotlib.pyplot as plt
import copy,random
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
                raise Exception("data for specified range does not exist")
            
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

    async def generate_handler(self,message:Message):
        try:
            msg,attachment = self.generate_message_pie_chart('louiscord',10,10)
            await message.channel.send(msg,file=nextcord.File(attachment))
        except Exception as e:
            await message.channel.send(f"Internal Error: {e}")


    def generate_message_pie_chart(self,server:str,start:int,end:int) -> tuple[str,str]:
        users = sorted(self.collect_data_from_x_to_y(server,start,end),key=lambda u: u.sum(),reverse=True)
        # print(users)
        labels = [u.name for u in users]
        values = [u.sum() for u in users]
        colors = [self.colors.file[str(m.id)] if str(m.id) in self.colors.file else f'#{hex(random.randint(0x333333,0xdddddd)).removeprefix('0x')}' for m in users]
        readout = "pie chart messages"
        suffix = "msgs"

        print(labels,values)
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
