from genericpath import exists
import json

import os
from config import Config
from dataclasses import dataclass,field
from datetime import datetime, timedelta
EPOCH = datetime(2025,5,14)

def datetime_to_epoch_day(day:datetime) -> int:
    diff = day - EPOCH
    return diff.days

# def datetime_to_epoch_day(datetime.now()) -> int:
#     return (datetime.now() - EPOCH).days

def epoch_to_unix(epoch_day:int) -> datetime:
    return EPOCH + timedelta(days=epoch_day)

# def get_epoch_offset_timestamp(offset_days:int) -> float :
#     dt = EPOCH + timedelta(days=offset_days)
#     return dt.timestamp()

@dataclass
class Day:
    MSG_HOURS = "msg_hours"
    EMOJI_HOURS="emoji_hours"
    DATE='date'
    date : float
    msg_hours : list[int] = field(default_factory=lambda: [0] * 24)
    emoji_hours : dict[str,list[int]] = field(default_factory=lambda: {})

    def to_dict(self) -> dict:
        return {self.MSG_HOURS:self.msg_hours,self.EMOJI_HOURS:self.emoji_hours,self.DATE:self.date}

    @classmethod
    def from_dict(cls,d:dict) -> "Day":
        try:
            return cls(date=d[cls.DATE],msg_hours=d[cls.MSG_HOURS],emoji_hours=d[cls.EMOJI_HOURS])
        except KeyError as e:
            raise Exception(f"invalid day missing key {e}")

    def total(self) -> int:
        return sum(self.msg_hours)

    def emoji_total_of(self,emoji:str) -> int:
        if emoji in self.emoji_hours.keys():
            return sum(self.emoji_hours[emoji])
        else:
            return 0
    def get_emoji(self,emoji:str) -> list[int]:
        e = self.emoji_hours.get(emoji)
        if e:
            return e
        else:
            self.emoji_hours[emoji] = [0] * 24
            return self.emoji_hours[emoji]

    def avg(self) -> float:
        return sum(self.msg_hours)/len(self.msg_hours)

    def emoji_avg_of(self,emoji:str) -> float:
        if emoji in self.emoji_hours.keys():
            return sum(self.emoji_hours[emoji])/len(self.emoji_hours[emoji])
        else:
            return 0.0

@dataclass
class User:
    ID = 'id'
    NAME = 'name'
    DAYS = 'days'
    id : int
    name : str
    days : dict[int,Day]

    @classmethod
    def from_dict(cls,d:dict) -> "User":

        days : dict[int,Day] = {}
        for absyd,day in d[cls.DAYS].items():
            days[int(absyd)] = Day.from_dict(day)

        return cls(id=d[cls.ID],name=d[cls.NAME],days=days)

    def to_dict(self) -> dict:
        days : dict[int,dict] = {}
        for day_n,day in self.days.items():
            # print(type(day_n))
            days[int(day_n)] = day.to_dict()
        return {self.ID:self.id,self.NAME:self.name,self.DAYS:days}

    def get_day(self,year:int,days_since_epoch:int) -> Day:
        day = self.days.get(days_since_epoch)
        if day:
           return day
        else:
            return Day(epoch_to_unix(days_since_epoch).timestamp())

    def update_message_count_at(self,hr:int,msgs:int):
        day_key = datetime_to_epoch_day(datetime.now())
        # hr = datetime.now().hour
        print(self.days)
        day = self.days.get(day_key)
        if day:
            day.msg_hours[hr]+=msgs
        else:
            self.days[day_key] = Day(datetime_to_epoch_day(datetime.now()))
            print("old_count: ",self.days[day_key].msg_hours[hr])
            self.days[day_key].msg_hours[hr]+=msgs

    def update_emoji_count_for_right_now_at(self,hr:int,emoji:str,count:int):
        day_key =datetime_to_epoch_day(datetime.now())
        # hr = datetime.now().hour
        print(self.days)
        day = self.days.get(day_key)
        if not day:
            self.days[day_key] = Day(datetime_to_epoch_day(datetime.now()))
            day = self.days[day_key]
        day.get_emoji(emoji)[hr]+=count

    def concat(self,other:"User",min:int|None=None,max:int|None=None):
        # print("other.days.items(): ",other.days.items())
        for (day,data) in other.days.items():
            # print("DOING")
            if min != None:
                if day < min:
                    # print("day<min")
                    continue
            if max != None:
                if day > max:
                    # print("day>max")
                    continue
            if day not in self.days:
                self.days[day] = data
            else:
                raise Exception(f"days overlapped somehow idk man day {day}")

    def sum(self) -> int:
        total = 0
        # print(self.days)
        for day in self.days.values():
            # print("LOOP")
            total+=day.total()
        print(f"total messages for {self.name} : {total}")
        return total

