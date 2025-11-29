# cli parsing module
# from enum improt Enum,auto
from typing import Any, TypeVar, Generic, Literal, Optional, Tuple
from dataclasses import dataclass
from database import DB, Server
from database import datetime_to_epoch_day
from datetime import datetime,timedelta
from dateutil import parser as natural_date_parser
from config import Config
import traceback
# from analysis import (  generate_message_pie_chart,
#                         generate_emoji_pie_chart,
#                         generate_line_message_chart,
#                         generate_line_emoji_chart
#                     )
from analysis import Analyzer
T = TypeVar("T")
from database import User


class ParseStream(Generic[T]):
    def __init__(self, inner: list[T]):
        self.inner = inner

    def next(self) -> T | None:
        v = self._get_next()
        if v is not None:
            self._consume_next()
        return v

    def peek(self,offset:int=0) -> T | None:
        return self._get_next()

    def _get_next(self,offset:int=0) -> T | None:
        if self._is_next(offset):
            # print(self.inner[offset])
            return self.inner[offset]
        else:
            return None

    def _consume_next(self) -> None:
        if self._is_next():
            v = self.inner.pop(0)
            # print(f"consumed {v}")
    def _is_next(self,offset:int=0) -> bool:
        if offset < len(self.inner):
            return True
        else:
            # print(f"is not next, length is {len(self.inner)}")
            return False

@dataclass
class CommandResult:
    success: bool
    string: str = ""
    img: str | None = None
    do_not_send: bool = False
    action:str|None=None

# generic empty interface
class GraphCommand:
    members: list[str] | None
    pass


@dataclass
class ReactionsGraph(GraphCommand):
    # kind:Literal["line", "pie"]
    # None = All
    reactions: list[str] | None
    members: list[str] | None
    def __str__(self) -> str:
        return f"reactions of emoji:{self.reactions} from members:{self.members}"

@dataclass
class MessagesGraph(GraphCommand):
    members: list[str] | None
    def __str__(self) -> str:
        return f"messages of members:{self.members}"


@dataclass
class ParsedGraphCommand:
    # "pie" "line"
    kind:str
    graph: GraphCommand
    range_start: int
    range_end: int
    granularity:str="days"
    def __str__(self) -> str:
        return f"{self.kind} graph of {self.graph} with range starting from {self.range_start} to {self.range_end}"
    
    # TODO: refactor generate_line_emoji_chart to allow for multiple emojis
    def evaluate(self,caller_id:int,server:Server,server_name:str,cfg:Config) -> CommandResult:
        # print(ramge_sta)
        def process_members(m:list[str]|None,none_is_all:bool) -> list[User]|Error:
            if m is None:
                if none_is_all:
                    return server.db.get_all_users()
                else:
                    caller = server.db.get_user(caller_id)
                    if caller is not None:
                        return [caller]
                    else: return Error(f"calling user @<{caller_id}> is not registered in the database")
            else:
                all_users = server.db.get_all_users()
                if len(m) == 1 and m[0] == "!":
                    return all_users
                else:
                    return [u for u in all_users if u.name in m]
        def process_reactions(r:list[str]|None,more_than_one:bool) -> list[str]|Error:
            if r is None:
                return Error(f"{"at least one reaction" if more_than_one else "exactly one reaction"} must be defined, however none was provided")
            if len(r) > 1 and not more_than_one:
                return Error(f"exactly one reaction must be provided")
            if len(r) == 1 and r[0] == "!":
                if more_than_one:
                    return server.db.get_all_reactions()
                else:
                    return Error("the `!` wildcard is not allowed here")
            return r
        analyzer = Analyzer(cfg)
        message : str
        image : str
        try:
            match self.kind:
                case "pie":
                    members = process_members(self.graph.members,True)
                    if isinstance(members,Error):
                                return members.to_command_result()
                    match self.graph:
                        
                        case x if isinstance(self.graph,MessagesGraph):
                            message,image = analyzer.generate_message_pie_chart(server_name,members,self.range_start,self.range_end)
                        
                        case x if isinstance(self.graph,ReactionsGraph):
                            reactions = process_reactions(self.graph.reactions,False)
                            if isinstance(reactions,Error):
                                return reactions.to_command_result()
                            message,image = analyzer.generate_emoji_pie_chart(server_name,reactions[0],members,self.range_start,self.range_end)
                        
                        case _:
                            # unreachable
                            pass
                case "line":
                    members = process_members(self.graph.members,False)
                    if isinstance(members,Error):
                                return members.to_command_result()
                    match self.graph:
                        case x if isinstance(self.graph,MessagesGraph):
                            message,image = analyzer.generate_line_message_chart(server_name,members,self.range_start,self.range_end,self.granularity)
                        case x if isinstance(self.graph,ReactionsGraph):
                            
                            reactions = process_reactions(self.graph.reactions,False)
                            if isinstance(reactions,Error):
                                return reactions.to_command_result()
                            message,image = analyzer.generate_line_emoji_chart(server_name,members,self.range_start,self.range_end,self.granularity,reactions[0])
                        case _:
                            # unreachable
                            pass
        except Exception as e:
            print(traceback.format_exc())
            return CommandResult(string=f"while processing command: {str(e)}",success=False)
        return CommandResult(string=message, success=True if image is not None else False,img=image)
  
