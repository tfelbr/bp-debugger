from abc import ABC, abstractmethod
from typing import Dict, Any, List, Type, Tuple


class Predicate(ABC):
    @abstractmethod
    def hash(self) -> str:
        pass

    @abstractmethod
    def attempt_solve(self, state: Dict[str, Any]) -> bool:
        pass

    @classmethod
    def from_json(cls, json_predicate: Dict[str, str | List[Dict]]) -> "Predicate":
        pass


class AND(Predicate):
    def __init__(self, *predicates: Predicate) -> None:
        self.__predicates = predicates

    def attempt_solve(self, state: Dict[str, Any]) -> bool:
        return all([predicate.attempt_solve(state) for predicate in self.__predicates])

    def hash(self) -> str:
        return "-AND-".join(sorted([predicate.hash() for predicate in self.__predicates]))

    @classmethod
    def from_json(cls, json_predicate: Dict[str, str | List[Dict]]) -> "Predicate":
        predicates = []
        for predicate in json_predicate["predicates"]:
            name: str = predicate["name"]
            predicates.append(POSSIBLE_PREDICATES.get(name).from_json(predicate))
        return cls(*predicates)


class OR(Predicate):
    def __init__(self, *predicates: Predicate) -> None:
        self.__predicates = predicates

    def attempt_solve(self, state: Dict[str, Any]) -> bool:
        return any([predicate.attempt_solve(state) for predicate in self.__predicates])

    def hash(self) -> str:
        return "-OR-".join(sorted([predicate.hash() for predicate in self.__predicates]))

    @classmethod
    def from_json(cls, json_predicate: Dict[str, str | List[Dict]]) -> "Predicate":
        predicates = []
        for predicate in json_predicate["predicates"]:
            name: str = predicate["name"]
            predicates.append(POSSIBLE_PREDICATES.get(name).from_json(predicate))
        return cls(*predicates)


class EventSelected(Predicate):
    def __init__(self, event: str) -> None:
        self.__event = event

    def attempt_solve(self, state: Dict[str, Any]) -> bool:
        return state["selected"] == self.__event

    def hash(self) -> str:
        return f"SELECTED:{self.__event}"

    @classmethod
    def from_json(cls, json_predicate: Dict[str, str | List[Dict]]) -> "Predicate":
        return cls(json_predicate["value"])


class EventRequested(Predicate):
    def __init__(self, event: str) -> None:
        self.__event = event

    def attempt_solve(self, state: Dict[str, Any]) -> bool:
        info: Dict[str, List[str]]
        for info in state["b_thread_info"]:
            if self.__event in info["request"]:
                return True
        return False

    def hash(self) -> str:
        return f"REQUESTED:{self.__event}"

    @classmethod
    def from_json(cls, json_predicate: Dict[str, str | List[Dict]]) -> "Predicate":
        return cls(json_predicate["value"])


class EventBlocked(Predicate):
    def __init__(self, event: str) -> None:
        self.__event = event

    def attempt_solve(self, state: Dict[str, Any]) -> bool:
        info: Dict[str, List[str]]
        for info in state["b_thread_info"]:
            if self.__event in info["block"]:
                return True
        return False

    def hash(self) -> str:
        return f"BLOCKED:{self.__event}"

    @classmethod
    def from_json(cls, json_predicate: Dict[str, str | List[Dict]]) -> "Predicate":
        return cls(json_predicate["value"])


class EventNumber(Predicate):
    def __init__(self, number: int) -> None:
        self.__number = number

    def attempt_solve(self, state: Dict[str, Any]) -> bool:
        if state["id"] == self.__number:
            return True
        return False

    def hash(self) -> str:
        return f"NUMBER:{self.__number}"

    @classmethod
    def from_json(cls, json_predicate: Dict[str, str | List[Dict]]) -> "Predicate":
        return cls(int(json_predicate["value"]))


POSSIBLE_PREDICATES: Dict[str, Type[Predicate]] = {
    "EVENT_SELECTED": EventSelected,
    "EVENT_REQUESTED": EventRequested,
    "EVENT_BLOCKED": EventBlocked,
    "EVENT_NUMBER": EventNumber,
    "AND": AND,
    "OR": OR,
}


