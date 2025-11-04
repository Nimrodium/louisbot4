# cli parsing module
# from enum improt Enum,auto
from typing import Any,TypeVar,Generic,Literal,Optional,Tuple
from dataclasses import dataclass
from database import DB
T = TypeVar('T')
class ParseStream(Generic[T]):
    def __init__(self,inner:list[T]):
        self.inner = inner

    def next(self) -> T|None:
        v = self._get_next()
        if v is not None:
            self._consume_next()
        return v

    def peek(self) -> T|None:
        return self._get_next()
    
    def _get_next(self) -> T|None:
        if self._is_next():
            return self.inner[0]
        else:
            return None

    def _consume_next(self) -> None:
        if self._is_next():
            self.inner.pop(0)

    def _is_next(self) -> bool:
        if len(self.inner) != 0:
            return True
        else:
            return False

# class Plots(Enum):
#     Line = auto()
#     Pie = auto()


@dataclass
class CommandResult:
    success:bool
    string:str=""
    img:str|None=None
    do_not_send:bool=False
# generic empty interface
class GraphCommand:
    pass

@dataclass
class ReactionsGraph(GraphCommand):
    # None = All 
    emoji:list[str]|None
    members:list[str]|None
@dataclass
class MessagesGraph(GraphCommand):
    members:list[str]|None

@dataclass
class ParsedGraphCommand:
    graph:GraphCommand
    range_start:int
    range_end:int
    def evaluate(self) -> CommandResult:
        return CommandResult(
            string = "stub",
            success = True
        )
# @dataclass
# class ParsedCommand:
#     plot : Literal["pie","line"]|None
#     data : Literal["messages","reactions"]|None
#     data_range : int|None # days

#     # def assert_valid(self) -> None|str:
#     #     if plot == None:
#     #         return "plot type is None"
#     #     if data == None:
#     #         return "data source is None"
#     #     if data_range == None:
#     #         return "data range is None"
#     #     return None
#     def execute(self) -> CommandResult:
#         receipt = assert_valid()
#         # if isinstance(receipt,str):
#         #     return CommandResult(string=receipt,success=False)
#         match self.plot:
#             case None:
#                 return CommandResult(string="plot type is None",success=False)
#             case "pie":
#                 pass
#             case "line":
#                 pass

@dataclass
class Error:
    why:str=""
    def to_command_result(self) -> CommandResult:
        return CommandResult(success=False,string=self.why)
# pub
def just_parse_cli(command_line:str,db:DB) -> CommandResult:
    command_stream = ParseStream[str](command_line.split())
    nx = command_stream.next()
    match nx:
        case None:
            return CommandResult(do_not_send=True,success=False)
        case "plot"|"p":
            x = parse_plot(command_stream)
            if isinstance(x,Error):
                return x.to_command_result()
            else:
                return x.evaluate()
        case "ping":
            return CommandResult(
                string = "pong!",
                success = True
                )
        case _:
            return CommandResult(
                string = f"`{nx}` is not a recognized command",
                success = False,
            )
    
# def parse_pie(command_stream:ParseStream[str]) -> CommandResult:
#     pass    
# def parse_line(command_stream:ParseStream[str]) -> CommandResult:
#     pass

def parse_lists(cmd_stm:ParseStream[str],expected_keys:list[Optional[str]]) -> dict[str,list[str]]|Error|None:
    def is_delimiter(s:str) -> bool:
        return s.endswith("]")
    nx: str|None = cmd_stm.next()
    if nx not in expected_keys:
        return None
    lists = dict[str,list[str]]()
    while True:
        nx = cmd_stm.peek()
        match nx:
            case None:
                return None
            case k if k in expected_keys:
                cmd_stm.next()
                xs : list[str]|Error = fill_list(cmd_stm)
                match xs:
                    case x if isinstance(x,Error):
                        return xs
                    case _:
                        lists.update({nx:xs})
            case _:
                return lists
    # lists = dict[str,list[str]]()
    # while True:
    #     nx = cmd_stm.next()
    #     match nx:
    #         case None:
    #             return Error(f"expecting a list after {expecting_key}")
    #         case "[":

def fill_list(cmd_stm:ParseStream[str]) -> list[str]|Error:
    xs = list[str]()
    nx = cmd_stm.next()
    match nx:
        case None:
            return Error("expected a list after key")
        case "[":
            pass
        # handles [x ... ] and  [x]
        case x if x.startswith("["):
            xs.append(x.removeprefix("["))
            if x.endswith("]"):
                return xs            
        # handles single x 
        case _:
            xs.append(nx)
            return xs
    while True:
        nx = cmd_stm.next()
        match nx:
            case None:
                return xs
            case "]":
                return xs
            case x if x.endswith("]"):
                xs.append(x.removesuffix("]"))
                return xs
            case _:
                xs.append(nx)


def parse_plot(cmd_stm:ParseStream[str]) -> ParsedGraphCommand|Error:
    graph:GraphCommand
    data_range_start:int
    data_range_end:int
    nx = cmd_stm.next()
    match nx:
        case "pie":
            x = parse_data_kind(cmd_stm)
            if isinstance(x,Error):
                return x
            else:
                graph = x
            data_range = parse_data_range(cmd_stm)
        case "line":
            x = parse_data_kind(cmd_stm)
            if isinstance(x,Error):
                return x
            else:
                graph = x
            data_range_start,data_range_end = parse_data_range(cmd_stm)
        case _:
            return Error("expected a plot subcommand, either line or pie")
    return ParsedGraphCommand(graph,data_range_start,data_range_end)


def parse_data_kind(command_stream:ParseStream[str]) -> GraphCommand|Error:
    nx = command_stream.next()
    match nx:
        case "messages"|"m":
            lists = parse_lists(command_stream,["users"])
            if isinstance(lists,Error):
                return lists
            members = lists.get("users") if lists else None
            data_range = parse_data_range(command_stream)
            return MessagesGraph(members)
        case "reactions"|"r":
            lists = parse_lists(command_stream,["users","emojis"])
            if isinstance(lists,Error):
                return lists
            members = lists.get("users") if lists else None
            emojis = lists.get("emojis") if lists else None
            return ReactionsGraph(members,emojis)
        case _:
            return Error(f"not a valid data source, either messages or reactions, not `{nx}`")

def parse_data_range(cmd_stm:ParseStream[str]) -> Tuple[int,int]:
    return 1,2 # stub