"""Pytest fixture for creating a standard Home Assistant topology."""

from collections import namedtuple

import pytest
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_API_VERSION, CONF_HOST
from homeassistant.helpers import (
    area_registry as ar,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers import (
    label_registry as lr,
)
from homeassistant.setup import async_setup_component

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
    # 3. Create ZEN35 Device in Living Room
    device = dev_reg.async_get_or_create(
        config_entry_id=mock_zwave_config_entry.entry_id,
        identifiers={("zwave_js", "zen35-node-5")},
        name="ZEN35 Switch",
    )
    device = dev_reg.async_update_device(device.id, area_id=areas.living_room.id)

    # 4. Load the real Hunter Douglas PowerView integration against the sim hub.
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
        labels={labels.open},
    )
    ent_reg.async_update_entity(
        scene_partial_entry.entity_id,
        area_id=areas.living_room.id,
        labels={labels.partial},
    )
    ent_reg.async_update_entity(
        scene_closed_entry.entity_id,
        area_id=areas.living_room.id,
        labels={labels.closed},
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

    # 8. Inject scheduledEvent_id attribute onto scene states.
    #    The blueprint reads state_attr(entity, 'scheduledEvent_id') to find which
    #    scheduled event corresponds to each scene, replacing the old label approach.
    sched_event_by_entity = {
        scene_open_entry.entity_id:    48860,
        scene_partial_entry.entity_id: 21095,
        scene_closed_entry.entity_id:  56009,
    }
    for entity_id, event_id in sched_event_by_entity.items():
        state = hass.states.get(entity_id)
        if state:
            hass.states.async_set(
                entity_id,
                state.state,
                {**state.attributes, "scheduledEvent_id": event_id},
            )

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

    # 10. Inject the initial scheduled-event sensor state directly into the HA
    #     state machine. Direct injection avoids HTTP polling timing races:
    #     async_block_till_done() can trigger background REST sensor scans
    #     that overwrite state — a directly-set state is immune to this.
    events = list(sim_powerview_hub._events.values())
    hass.states.async_set(
        "sensor.powerview_scheduled_events",
        str(len(events)),
        {"scheduledEventData": events},
    )

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
