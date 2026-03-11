"""Pytest fixture for creating a standard Home Assistant topology."""

from collections import namedtuple
import pytest

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_API_VERSION
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    label_registry as lr,
)
from homeassistant.setup import async_setup_component

from .simulations import SimulatedPowerViewHub

Topology = namedtuple("Topology", ["zen35_device", "areas", "labels", "entities"])
Areas = namedtuple("Areas", ["living_room", "kitchen"])
Labels = namedtuple("Labels", ["open", "partial", "closed"])
Entities = namedtuple(
    "Entities",
    [
        "scene_open",
        "scene_partial",
        "scene_closed",
        "noise_scene_kitchen",
        "noise_scene_no_label",
    ],
)


@pytest.fixture
async def hass_topology(hass, mock_zwave_config_entry, sim_powerview_hub):
    """Set up a standard entity topology for integration tests.

    Uses real HA components throughout:
    - The real ``hunterdouglas_powerview`` integration is loaded against the
      SimulatedPowerViewHub, creating real scene entities. Activating them makes
      actual HTTP calls to the sim hub, which records the activation.
    - input_boolean.living_room_blinds_central is used by button 4 (central control).
    - rest_command.powerview_set_scheduled_event makes actual HTTP PUT calls to the sim hub.
    - sensor.powerview_scheduled_events is a real REST sensor polling the hub.
    - "Noise" entities (wrong area, or no label) verify discovery is precise.
    """
    area_reg = ar.async_get(hass)
    label_reg = lr.async_get(hass)
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    # 1. Create Areas
    area_living_room = area_reg.async_create("Living Room")
    area_kitchen = area_reg.async_create("Kitchen")
    areas = Areas(living_room=area_living_room, kitchen=area_kitchen)

    # 2. Create Labels
    label_open    = label_reg.async_create("Blinds Open")
    label_partial = label_reg.async_create("Blinds Partial")
    label_closed  = label_reg.async_create("Blinds Closed")
    labels = Labels(
        open=label_open.label_id,
        partial=label_partial.label_id,
        closed=label_closed.label_id,
    )
    # Scheduled event label IDs — assigned directly to entities (no label registry entry
    # needed because labels() template reads raw strings from entity registry)
    sched_label_open    = "powerview.scheduledEvent_id.48860"
    sched_label_partial = "powerview.scheduledEvent_id.21095"
    sched_label_closed  = "powerview.scheduledEvent_id.56009"

    # 3. Create ZEN35 Device in Living Room
    device = dev_reg.async_get_or_create(
        config_entry_id=mock_zwave_config_entry.entry_id,
        identifiers={("zwave_js", "zen35-node-5")},
        name="ZEN35 Switch",
    )
    device = dev_reg.async_update_device(device.id, area_id=areas.living_room.id)

    # 4. Set up homeassistant integration (provides update_entity service) and the REST sensor
    #    before loading the PowerView integration.
    #    Once hunterdouglas_powerview loads it also sets up the sensor component,
    #    which means a subsequent async_setup_component(hass, "sensor", ...) would be
    #    a no-op. We must load the REST sensor first so it actually gets registered.
    await async_setup_component(hass, "homeassistant", {})
    await hass.async_block_till_done()

    assert await async_setup_component(
        hass,
        "sensor",
        {
            "sensor": [
                {
                    "platform": "rest",
                    "resource": f"{sim_powerview_hub.url}/api/scheduledEvents",
                    "name": "powerview_scheduled_events",
                    "scan_interval": 300,
                    "value_template": "{{ value_json.scheduledEventData | length }}",
                    "json_attributes": ["scheduledEventData"],
                }
            ]
        },
    ), "REST sensor setup failed — is the sim hub running?"
    await hass.async_block_till_done()  # ensure entity is registered before polling
    # Force an immediate poll so sensor attributes are populated before any test runs.
    await hass.services.async_call(
        "homeassistant", "update_entity",
        {"entity_id": "sensor.powerview_scheduled_events"},
        blocking=True,
    )

    # 6. Load the real Hunter Douglas PowerView integration against the sim hub.
    #    This creates real scene entities (scene.open, scene.partial, etc.) backed
    #    by actual HTTP calls to SimulatedPowerViewHub.
    pv_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain="hunterdouglas_powerview",
        title="PowerView Hub",
        data={CONF_HOST: sim_powerview_hub.url.removeprefix("http://"), CONF_API_VERSION: 2},
        options={},
        entry_id="test-powerview",
        state=ConfigEntryState.NOT_LOADED,
        source="user",
        unique_id="SIMHUB001",
        discovery_keys=set(),
        subentries_data={},
    )
    hass.config_entries._entries[pv_entry.entry_id] = pv_entry
    await hass.config_entries.async_setup(pv_entry.entry_id)
    await hass.async_block_till_done()

    # Retrieve the hub device created by the integration and set configuration_url
    # so the blueprint can extract the hub base URL via device_attr(..., 'configuration_url').
    powerview_device = dev_reg.async_get_device(
        identifiers={("hunterdouglas_powerview", "SIMHUB001")}
    )
    dev_reg.async_update_device(
        powerview_device.id,
        configuration_url=f"{sim_powerview_hub.url}/api/shades",
    )
    powerview_device = dev_reg.async_get_device(
        identifiers={("hunterdouglas_powerview", "SIMHUB001")}
    )

    # 7. Assign areas and labels to the PowerView scene entities.
    scene_open_entry    = ent_reg.async_get("scene.open")
    scene_partial_entry = ent_reg.async_get("scene.partial")
    scene_closed_entry  = ent_reg.async_get("scene.closed")
    noise_kitchen_entry = ent_reg.async_get("scene.kitchen_open")
    noise_no_label_entry = ent_reg.async_get("scene.living_room_unlabeled")

    ent_reg.async_update_entity(
        scene_open_entry.entity_id,
        area_id=areas.living_room.id,
        labels={labels.open, sched_label_open},
    )
    ent_reg.async_update_entity(
        scene_partial_entry.entity_id,
        area_id=areas.living_room.id,
        labels={labels.partial, sched_label_partial},
    )
    ent_reg.async_update_entity(
        scene_closed_entry.entity_id,
        area_id=areas.living_room.id,
        labels={labels.closed, sched_label_closed},
    )
    ent_reg.async_update_entity(
        noise_kitchen_entry.entity_id,
        area_id=areas.kitchen.id,
        labels={labels.open},
    )
    ent_reg.async_update_entity(
        noise_no_label_entry.entity_id,
        area_id=areas.living_room.id,
        # intentionally no label
    )
    await hass.async_block_till_done()

    # 9. Set up real rest_command for PowerView scheduled event control.
    await async_setup_component(
        hass,
        "rest_command",
        {
            "rest_command": {
                "powerview_set_scheduled_event": {
                    "url": "{{ hub }}/api/scheduledEvents/{{ id }}",
                    "method": "PUT",
                    "content_type": "application/json",
                    "payload": '{"scheduledEvent": {"enabled": {{ enabled }}}}',
                }
            }
        },
    )
    await hass.async_block_till_done()

    return Topology(
        zen35_device=device,
        areas=areas,
        labels=labels,
        entities=Entities(
            scene_open=scene_open_entry.entity_id,
            scene_partial=scene_partial_entry.entity_id,
            scene_closed=scene_closed_entry.entity_id,
            noise_scene_kitchen=noise_kitchen_entry.entity_id,
            noise_scene_no_label=noise_no_label_entry.entity_id,
        ),
    )
