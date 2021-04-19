import typing as t


CB = t.TypeVar('CB', bound=t.Any)
CBV = t.Callable[[CB], bool]
TYPE_METHODS = t.Union[t.Collection[str], str]
TYPE_PATH = t.Union[str, t.Pattern]