USERS = 'users'
META = 'meta'

class ServerFile:
    def __init__(self,inner_path:str,ro:bool=True):
        print("file path $database/$name/$name-$year.json: ",inner_path)
        self.path = inner_path
        self.users : dict[int,User] = {}
        self.meta : dict = {}
        self.read_only = ro
        if os.path.exists(inner_path):
            with open(inner_path,'r') as f:
                inner = json.loads(f.read())
            for user_id,user in inner[USERS].items():
                self.users[int(user_id)] = User.from_dict(user)
            self.meta = inner[META]
        elif not self.read_only:
            # its going to assume that its making the new file because its a new year, the current year.
            self.meta['year'] = datetime.now().year
            current_epoch_day = datetime_to_epoch_day(datetime.now())
            self.meta['first_day'] = current_epoch_day
            self.meta['last_day'] = current_epoch_day
        else:
            raise Exception(f"error retrieving server file: {inner_path} not found")

    def to_dict(self) -> dict:
        users = {}
        for (id,user) in self.users.items():
            users[id] = user.to_dict()
        return {USERS:users,META:self.meta}

    def flush(self):
        if not self.read_only:
            serialized = self.to_dict()
            os.makedirs(os.path.dirname(self.path),exist_ok=True)
            with open(self.path,'w') as f:
                json.dump(serialized,f,indent=2)
            print(f"flushed {self.path}")
        else:
            print(f"attempted to flush read only file {self.path}")

    def get_user(self,id:int,**kwargs) -> User|None:
        if id in self.users.keys():
            return self.users[id]
        elif not self.read_only:
            name = kwargs.get('name')
            if not name:
                print('could not default user as no name was provided')
                return None
            self.users[id] = User(id,name,{})
            return self.users[id]

    def update_last_day_to_now(self):
        self.meta['last_day'] = datetime_to_epoch_day(datetime.now())

def build_file_name(server_name,year:int) -> str:
    return f"{server_name}_{year}.json"

def build_file_path(server_name:str,year:int) -> str:
    return os.path.join(server_name,build_file_name(os.path.basename(server_name),year))

# wraps open files and retains context, allowing lazy loading
class ROServerFS:
    def __init__(self,directory:str):
        self.directory = directory
        self.server_name = os.path.basename(os.path.normpath(directory))
        self.files : dict[int,ServerFile] = {}

    def get_server(self,year:int) -> ServerFile:
        if year not in self.files.keys():
            self.files[year] = ServerFile(build_file_path(self.directory,year))
        return self.files[year]

class Server:
    def __init__(self,server_path:str):
        self.server_path = server_path
        print("server path: $database/$name: ",server_path)
        now = datetime.now()
        self.db = ServerFile(build_file_path(server_path,now.year),ro=False)

    def update_user_msg_count(self,id:int,name:str,hr:int,new_msgs:int):
        user = self.db.get_user(id,name=name)
        if user:
            user.update_message_count_at(hr,new_msgs)
        else:
            print(f"FAILED TO GET USER {name} AND UPDATE COUNT !!! ")
    def update_user_emoji_count(self,id:int,name:str,hr:int,emoji:str,new_emojis:int):
        user = self.db.get_user(id,name=name)
        if user:
            user.update_emoji_count_for_right_now_at(hr,emoji, new_emojis)
        else:
            print(f"FAILED TO GET USER {name} AND UPDATE emoji COUNT !!! ")

class BatchCache:
    def __init__(self,database_dir:str):
        self.fill:int=0
        self.path = os.path.join(database_dir,'batch_cache.json')
        if os.path.exists(self.path):
            with open(self.path,'r') as f:
                cache : dict[str,dict[str,float]]= json.load(f)
                self.servers : dict[int,dict[int,float]] = {}
                # convert all the stupid json str keys to int
                for server,channels in cache.items():
                    new_channel : dict[int,float]= {}
                    for channel,timestamp in channels.items():
                        new_channel[int(channel)] = timestamp
                    self.servers[int(server)] = new_channel
                # self.servers[server] = channel
        else:
            self.servers = {}
    def flush(self):
        with open(self.path,'w') as f:
            json.dump(self.servers,f)

    def log_pointer(self,server_id:int,channel_id:int,ptr:float):
        if server_id not in self.servers:
            self.servers[server_id] = {}
        if channel_id not in self.servers[server_id]:
            self.servers[server_id][channel_id] = ptr
            print(f"logging pointer sid:{server_id} cid:{channel_id}")
    def clear(self):
        self.servers = {}

if __name__ == "__main__":
    server = Server('test_server')
    # server.update_user_msg_count(0,"nimmy",10)
    # server.update_user_emoji_count(0, "nimmy", "munley", 20)
    server.db.flush()


# class Database:
#     def __init__(self,cfg:Config):
#         self.cfg = cfg
