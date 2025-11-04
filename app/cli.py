# cli parsing module

from typing import Any,TypeVar,Generic
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

@dataclass
class ParsingReturn:
    string:str
    success:bool
    img:str|None=None

# pub
def parse_cli(command_line:str) -> ParsingReturn:
    command_stream = ParseStream[str](command_line)
    while True:
        nx = command_stream.next()
        match command_stream.next():
            case None:
                break
            case str:
                match nx:
                    case "plot"|"p":
                        pass
                    case "ping":
                        return ParsingReturn(
                            string = "pong!"
                            success = True
                            )


def parse_plot(command_line:str) ->
