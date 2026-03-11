"""Simulated hardware for ZEN35 PowerView blueprint tests.

Each simulation registers real HA services or runs a real HTTP server so the
blueprint's full call path is exercised. Tests then assert on the simulation's
state rather than on mock call arguments.

To validate against real hardware:
  SimulatedZEN35  — compare parameter numbers, value ranges, and service schema
                    with the ZEN35 Z-Wave configuration parameter table.
  SimulatedPowerViewHub — compare each endpoint's request/response shape with a
                    live hub (Gen 2 API).
"""
from __future__ import annotations

import logging

from aiohttp import web
from homeassistant.core import HomeAssistant, ServiceCall

_LOGGER = logging.getLogger(__name__)


class SimulatedZEN35:
    """Simulates the LED config state of a ZEN35 switch.

    Registers a real ``zwave_js.set_config_parameter`` HA service so the
    blueprint's service calls go through HA's full service dispatch pipeline.
    State is stored per (device_id, parameter) and can be queried directly.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        # {(device_id, param): latest_value}
        self._state: dict[tuple[str | None, int], int] = {}
        # ordered log of all calls: [(device_id, param, value), ...]
        self._history: list[tuple[str | None, int, int]] = []
        hass.services.async_register(
            "zwave_js", "set_config_parameter", self._handle
        )

    async def _handle(self, call: ServiceCall) -> None:
        # HA merges the `target` dict into `call.data` before dispatch,
        # so device_id is accessible directly here.
        device_id = call.data.get("device_id")
        param = int(call.data["parameter"])
        value = int(call.data["value"])
        self._state[(device_id, param)] = value
        self._history.append((device_id, param, value))

    def get_param(self, device_id: str | None, param: int) -> int | None:
        """Current value of a config parameter, or None if never set."""
        return self._state.get((device_id, param))

    def param_history(self, device_id: str | None, param: int) -> list[int]:
        """All values set for a parameter in order.

        Useful for confirm-mode tests that verify ON then OFF:
            assert sim.param_history(dev_id, LED1_MODE) == [LEDState.ON, LEDState.OFF]
        """
        return [v for (d, p, v) in self._history if d == device_id and p == param]

    @property
    def total_calls(self) -> int:
        """Total set_config_parameter calls across all devices and parameters."""
        return len(self._history)


class SimulatedPowerViewHub:
    """Simulates a Hunter Douglas PowerView Gen 2 hub REST API.

    Runs a real aiohttp HTTP server on 127.0.0.1 (allowed by pytest-socket).
    The real ``hunterdouglas_powerview`` integration, ``rest_command``, and the
    ``rest`` sensor platform all hit real HTTP, so the full request/response
    stack is exercised. Tests inspect hub state directly.
    """

    # Scene IDs for the three controllable scenes (Living Room)
    SCENE_ID_OPEN    = 36156
    SCENE_ID_PARTIAL = 16652
    SCENE_ID_CLOSED  = 46041
    # Scene IDs for noise/isolation scenes
    SCENE_ID_KITCHEN_OPEN     = 99001  # right label, wrong area
    SCENE_ID_LR_UNLABELED     = 99002  # right area, no label

    INITIAL_EVENTS: list[dict] = [
        {"id": 48860, "enabled": True, "sceneId": SCENE_ID_OPEN},
        {"id": 21095, "enabled": True, "sceneId": SCENE_ID_PARTIAL},
        {"id": 56009, "enabled": True, "sceneId": SCENE_ID_CLOSED},
    ]
    INITIAL_ROOMS: list[dict] = [
        {"id": 1, "name": "Living Room", "colorId": 0, "iconId": 0},
        {"id": 2, "name": "Kitchen",     "colorId": 0, "iconId": 0},
    ]
    INITIAL_SCENES: list[dict] = [
        {"id": SCENE_ID_OPEN,         "roomId": 1, "name": "Open"},
        {"id": SCENE_ID_PARTIAL,      "roomId": 1, "name": "Partial"},
        {"id": SCENE_ID_CLOSED,       "roomId": 1, "name": "Closed"},
        {"id": SCENE_ID_KITCHEN_OPEN, "roomId": 2, "name": "Kitchen Open"},
        {"id": SCENE_ID_LR_UNLABELED, "roomId": 1, "name": "Living Room Unlabeled"},
    ]

    def __init__(self, events: list[dict] | None = None) -> None:
        self._runner: web.AppRunner | None = None
        self._url: str | None = None
        self.seed_events(events if events is not None else self.INITIAL_EVENTS)
        self._rooms  = {r["id"]: dict(r) for r in self.INITIAL_ROOMS}
        self._scenes = {s["id"]: dict(s) for s in self.INITIAL_SCENES}
        self._shades: dict[int, dict] = {}
        self._activated_scenes: list[int] = []

    def seed_events(self, events: list[dict]) -> None:
        """Set scheduled event state. Each dict: {id, enabled, sceneId}."""
        self._events = {int(e["id"]): dict(e) for e in events}

    def scene_was_activated(self, scene_id: int) -> bool:
        """Return True if scene.turn_on was called for this scene ID."""
        return scene_id in self._activated_scenes

    @property
    def url(self) -> str:
        assert self._url is not None, "Hub not started — call await hub.start() first"
        return self._url

    def get_event(self, event_id: int) -> dict | None:
        """Current state dict for a scheduled event, or None if unknown."""
        return self._events.get(event_id)

    async def start(self) -> None:
        """Start the HTTP server on a random free port on 127.0.0.1."""
        app = web.Application()
        app.router.add_get("/api/userdata",        self._handle_userdata)
        app.router.add_get("/api/fwversion",       self._handle_fwversion)
        app.router.add_get("/api/rooms",           self._handle_rooms)
        app.router.add_get("/api/scenes",          self._handle_scenes)
        app.router.add_get("/api/shades",          self._handle_shades)
        app.router.add_get("/api/scheduledEvents", self._handle_scheduled_events_get)
        app.router.add_put("/api/scheduledEvents/{id}", self._handle_scheduled_events_put)
        app.router.add_route("*", "/{path_info:.*}", self._handle_unrecognized)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        self._url = f"http://127.0.0.1:{port}"

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()

    async def _handle_userdata(self, request: web.Request) -> web.Response:
        return web.json_response({
            "userData": {"serialNumber": "SIMHUB001", "macAddress": "00:11:22:33:44:55"},
            "firmware": {"mainProcessor": {"revision": "1", "subRevision": "0", "build": 0}},
        })

    async def _handle_fwversion(self, request: web.Request) -> web.Response:
        return web.json_response({
            "firmware": {"mainProcessor": {"revision": "1", "subRevision": "0", "build": 0}}
        })

    async def _handle_rooms(self, request: web.Request) -> web.Response:
        return web.json_response({"roomData": list(self._rooms.values())})

    async def _handle_scenes(self, request: web.Request) -> web.Response:
        # Gen 2 scene activation: GET /api/scenes?sceneId={id}
        scene_id = request.rel_url.query.get("sceneId")
        if scene_id is not None:
            sid = int(scene_id)
            self._activated_scenes.append(sid)
            return web.json_response({"scene": self._scenes.get(sid, {})})
        return web.json_response({"sceneData": list(self._scenes.values())})

    async def _handle_shades(self, request: web.Request) -> web.Response:
        return web.json_response({"shadeData": list(self._shades.values())})

    async def _handle_scheduled_events_get(self, request: web.Request) -> web.Response:
        return web.json_response({"scheduledEventData": list(self._events.values())})

    async def _handle_scheduled_events_put(self, request: web.Request) -> web.Response:
        event_id = int(request.match_info["id"])
        body = await request.json()
        enabled = body.get("scheduledEvent", {}).get("enabled", False)
        if event_id in self._events:
            self._events[event_id] = {**self._events[event_id], "enabled": enabled}
        return web.json_response({"scheduledEvent": self._events.get(event_id, {})})

    async def _handle_unrecognized(self, request: web.Request) -> web.Response:
        body = await request.text()
        _LOGGER.warning(
            "SimulatedPowerViewHub: unhandled %s %s — body: %s",
            request.method, request.path, body or "(empty)",
        )
        return web.json_response({})