@dataclass
class Error:
    why: str = ""

    def to_command_result(self) -> CommandResult:
        return CommandResult(success=False, string=self.why)
    def traceback(self,trace:str) -> "Error":
        self.why = f"while {trace}:\n\t{self.why}"
        return self
    def __str__(self) -> str:
        return self.why
# pub


def parse(command_line: str,caller_id:int, server:Server,server_name:str,cfg:Config) -> CommandResult:
    parsed = just_parse_cli(command_line)
    if isinstance(parsed,CommandResult):
        return parsed
    else:
        return parsed.evaluate(caller_id,server,server_name,cfg)
    
def just_parse_cli(command_line:str) -> ParsedGraphCommand|CommandResult:
    stream = ParseStream[str](command_line.split())
    nx = stream.next()
    match nx:
        case None:
            return CommandResult(do_not_send=True,success=False)
        case "plot"|"p":
            x = parse_plot(stream)
            if isinstance(x,Error):
                return x.to_command_result()
            else:
                print(x)
                print(x.range_start,x.range_end)
                return x
        case "ping":
            return CommandResult(string="pong!", success=True)
        case "process":
            return CommandResult(string="processed batch",success=True,action="process")
        case "flush":
            return CommandResult(string="flushed database",success=True,action="flush")
        case _:
            return CommandResult(
                string=f"`{nx}` is not a recognized command",
                success=False,
            )

# parses multiple named lists 
# eg. ( list1: [ a b c ] list2: [ d e f ] other command )
# parses into lists {"list1":["a","b","c"],"list2":["d" "e" "f"]}

def parse_lists(stream:ParseStream[str]) -> dict[str,list[str]] | Error | None:
    def is_key(s:str|None) -> bool: return s.endswith(":") if isinstance(s,str) else False
    def is_prelimiter(s:str|None) -> bool: return s.startswith("[") if isinstance(s,str) else False
    def is_delimiter(s:str|None) -> bool: return s.endswith("]") if isinstance(s,str) else False
    def extract_value(s:str|None) -> str|None: 
        if s is None:
            return None
        v = s.removeprefix("[").removesuffix("]") # technically i am doing redunant code execution with removeprefix on the inner elements, but... its python i dont care.
        if v != "": 
            return v
        else:
            return None
    
    def parse_list(stream:ParseStream[str]) -> list[str] | Error | None:
        first = stream.next()
        parsed = list[str]()
        if first is None:
            return Error("list was defined without any members")
        value = extract_value(first)
        if value is not None:
            parsed.append(value)
        
        if not is_prelimiter(first):
            return parsed
        if is_prelimiter(first) and is_delimiter(first) and value is None:
            return Error("list was defined without any members")
        if is_prelimiter(first) and is_delimiter(first):
            return parsed
        while True:
            next_member = stream.next()
            value = extract_value(next_member)
            if value is None:
                if is_delimiter(next_member):
                    break
                else:
                    return Error("expected another element in list, instead got end of command (eg: [... missing -> ])")
            parsed.append(value)
            if is_delimiter(next_member):
                    break
        return parsed

    lists = dict[str,list[str]]()
    while True:
        key: str | None = stream.peek()
        if not is_key(key):

            break
        stream.next() # consume key
        assert isinstance(key,str)
        parsed = parse_list(stream)
        match parsed:
            case x if isinstance(parsed,Error):
                return x.traceback(f"evaluating list key `{key.removesuffix(":")}`") # type: ignore
            case x if isinstance(parsed,list):
                lists.update({key.removesuffix(":"):parsed})
    
    return lists



def parse_plot(cmd_stm: ParseStream[str]) -> ParsedGraphCommand | Error:
    graph: GraphCommand
    data_range_start: int
    data_range_end: int
    nx = cmd_stm.next()
    kind : str
    match nx:
        case "pie":
            granularity = "days" # fucked
            kind = "pie"
            x = parse_data_kind(cmd_stm)
            if isinstance(x, Error):
                return x
            else:
                graph = x
            # data_range = parse_data_range(cmd_stm)
        case "line":
            kind = "line"
            granularity = parse_line_granularity(cmd_stm)
            x = parse_data_kind(cmd_stm)
            if isinstance(x, Error):
                return x
            else:
                graph = x
            # data_range_start, data_range_end = parse_data_range(cmd_stm)
        case _:
            return Error("expected a plot subcommand, either line or pie")
    result = parse_data_range(cmd_stm)
    if isinstance(result,Error):
        return result.traceback("evaluating range")
    else:
        data_range_start, data_range_end = result
    # data_range_start=0
    print(f"range {data_range_start}-{data_range_end}")
    return ParsedGraphCommand(kind, graph, data_range_start, data_range_end, granularity)

