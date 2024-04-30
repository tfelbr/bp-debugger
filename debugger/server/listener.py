import json
import time
from datetime import datetime
from multiprocessing import Queue
from threading import Thread, Lock
from typing import Dict, Callable, Any, List, Optional

from bppy import BProgramRunnerListener, BProgram, BEvent, All, EventSetList, EventSet, EmptyEventSet
from flask import Flask, Response, request

from debugger.bp_server.break_point import BreakpointRepository, Breakpoint, DifferenceBreakpoint


def _format_sse(data: str, event=None) -> str:
    msg = f'data: {data}\n\n'
    if event is not None:
        msg = f'event: {event}\n{msg}'
    return msg


def _extract_event_names_if_known(event_set: Any, known_events: Optional[List[BEvent]] = None) -> List[BEvent]:
    if known_events is None:
        known_events_list = []
    else:
        known_events_list = known_events
    if isinstance(event_set, list):
        result = []
        for e in event_set:
            result.extend(_extract_event_names_if_known(e, known_events))
        return result
    else:
        if event_set is None:
            return []
        elif isinstance(event_set, EmptyEventSet):
            return []
        elif isinstance(event_set, All):
            return known_events_list
        elif isinstance(event_set, EventSetList):
            return [event for event in event_set.lst]
        elif isinstance(event_set, EventSet):
            # AllExcept and EventSet can be handled via the predicate
            result = []
            for event in known_events_list:
                if event_set.predicate(event):
                    result.append(event)
            return result
        else:
            return [event_set]


def _get_all_events(state_info: List[Dict[str, Any]]) -> List[BEvent]:
    result = []
    for t in state_info:
        possible_event_sets = {
            "request": t.get("request"),
            "wait_for": t.get("waitFor"),
            "block": t.get("block"),
        }
        for _, event_set in possible_event_sets.items():
            result.extend(_extract_event_names_if_known(event_set))
    return list(set(result))


