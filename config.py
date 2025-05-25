import json,os
CONFIG="./lb4_config.json"
class Config:
    KEY_BATCH_SIZE="batch_size"
    KEY_TOKEN="token"
    # KEY_COMMIT_INTERVAL="commit_interval_minutes"
    # KEY_RANGE_DAYS="range_days"
    KEY_DUMP_INTERVAL_MINUTES="dump_interval_minutes"
    KEY_DB_ROOT="database"
    KEY_PREFIX="prefix"
    KEY_SERVER_NAMES="server_names"
    KEY_TRACKED_SERVERS = "tracked_servers"
    def __init__(self):
        if os.path.exists(CONFIG):
            with open(CONFIG,'r') as f:
                cfg = json.load(f)
                try:
                    self.batch_size : int = cfg[self.KEY_BATCH_SIZE]
                    self.token : str = cfg[self.KEY_TOKEN]
                    # self.commit_inverval : int = cfg[self.KEY_COMMIT_INTERVAL]
                    # self.range_days : int = cfg[self.KEY_RANGE_DAYS]
                    self.database_directory : str = cfg[self.KEY_DB_ROOT]
                    self.prefix : str = cfg[self.KEY_PREFIX]
                    # self.server_names : dict[str,str] = cfg[self.KEY_SERVER_NAMES]
                    self.dump_interval_minutes : int = int(cfg[self.KEY_DUMP_INTERVAL_MINUTES])
                    self.tracked_servers : dict[str,str] = cfg[self.KEY_TRACKED_SERVERS]
                    # print(self.server_names)
                except KeyError as e:
                    print(f"missing key `{e}`")
                    exit()
                self.time_stamp_file = os.path.join(self.database_directory,'timestamp')
                self.database_data = os.path.join(self.database_directory,'data')
                os.makedirs(self.database_data,exist_ok=True)
        else:
            interactive_setup()
            self.__init__()
    def get_server_alias(self,id:int) -> str:
        return self.tracked_servers[str(id)]

def checked_int_input(prompt:str) -> int:
    while True:
        value = input(prompt)
        if not value.isdigit():
            print("requires integer")
        else:
            return int(value)

def interactive_setup():
    cfg = {}

    cfg[Config.KEY_TOKEN] = input(f"{Config.KEY_TOKEN}: ").strip()
    cfg[Config.KEY_BATCH_SIZE] = checked_int_input(f"{Config.KEY_BATCH_SIZE}: ")
    cfg[Config.KEY_DUMP_INTERVAL_MINUTES] = checked_int_input(f"{Config.KEY_DUMP_INTERVAL_MINUTES}")
    cfg[Config.KEY_DB_ROOT] = input(f"{Config.KEY_DB_ROOT}: ")
    cfg[Config.KEY_PREFIX]= input(f"{Config.KEY_PREFIX}")
    cfg[Config.KEY_SERVER_NAMES] = {}
    jsonned = json.dumps(cfg)
    with open(CONFIG,'x') as f:
        f.write(jsonned)
    print("config generated")