def parse_line_granularity(stream:ParseStream[str]) -> str:
    nxt = stream.peek()
    match nxt:
        case "days":
            stream.next()
            return "days"
        case "hours":
            stream.next()
            return "hours"
        case _:
            return "days"

def parse_data_kind(command_stream: ParseStream[str]) -> GraphCommand | Error:
    nx = command_stream.next()
    match nx:
        case "messages" | "m":
            lists = parse_lists(command_stream)
            if isinstance(lists, Error):
                return lists
            members = lists.get("users") if lists else None
            # data_range = parse_data_range(command_stream)
            return MessagesGraph(members)
        case "reactions" | "r":
            lists = parse_lists(command_stream)
            if isinstance(lists, Error):
                return lists
            members = lists.get("users") if lists else None
            emojis = lists.get("emojis") if lists else None
            return ReactionsGraph(emojis, members)
        case _:
            return Error(
                f"not a valid data source, either messages or reactions, not `{nx}`"
            )


def parse_data_range(stream: ParseStream[str]) -> Tuple[int, int]|Error:
    def natural_lang_parser(stream:ParseStream[str],stop_at:str|None=None) -> int|Error:
        collected = collect_stream(stream,stop_at)
        try:
            dt = natural_date_parser.parse(collected)
            return datetime_to_epoch_day(dt)
        except Exception as e:
            return Error(f"natural language parser failed: {e}") 
    # because range is last we can consume the rest of the stream, 
    # however if it wasnt last, id probably have a delimiter token like ;
    # for this.
    def collect_stream(stream:ParseStream[str],stop_at:str|None=None) -> str:
        # would fold this but parsestream is too custom
        aggregate = ""
        while (True):
            nxt = stream.next()
            if nxt is not None:
                if stop_at is not None and nxt ==stop_at:
                    break
                else:
                    aggregate+=" "+nxt
            else:
                break
        return aggregate
    print("parsing data range")
    nxt = stream.next()
    now = datetime.now()
    # default case, 1 week | 7 days
    # if nxt is None:
    #     now = datetime.now()
    #     return (datetime_to_epoch_day(now - timedelta(days=7)),datetime_to_epoch_day(now))
    match nxt:
        case None: 
            print("defaulting to 7 days")
            return (
                datetime_to_epoch_day(now - timedelta(days=7)),
                datetime_to_epoch_day(now)
                )
        case "past":

            err_start = "`past` expects `VALUE:int` `TYPE:[days|weeks|months|years]`,"
            value = stream.next()
            if value is None:
                return Error(f"{err_start} however `VALUE` was not provided")
            if not value.isdigit():
                return Error(f"{err_start} however `VALUE` was not an integer")
            value_int = int(value)
            value_type = stream.next()
            if value_type is None:
                return Error(f"{err_start} however `TYPE` was not provided")
            value_type_caster:int
            match value_type:
                case "days":
                    value_type_caster=1
                case "weeks":
                    value_type_caster=7
                case "months":
                    value_type_caster=32
                case "years":
                    value_type_caster=365
                case _:
                    return Error(f"{err_start} however `TYPE` was not in the defined type set")
            epoch = datetime_to_epoch_day(now - timedelta(days=value_int*value_type_caster))
            print(f"starting date: {value_int*value_type_caster} as epoch {epoch}")
            return (
                # datetime_to_epoch_day(now - timedelta(days=value_int*value_type_caster)),
                epoch,
                datetime_to_epoch_day(now)
                )
        case "since":
            since_start = natural_lang_parser(stream)
            since_end = datetime_to_epoch_day(now)
            if isinstance(since_start,Error):
                return since_start.traceback("evaluating `since`")
            return (
                since_start,since_end
            )
        
        case "from":
            from_start : int|Error = natural_lang_parser(stream,stop_at="to")
            from_end : int|Error = natural_lang_parser(stream)
            if isinstance(from_start,Error):
                return from_start.traceback("evaluating `a` in from `a` to `b`")
            if isinstance(from_end,Error):
                return from_end.traceback("evaluating `b` in from `a` to `b`")
            return (
                from_start,
                from_end
            )
        case _:
            return Error(f"{nxt} is not a valid date format, from the set of `since` `from` `past` ")


if __name__ == "__main__":
    # s = "key: [ test list ] key2: [louis spoink] key3: value3"
    s = "plot line messages users: [nimrod juni] past 7 days"
    stream = ParseStream[str](s.split())
    # print(just_parse_cli(s).string)