class MonitoringListener(BProgramRunnerListener):
    def __init__(self, listener: BProgramRunnerListener, name: str, port: int = 5000) -> None:
        self.__listener = listener
        self.__flask_app = Flask(name)
        self.__flask_task = Thread(target=self.__flask_app.run, kwargs={"port": port, "threaded": True})
        self.__event_queue = Queue()
        self.__b_thread_by_name = dict()
        self.__data_to_send = lambda: dict()
        self.current_id = 0

        self.__flask_app.route("/settimeout/<timeout>")(self.__set_timeout)
        self.__flask_app.route("/listen")(self.__client_listen)
        self.__flask_app.route("/pause")(self.__pause)
        self.__flask_app.route("/continue")(self.__continue)
        self.__flask_app.route("/step")(self.__step)
        self.__flask_app.route("/breakpoints/add", methods=["POST"])(self.__add_breakpoint)
        self.__flask_app.route("/breakpoints/delete/<b_id>")(self.__delete_breakpoint)
        self.__flask_app.route("/connect")(self.__client_connect)
        self.__flask_app.route("/setParameter/<parameter>/<new_value>")(self.__set_parameter)

        self.__timeout = 0

        self.__run_lock = Lock()
        self.__run_lock.acquire()
        self.__step_lock = Lock()
        self.__set_break_point = False
        self.__stepping = False

        self.__breakpoint_repository = BreakpointRepository()

    def __client_connect(self) -> Response:
        to_send = self.__data_to_send()
        for value in to_send.values():
            value.pop("callback", None)
        return Response(json.dumps(to_send))

    def __client_listen(self) -> Response:
        def stream():
            while True:
                data = self.__event_queue.get()
                yield _format_sse(json.dumps(data))
        return Response(
            stream(),
            mimetype='text/event-stream',
            headers={"Access-Control-Allow-Origin": "*"}
        )

    def __pause(self) -> str:
        self.__run_lock.acquire()
        self.__send_paused()
        return ""

    def __continue(self) -> str:
        if self.__run_lock.locked():
            self.__run_lock.release()
        self.__stepping = False
        return ""

    def __step(self) -> str:
        self.__stepping = True
        self.__run_lock.release()
        self.__step_lock.acquire()
        self.__run_lock.acquire()
        self.__step_lock.release()
        return ""

    def __set_timeout(self, timeout: int) -> str:
        self.__timeout = float(timeout)
        return ""

    def __add_breakpoint(self) -> str:
        json_break_point: dict = request.json
        if json_break_point["id"] == "0":
            self.__breakpoint_repository.add_breakpoint(DifferenceBreakpoint.from_json(json_break_point))
        else:
            self.__breakpoint_repository.add_breakpoint(Breakpoint.from_json(json_break_point))
        return ""

    def __delete_breakpoint(self, b_id: str) -> str:
        self.__breakpoint_repository.delete_breakpoint(b_id)
        return ""

    def __set_parameter(self, parameter: str, new_value: str) -> str:
        value_type = type(self.__data_to_send()[parameter]["value"])
        if value_type == int:
            self.__data_to_send()[parameter]["callback"](int(new_value))
        elif value_type == str:
            self.__data_to_send()[parameter]["callback"](new_value)
        else:
            if new_value == "True":
                self.__data_to_send()[parameter]["callback"](True)
            else:
                self.__data_to_send()[parameter]["callback"](False)
        return ""

    def __send_paused(self, *breakpoint_id: str) -> None:
        self.__event_queue.put(
            {
                "type": "info",
                "paused": True,
                "ended": False,
                "breakpoint_ids": list(breakpoint_id),
            }
        )

    def __send_ended(self) -> None:
        self.__event_queue.put(
            {
                "type": "info",
                "paused": True,
                "ended": True,
                "breakpoint_ids": list(),
            }
        )

    def mark_name(self, name: str, b_thread):
        self.__b_thread_by_name[b_thread] = name
        return b_thread

    def register_data_poll(self, data_poll: Callable[[], Dict[str, Dict[str, str | int | bool]]]) -> None:
        self.__data_to_send = data_poll

    def starting(self, b_program: BProgram):
        self.__flask_task.start()
        return self.__listener.starting(b_program)

    def started(self, b_program: BProgram):
        return self.__listener.started(b_program)

    def super_step_done(self, b_program: BProgram):
        return self.__listener.super_step_done(b_program)

    def ended(self, b_program: BProgram):
        self.__send_ended()
        return self.__listener.ended(b_program)

    def assertion_failed(self, b_program: BProgram):
        return self.__listener.assertion_failed(b_program)

    def b_thread_added(self, b_program: BProgram):
        return self.__listener.b_thread_added(b_program)

    def b_thread_removed(self, b_program: BProgram):
        return self.__listener.b_thread_removed(b_program)

    def b_thread_done(self, b_program: BProgram):
        return self.__listener.b_thread_done(b_program)

    def event_selected(self, b_program: BProgram, event: BEvent):
        time.sleep(self.__timeout)
        if self.__set_break_point:
            if not self.__stepping:
                self.__run_lock.acquire()
            self.__send_paused(*self.__breakpoint_repository.which())
            self.__set_break_point = False
        self.__step_lock.acquire()
        self.__run_lock.acquire()
        try:
            selected = event.name
            final_data = {"selected": selected, "b_thread_info": []}
            tickets = b_program.tickets
            all_events = _get_all_events(tickets)
            t: dict
            for t in tickets:
                # base infos
                if len(t) == 0:
                    continue
                b_thread_name = self.__b_thread_by_name[t["bt"]]
                priority = t.get("priority", 0)
                possible_event_sets = {
                    "request": t.get("request"),
                    "wait_for": t.get("waitFor"),
                    "block": t.get("block"),
                }

                # break down of event sets
                b_thread_info = {"name": b_thread_name, "priority": priority}
                for tag, event_set in possible_event_sets.items():
                    b_thread_info[tag] = [e.name for e in _extract_event_names_if_known(event_set, all_events)]
                final_data["b_thread_info"].append(b_thread_info)

            result = self.__listener.event_selected(b_program, event)
            final_data["parameters"] = self.__data_to_send()
            for values in final_data["parameters"].values():
                values.pop("callback", None)
            final_data["datetime"] = datetime.now().timestamp()
            final_data["id"] = self.current_id
            final_data["type"] = "trace"
            self.current_id += 1
            self.__event_queue.put(final_data)

            if self.__breakpoint_repository.advance_break_points(final_data):
                self.__set_break_point = True

            return result
        finally:
            self.__step_lock.release()
            self.__run_lock.release()

    def halted(self, b_program: BProgram):
        return self.__listener.halted(b_program)
