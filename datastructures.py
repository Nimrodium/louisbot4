from nextcord.ext import commands

class MemberLog(dict):
    KEY_ID="id"
    KEY_NAME="name"
    KEY_COUNT="count"
    KEY_EMOJIS="emojis"
    def __init__(self,inner:dict):
        super().__init__()
        if self.KEY_EMOJIS in inner.keys():
            emoji : dict[str,int] = inner[self.KEY_EMOJIS]
        else:
            emoji = {}
        try:
            self.update(
                {
                    self.KEY_ID: inner[self.KEY_ID],
                    self.KEY_NAME: inner[self.KEY_NAME],
                    self.KEY_COUNT: inner[self.KEY_COUNT],
                    self.KEY_EMOJIS:emoji
                }
            )
        except KeyError as e:
            print(f"malformed server json `{e}`")
            exit()
    @classmethod
    async def from_id(cls,ctx:commands.Bot,id:int):
        user = await ctx.fetch_user(id)
        return cls({cls.KEY_ID:id,cls.KEY_NAME:user.name,cls.KEY_COUNT:0})

    def to_dict(self) -> dict:
        return dict(self)

    def id(self) -> int:
        return self[self.KEY_ID]

    def name(self) -> str:
        return self[self.KEY_NAME]

    def count(self) -> int:
        return self[self.KEY_COUNT]

    def emojis(self) -> dict[str,int]:
        return self[self.KEY_EMOJIS]
    def add_to_count(self,delta:int) -> None:
        old = self.count()
        self[self.KEY_COUNT] = old+delta

    def reset_count(self) -> None:
        self[self.KEY_COUNT] = 0

    def inc_emoji(self,emoji_name:str) -> None:
        emojis = self[self.KEY_EMOJIS]
        if emoji_name in emojis.keys():
            old_val = emojis[emoji_name]
        else:
            old_val = 0

        emojis.update({emoji_name:old_val+1})

# object that holds a single members data across points
class MemberData:
    def __init__(self,former:MemberLog):
        self.id = former.id()
        self.name = former.name()
        self.counts : list[int] = []
        self.emojis : dict[str,list[int]] = {}
        self.merge(former)

    def merge(self,other:MemberLog) -> None:
        if other.id() != self.id:
            raise Exception("Merge rejected because id's differed")
        self.counts.append(other.count())
        for (emoji_name,count) in other.emojis().items():
            if emoji_name in self.emojis.keys():
                self.emojis[emoji_name].append(count)
            else:
                self.emojis.update({emoji_name:[count]})
    def total_messages(self) -> int:
        return sum(self.counts)
    # # returns 0 if key missing
    def total_reactions_of(self,reaction:str) -> int:
        print(self.emojis)
        if reaction in self.emojis.keys():
            return sum(self.emojis[reaction])
        else:
            return 0

class Server(dict):
    KEY_MEMBERS="members" # : dict
    KEY_ID="id"  # : int
    KEY_STDNAME="std_name" # : str
    KEY_TOTAL_MESSAGES="total_messages" # : int
    KEY_TOP_MESSANGER="top_messanger" # : int (member key)
    KEY_TOP_MESSANGER_MESSAGES="top_messanger_messages" # int
    def __init__(self,inner:dict):
        super().__init__()
        try:
            members_raw = inner[self.KEY_MEMBERS]
            members : dict[int,MemberLog] = {}
            for (id,member) in members_raw.items():
                members.update({int(id):MemberLog(member)})
            self.update(
            {
                self.KEY_MEMBERS:members,
                self.KEY_ID:inner[self.KEY_ID],
                self.KEY_STDNAME:inner[self.KEY_STDNAME],
                self.KEY_TOTAL_MESSAGES:inner[self.KEY_TOTAL_MESSAGES],
                self.KEY_TOP_MESSANGER:inner[self.KEY_TOP_MESSANGER],
                self.KEY_TOP_MESSANGER_MESSAGES:inner[self.KEY_TOP_MESSANGER_MESSAGES],
            }
        )
        except KeyError as e:
            print(f"malformed server json `{e}`")
            exit()
    @classmethod
    def new(cls,id:int,std_name:str):
        return cls({cls.KEY_ID:id,cls.KEY_STDNAME:std_name,cls.KEY_MEMBERS:{},cls.KEY_TOP_MESSANGER:0,cls.KEY_TOP_MESSANGER_MESSAGES:0,cls.KEY_TOTAL_MESSAGES:0})

    def members(self) -> dict[int,MemberLog]:
        return self[self.KEY_MEMBERS]

    async def get_member(self,ctx:commands.Bot,id:int) -> MemberLog:
        members = self.members()
        member = members.get(id)
        if member:
            return member
        else:
            new = await MemberLog.from_id(ctx,id);
            self.add_member(new)
            return members[id]

    def add_member(self,new_member:MemberLog) -> None:
        self.members().update({new_member.id():new_member})