class Breakpoint:
    def __init__(self, b_id: str, *chain: Predicate) -> None:
        self.__chain = chain
        self.__current_position = 0
        self.__b_id = b_id

    @classmethod
    def from_json(cls, json_breakpoint: Dict[str, str | List[Dict]]) -> "Breakpoint":
        predicates = []
        for predicate in json_breakpoint["chain"]:
            name: str = predicate["name"]
            possible_predicate_type = POSSIBLE_PREDICATES.get(name)
            if possible_predicate_type is None:
                raise ValueError(f"Predicate '{name}' not known")
            predicates.append(possible_predicate_type.from_json(predicate))
        return cls(json_breakpoint["id"], *predicates)

    @property
    def b_id(self) -> str:
        return self.__b_id

    def advance(self, state: Dict[str, Any]) -> bool:
        predicate = self.__chain[self.__current_position]
        if predicate.attempt_solve(state):
            self.__current_position += 1
        else:
            self.reset()
            # check if the current state would solve the first predicate,
            # after it was not able to solve the previous one
            first_predicate = self.__chain[self.__current_position]
            if first_predicate.attempt_solve(state):
                self.__current_position += 1
        if self.__current_position == len(self.__chain):
            self.reset()
            return True
        return False

    def reset(self) -> None:
        self.__current_position = 0

    def hash_chain(self) -> str:
        return "--".join([predicate.hash() for predicate in self.__chain])


class DifferenceBreakpoint(Breakpoint):
    def __init__(self, b_id: str, current_position: int, *chain: Predicate) -> None:
        super().__init__(b_id, *chain)
        self.__chain = chain
        self.__current_position = current_position
        print(current_position)

    def advance(self, state: Dict[str, Any]) -> bool:
        if self.__current_position < len(self.__chain):
            predicate = self.__chain[self.__current_position]
            self.__current_position += 1
            if predicate.attempt_solve(state):
                return False
            else:
                return True
        else:
            return False

    @classmethod
    def from_json(cls, json_breakpoint: Dict[str, str | List[Dict]]) -> "DifferenceBreakpoint":
        predicates = []
        for predicate in json_breakpoint["chain"]:
            name: str = predicate["name"]
            possible_predicate_type = POSSIBLE_PREDICATES.get(name)
            if possible_predicate_type is None:
                raise ValueError(f"Predicate '{name}' not known")
            predicates.append(possible_predicate_type.from_json(predicate))
        return cls(json_breakpoint["id"], int(json_breakpoint["current_position"]), *predicates)


class BreakpointRepository:
    def __init__(self) -> None:
        self.__breakpoints_by_chain: Dict[str, Breakpoint] = dict()
        self.__fired_by_breakpoint: Dict[Breakpoint, bool] = dict()

    def add_breakpoint(self, break_point: Breakpoint) -> None:
        chain_hash = break_point.hash_chain()
        if chain_hash in self.__breakpoints_by_chain:
            raise KeyError(f"Breakpoint with hash '{chain_hash}' already exists")
        self.__breakpoints_by_chain[chain_hash] = break_point
        self.__fired_by_breakpoint[break_point] = False

    def delete_breakpoint(self, b_id: str) -> None:
        for chain_hash, break_point in self.__breakpoints_by_chain.items():
            if break_point.b_id == b_id:
                self.__breakpoints_by_chain.pop(chain_hash)
                self.__fired_by_breakpoint.pop(break_point)
                break

    def advance_break_points(self, state: Dict[str, Any]) -> bool:
        all_state = []
        for break_point in self.__breakpoints_by_chain.values():
            fired = break_point.advance(state)
            self.__fired_by_breakpoint[break_point] = fired
            all_state.append(fired)
        if True in all_state:
            return True
        return False

    def which(self) -> Tuple[str, ...]:
        result = []
        for b, fired in self.__fired_by_breakpoint.items():
            if fired:
                result.append(b.b_id)
        return tuple(result)
