from json import JSONDecoder, JSONEncoder
from typing import Any, Callable, Dict, Generic, Protocol, Tuple, Type, TypeVar

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


class TwoWayDict(Generic[K, V]):
    """
    A two-way dictionary that allows for key-value and value-key lookups.
    """

    kv: Dict[K, V]
    vk: Dict[V, K]

    def __init__(self):
        self.kv = {}
        self.vk = {}

    def __setitem__(self, key: K, value: V):
        self.kv[key] = value
        self.vk[value] = key

    def __getitem__(self, key: K) -> V:
        return self.kv[key]

    def get_key(self, value: V) -> K:
        return self.vk[value]

    def __delitem__(self, key: K):
        value = self.kv[key]
        del self.kv[key]
        del self.vk[value]

    def __contains__(self, key: K) -> bool:
        return key in self.kv

    def __len__(self) -> int:
        return len(self.kv)

    def __iter__(self):
        return iter(self.kv)

    def items(self):
        return self.kv.items()

    def keys(self):
        return self.kv.keys()

    def values(self):
        return self.kv.values()


class JSONSerializable(Protocol):
    """
    Structural type for JSON serializable objects.

    To implement, define a classmethod __json__ that returns a tuple of attribute names which will be used to uniquely identify the object type.
    """

    @classmethod
    def __json__(cls) -> Tuple[str, ...]:
        """
        Return a tuple of attribute names that will be used to uniquely identify the object type.
        """
        ...


class JSONSerializableManager:
    """
    Manager for types that should be serialized by builtin json module.

    Registers and unregisters types and builds custom JSONEncoder and JSONDecoder classes.

    Example:
    >>> manager = JSONSerializableManager()
    >>> manager.register(TestCustomClassA)
    >>> manager.register(TestCustomClassB)

    >>> json_str = json.dumps(test, cls=manager.build_encoder())
    >>> print(json_str)

    >>> decoded = json.loads(json_str, cls=manager.build_decoder())
    >>> print(decoded, type(decoded))

    """

    types: TwoWayDict[Tuple[str, ...], type]
    encoders: Dict[Tuple[str, ...], Callable]
    decoders: Dict[Tuple[str, ...], Callable]

    def __init__(self):
        self.types = TwoWayDict()
        self.encoders = {}
        self.decoders = {}

    def __register(self, cls: Type, json_attrs: Tuple[str, ...]):
        if json_attrs in self.types:
            raise ValueError(
                f"Registered type {self.types[json_attrs]} has same attribute signature {json_attrs}."
            )
        self.types[json_attrs] = cls

    def register(self, cls: Type[JSONSerializable]):
        """
        Register a JSONSerializable type.

        Args:
            cls (Type[JSONSerializable]): JSONSerializable type to register.
        """
        self.__register(cls, cls.__json__())

    def register_special(self, cls: Type[T], json_attrs: Tuple[str, ...]):
        """
        Register a type with a custom attribute signature.

        Args:
            cls (Type): JSONSerializable type to register.
            json_attrs (Tuple[str, ...]): Custom attribute signature.
        """
        self.__register(cls, json_attrs)

    def add_decoder(self, cls: Type[T], decoder: Callable[[Dict[str, Any]], T]):
        """
        Add a custom decoder for a registered type.

        Args:
            cls (Type[T]): Type to decode.
            decoder (Callable): Decoder function.
        """
        json_attr = self.types.get_key(cls)
        if json_attr in self.decoders:
            raise ValueError(
                f"Decoder for type {cls} with attribute signature {json_attr} already exists."
            )
        self.decoders[json_attr] = decoder

    def add_encoder(self, cls: Type[T], encoder: Callable[[T], Dict[str, Any]]):
        """
        Add a custom encoder for a registered type.

        Args:
            cls (Type[T]): Type to encode.
            encoder (Callable): Encoder function.
        """
        json_attr = self.types.get_key(cls)
        if json_attr in self.encoders:
            raise ValueError(
                f"Encoder for type {cls} with attribute signature {json_attr} already exists."
            )
        self.encoders[json_attr] = encoder

    def build_encoder(self) -> Type[JSONEncoder]:
        """
        Build a custom JSONEncoder class that can serialize registered JSONSerializable types.

        Returns:
            Type[JSONEncoder]: Custom JSONEncoder class.
        """

        def default(self_encoder, o: JSONSerializable):
            if o is None or isinstance(o, (int, float, str, bool, list, tuple, dict)):
                return o
            else:
                json_attr = self.types.get_key(type(o))
                if json_attr in self.encoders:
                    return self.encoders[json_attr](o)
                else:
                    o_dict = {}
                    for key in json_attr:
                        o_dict[key] = self_encoder.default(getattr(o, key))  # type: ignore
                    return o_dict

        return type(
            "ExtensibleEncoder",
            (JSONEncoder,),
            {"default": default},
        )

    def build_decoder(self) -> Type[JSONDecoder]:
        """
        Build a custom JSONDecoder class that can deserialize registered JSONSerializable types.

        Returns:
            Type[JSONDecoder]: Custom JSONDecoder class.
        """

        def object_hook(o):
            if isinstance(o, dict):
                key_tuple = tuple(o.keys())
                if key_tuple in self.decoders:
                    return self.decoders[key_tuple](o)
                elif key_tuple in self.types:
                    obj = self.types[key_tuple].__new__(self.types[key_tuple])  # type: ignore
                    for key in o.keys():
                        setattr(obj, key, object_hook(o[key]))
                    return obj
                return {key: object_hook(value) for key, value in o.items()}
            elif isinstance(o, list):
                return [object_hook(value) for value in o]
            elif isinstance(o, tuple):
                return tuple(object_hook(value) for value in o)
            else:
                return o

        def __init__(self, object_hook=object_hook, *args, **kwargs):
            JSONDecoder.__init__(self, object_hook=object_hook, *args, **kwargs)

        return type(
            "ExtensibleDecoder",
            (JSONDecoder,),
            {"__init__": __init__},
        )
