import json
from queue import Queue
from threading import Thread, Lock
from typing import List, Dict, Any

import requests
from flask import Flask, render_template, Response, request


def _format_sse(data: str, event=None) -> str:
    msg = f'data: {data}\n\n'
    if event is not None:
        msg = f'event: {event}\n{msg}'
    return msg


class App:
    def __init__(self) -> None:
        self.__flask_app = Flask(__name__, static_url_path="/")

        self.__backup_queue = Queue()
        self.__consumer_queues: List[Queue] = []
        self.__id_by_state: Dict[str, Dict[str, Any]] = dict()
        self.__imported_id_by_state: Dict[str, Dict[str, Any]] = dict()
        self.__timeout = 0
        self.__initial_parameters = dict()
        self.__running = False

        self.__backup_queue_lock = Lock()

        self.__json_breakpoints = {}

        self.__flask_app.route("/")(self.__client_frontend)
        self.__flask_app.route("/listen")(self.__client_listen)
        self.__flask_app.route("/continue")(self.__start)
        self.__flask_app.route("/pause")(self.__pause)
        self.__flask_app.route("/step")(self.__step)
        self.__flask_app.route("/settimeout/<timeout>")(self.__set_timeout)
        self.__flask_app.route("/getStateData/<data_type>/<state_id>")(self.__get_state_data)
        self.__flask_app.route("/breakpoints/add", methods=["POST"])(self.__add_breakpoint)
        self.__flask_app.route("/breakpoints/delete/<b_id>")(self.__delete_breakpoint)
        self.__flask_app.route("/breakpoints/get")(self.__get_breakpoint)
        self.__flask_app.route("/breakpoints/pause/<b_id>")(self.__pause_breakpoint)
        self.__flask_app.route("/breakpoints/unpause/<b_id>")(self.__unpause_breakpoint)
        self.__flask_app.route("/breakpoints/enableStopIfDifferent")(self.__enable_stop_if_different)
        self.__flask_app.route("/breakpoints/disableStopIfDifferent")(self.__disable_stop_if_different)
        self.__flask_app.route("/setParameter/<parameter>/<new_value>")(self.__set_parameter)
        self.__flask_app.route("/download/<file_type>")(self.__download_model)
        self.__flask_app.route("/upload", methods=["POST"])(self.__upload_model)

    def __create_queue_from_backup(self) -> Queue[Dict[str, Any]]:
        self.__backup_queue_lock.acquire()
        try:
            consumer_queue = Queue()
            to_re_add = []
            while not self.__backup_queue.empty():
                element = self.__backup_queue.get()
                to_re_add.append(element)
                consumer_queue.put(element)
            self.__consumer_queues.append(consumer_queue)
            for element_to_re_add in to_re_add:
                self.__backup_queue.put(element_to_re_add)
        finally:
            self.__backup_queue_lock.release()
        return consumer_queue

    def __listen_to_server(self) -> None:
        response = requests.get("http://127.0.0.1:5000/listen", stream=True, headers={'Accept': 'text/event-stream'})
        for line in response.iter_lines(1, decode_unicode=True):
            if line != "":
                json_data = json.loads(line.split("data: ")[1])
                if json_data["type"] == "trace":
                    self.__id_by_state[str(json_data["id"])] = json_data
                    self.__backup_queue_lock.acquire()
                    try:
                        self.__backup_queue.put(json_data)
                    finally:
                        self.__backup_queue_lock.release()
                else:
                    self.__running = not json_data["paused"]
                to_remove = []
                # fill consumer queues
                for consumer_queue in self.__consumer_queues:
                    # filter already full queues to be removed because not used anymore
                    if consumer_queue.full():
                        to_remove.append(consumer_queue)
                    else:
                        consumer_queue.put(json_data)
                # remove unused consumer queues
                for consumer_queue in to_remove:
                    self.__consumer_queues.remove(consumer_queue)

    def __client_listen(self) -> Response:
        queue = self.__create_queue_from_backup()

        def stream():
            yield _format_sse(
                json.dumps(
                    {
                        "type": "initial",
                        "timeout": self.__timeout,
                        "parameters": self.__initial_parameters,
                        "running": self.__running,
                    }
                )
            )
            while True:
                data = queue.get()
                if data["type"] == "trace":
                    final_data = {
                        "selected": data["selected"],
                        "parameters": data["parameters"],
                        "id": data["id"],
                        "type": data["type"],
                    }
                else:
                    final_data = data
                yield _format_sse(json.dumps(final_data))

        return Response(stream(), mimetype='text/event-stream', headers={"Access-Control-Allow-Origin": "*"})

    def __start(self) -> str:
        requests.get("http://127.0.0.1:5000/continue")
        self.__running = True
        return ""

    @staticmethod
    def __pause() -> str:
        requests.get("http://127.0.0.1:5000/pause")
        return ""

    @staticmethod
    def __step() -> str:
        requests.get("http://127.0.0.1:5000/step")
        return ""

    def __set_timeout(self, timeout: str) -> str:
        requests.get(f"http://127.0.0.1:5000/settimeout/{timeout}")
        self.__timeout = float(timeout)
        return ""

    def __get_state_data(self, data_type: str, state_id: str) -> Response:
        if data_type == "current":
            complete_state_data = self.__id_by_state[state_id]
        else:
            complete_state_data = self.__imported_id_by_state[state_id]
        return Response(
            json.dumps(complete_state_data["b_thread_info"]),
            headers={"Access-Control-Allow-Origin": "*"},
        )

    def __add_breakpoint(self) -> Response:
        json_breakpoint: dict = request.json
        self.__json_breakpoints[json_breakpoint["id"]] = json_breakpoint
        requests.post("http://127.0.0.1:5000/breakpoints/add", json=json_breakpoint)
        return Response("", headers={"Access-Control-Allow-Origin": "*"})

    def __delete_breakpoint(self, b_id: str) -> Response:
        self.__json_breakpoints.pop(b_id)
        requests.get(f"http://127.0.0.1:5000/breakpoints/delete/{b_id}")
        return Response("", headers={"Access-Control-Allow-Origin": "*"})

    def __get_breakpoint(self) -> Response:
        break_points = []
        for break_point in self.__json_breakpoints.values():
            break_points.append(break_point)
        return Response(json.dumps(break_points), headers={"Access-Control-Allow-Origin": "*"})

    def __pause_breakpoint(self, b_id: str) -> Response:
        self.__json_breakpoints[b_id]["paused"] = True
        requests.get(f"http://127.0.0.1:5000/breakpoints/delete/{b_id}")
        return Response("", headers={"Access-Control-Allow-Origin": "*"})

    def __unpause_breakpoint(self, b_id: str) -> Response:
        self.__json_breakpoints[b_id]["paused"] = False
        json_breakpoint = self.__json_breakpoints[b_id]
        requests.post("http://127.0.0.1:5000/breakpoints/add", json=json_breakpoint)
        return Response("", headers={"Access-Control-Allow-Origin": "*"})

    def __enable_stop_if_different(self) -> Response:
        current_position = 0
        if len(self.__id_by_state) > 0:
            current_position = int(list(self.__id_by_state.keys())[-1]) + 1
        json_breakpoint = {
            "id": "0",
            "current_position": current_position,
            "chain": [
                {
                    "name": "EVENT_SELECTED",
                    "value": data["selected"],
                    "kind": "flat",
                }
                for _, data in self.__imported_id_by_state.items()
            ]
        }
        requests.post("http://127.0.0.1:5000/breakpoints/add", json=json_breakpoint)
        return Response("", headers={"Access-Control-Allow-Origin": "*"})

    @staticmethod
    def __disable_stop_if_different() -> Response:
        requests.get(f"http://127.0.0.1:5000/breakpoints/delete/0")
        return Response("", headers={"Access-Control-Allow-Origin": "*"})

    @staticmethod
    def __set_parameter(parameter: str, new_value: str) -> Response:
        requests.get(f"http://127.0.0.1:5000/setParameter/{parameter}/{new_value}")
        return Response("", headers={"Access-Control-Allow-Origin": "*"})

    @staticmethod
    def __client_frontend() -> str:
        return render_template("index.html")

    def __download_model(self, file_type: str) -> Response:
        if file_type == "json":
            return Response(
                json.dumps(self.__id_by_state),
                headers={"Access-Control-Allow-Origin": "*"}
            )
        else:
            return Response(
                "",
                headers={"Access-Control-Allow-Origin": "*"}
            )

    def __upload_model(self) -> Response:
        self.__imported_id_by_state: Dict[int, Dict[str, Any]] = request.json
        payload = []
        for _, value in self.__imported_id_by_state.items():
            payload.append(
                {
                    "type": "trace",
                    "selected": value["selected"],
                    "id": value["id"],
                    "parameters": value["parameters"]
                }
            )
        return Response(
            json.dumps(payload),
            headers={"Access-Control-Allow-Origin": "*"}
        )

    def __connect_to_server(self) -> None:
        response = requests.get("http://127.0.0.1:5000/connect")
        self.__initial_parameters = response.json()

    def run(self, port: int) -> None:
        self.__connect_to_server()
        listener_thread = Thread(target=self.__listen_to_server)
        listener_thread.start()
        self.__flask_app.run(port=port)


if __name__ == "__main__":
    app = App()
    app.run(port=4000)
