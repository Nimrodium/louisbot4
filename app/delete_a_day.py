from database import DB,Server
from config import Config
import os
DELETE_DAY=197
cfg = Config()
for server_name in cfg.tracked_servers.values():
    print(f"opening server {server_name}")
    server = Server(os.path.join(cfg.database_directory,server_name))
    for user in server.db.users.values():
        if DELETE_DAY in user.days.keys():
            user.days.pop(DELETE_DAY)
            print(f"deleted {user.name}'s {DELETE_DAY} day")
            # print(f"{user.days}")
        else:
            print(f"{user.name} did not have a {DELETE_DAY} day")
    server.db.flush()