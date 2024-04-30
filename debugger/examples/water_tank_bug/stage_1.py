import time
from typing import Dict, Callable

from bppy import *

from debugger.server.listener import MonitoringListener


class TARGET:
    TEMP = 20
    LEVEL = 50


class WaterTank:
    def __init__(self) -> None:
        self.water_level = 0
        self.water_temperature = 0

    def add_water(self, amount: int, temperature: int) -> None:
        if amount == 0:
            return
        new_temperature = (self.water_level * self.water_temperature + amount * temperature) / \
                          (self.water_level + amount)
        self.water_level += amount
        self.water_temperature = new_temperature

    def remove_water(self, amount: int) -> None:
        if self.water_level >= amount:
            self.water_level -= amount


def set_temp(temp: int) -> None:
    TARGET.TEMP = temp


def set_level(level: int) -> None:
    TARGET.LEVEL = level


class WaterTankListener(BProgramRunnerListener):
    def __init__(self, water_tank: WaterTank) -> None:
        self.__water_tank = water_tank
        self.__water_level = TARGET.LEVEL
        self.__water_temp = TARGET.TEMP

    def starting(self, b_program):
        pass

    def started(self, b_program):
        pass

    def super_step_done(self, b_program):
        pass

    def ended(self, b_program):
        pass

    def assertion_failed(self, b_program):
        pass

    def b_thread_added(self, b_program):
        pass

    def b_thread_removed(self, b_program):
        pass

    def b_thread_done(self, b_program):
        pass

    def halted(self, b_program):
        pass

    def event_selected(self, b_program: BProgram, event: BEvent):
        if event == BEvent("FINISHED"):
            time.sleep(1)
        else:
            if event == BEvent("HOT"):
                self.__water_tank.add_water(1, 80)
            elif event == BEvent("COLD"):
                self.__water_tank.add_water(1, 0)
            elif event == BEvent("DRAIN"):
                self.__water_tank.remove_water(1)
            # print(f"{self.__water_tank.water_level} L, {self.__water_tank.water_temperature} °C", {event.name})


TANK = WaterTank()


@thread
def add_hot():
    while True:
        yield sync(request=BEvent("HOT"))


@thread
def add_cold():
    while True:
        yield sync(request=BEvent("COLD"))


@thread
def remove_water():
    while True:
        yield sync(request=BEvent("DRAIN"))


@thread
def control_temp():
    while True:
        if TARGET.TEMP - 0.1 < TANK.water_temperature < TARGET.TEMP + 0.1:
            yield sync(
                waitFor=All(),
                block=All(),
            )
        elif TANK.water_temperature < TARGET.TEMP:
            yield sync(
                waitFor=All(),
                block=BEvent("COLD"),
            )
        elif TANK.water_temperature >= TARGET.TEMP:
            yield sync(
                waitFor=All(),
                block=BEvent("HOT"),
            )


if __name__ == "__main__":
    def poll_tank_data() -> Dict[str, Dict[str, str | int | bool | Callable]]:
        return {
            "TargetLevel": {"value": TARGET.LEVEL, "editable": True, "unit": "l", "callback": set_level},
            "TargetTemperature": {"value": TARGET.TEMP, "editable": True, "unit": "°C", "callback": set_temp},
            "Level": {"value": round(TANK.water_level, ndigits=3), "editable": False, "unit": "l"},
            "Temperature": {"value": round(TANK.water_temperature, ndigits=3), "editable": False, "unit": "°C"},
        }

    listener = MonitoringListener(WaterTankListener(TANK), "example")
    listener.register_data_poll(poll_tank_data)
    b_program = BProgram(
        bthreads=[
            listener.mark_name("ControlTemp", control_temp()),
            listener.mark_name("AddHot", add_hot()),
            listener.mark_name("AddCold", add_cold()),
            listener.mark_name("RemoveWater", remove_water()),
        ],
        event_selection_strategy=PriorityBasedEventSelectionStrategy(),
        listener=listener
    )
    b_program.run()

# debugging
# temporal runtime models
# eclipse hawk
# beispiel erweitern, objekte einbauen
# trace analysis
