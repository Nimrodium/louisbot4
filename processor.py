import os,json
from numpy import random
from config import Config
import datetime
from math import ceil
from datastructures import Server,MemberData
import matplotlib.colors as mpl_colors
import matplotlib.pyplot as plt

KEY_SCRAPER_DATA = 'data'
# class MemberStat:
#     def __init__(self,name:str,id:int,reactions:dict,color:int):
#         self.name = name
#         self.id = id
#         self.color = color

def make_file_name(year:int,month:int,week:int) -> str:
    return f"{year}y-{month}m-{week}w.json"


def week_of_month(dt:datetime.datetime): #https://stackoverflow.com/questions/3806473/how-do-i-get-the-week-number-of-the-month
    #Returns the week of the month for the specified date.
    first_day = dt.replace(day=1)
    dom = dt.day
    adjusted_dom = dom + first_day.weekday()
    return int(ceil(adjusted_dom/7.0))


def files_for_range(parent:str,weeks_from_now:int) -> list[str]:
    now : datetime.datetime = datetime.datetime.now()
    now_date = now.date()

    files : list[str] = []

    for n in range(weeks_from_now):
        entry = now - datetime.timedelta(weeks=n)
        name = os.path.join(parent,make_file_name(entry.year,entry.month,week_of_month(entry)))
        files.append(name)

    print(f"files from past {weeks_from_now} weeks\n{files}")
    return files

# def hex_to_rgba(hex:int) -> tuple[int...]:
#     lv = len(hex)
#     return tuple(int(hex[i:i + lv // 3], 16) / 255 for i in range(0, lv, lv // 3))


class StatBuilder:
    def __init__(self,cfg:Config):
        self.cfg = cfg
        self.colors_file = os.path.join(self.cfg.database_directory,'colors.json')
        with open(self.colors_file,'r') as f:
            self.user_colors : dict = json.load(f)


    def collect_data(self,server_id:int,files:list[str]) -> list[MemberData]:
        # members : list[MemberStat] = []
        members : dict[int,MemberData] = {}
        for file in files:
            with open(file,'r') as f:
                parsed = json.load(f)
                try:
                    if str(server_id) not in parsed[KEY_SCRAPER_DATA]: #Scraper.KEY_DATA
                        continue
                    server : Server = Server(parsed[KEY_SCRAPER_DATA][str(server_id)])
                    # member_logs = server.members()
                    for (id,member_log) in server.members().items():
                        if id in members.keys():
                            members[id].merge(member_log)
                        else:
                            members[id] = MemberData(member_log)

                except KeyError as e:
                    raise Exception(f"malformed json missing key `{e}`")
        return list(members.values())

    # def process(self,cmd:list[str]) -> tuple[str,str]: # (msg,file_path)
    #     pass

    def pie_chart_stat(self,server_id:int,past_n_weeks:int) -> tuple[str,str]:
        files = files_for_range(self.cfg.database_data, past_n_weeks)
        data = self.collect_data(server_id,files)
        readout = f"total messages from past {past_n_weeks} weeks:\n"
        # making multiple sum calls but eh... its python we arent aiming for efficieny here -- NOT ANYMORE
        sorted_data =  sorted(data,key=lambda m: m.total_messages(),reverse=True)
        all_messages = sum(m.total_messages() for m in sorted_data)


        labels = [m.name for m in sorted_data]
        values = [m.total_messages() for m in sorted_data]
        percents = [v/all_messages*100 for v in values]

        # DEFAULT_COLOR = 0xFF00FF
        users_to_display = 0
        for user_percent in percents:
            if user_percent >= 2.0:
                users_to_display+=1
            else:
                break
        print(f"users displayed {users_to_display}")
        colors : list[str] = [self.user_colors[str(m.id)] if str(m.id) in self.user_colors else f'#{hex(random.randint(0x333333,0xdddddd)).removeprefix('0x')}' for m in sorted_data]
        for n in range(len(sorted_data)): # so no more redundant calls for total messages which could get expensive on albeit extremely large datasets
            readout += f"\t{labels[n]}: {values[n]}msgs\n"
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

    def message_stats(self,range:int,server:int) -> tuple[str,str]: # (message,attachment path)
        return (f"this is a placeholder for stats command with range {range} weeks and serverid {server}","./db/sheepy.gif")

    def set_user_color(self,id:int,color:str) -> bool:
        try:
            n = int(color.removeprefix('#'),16) # check if valid
        except:
            return False
        self.user_colors.update({str(id):color})
        self.flush_colors()
        return True

    def get_user_color(self,id) -> str|None:
        self.user_colors.get(str(id))

    def flush_colors(self):
        with open(self.colors_file,'w') as f:
            print("flushed colors cfg to disk")
            f.write(json.dumps(self.user_colors,indent=2))
