"""Pytest fixture for creating a standard Home Assistant topology."""

from collections import namedtuple
import pytest

from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    label_registry as lr,
)
from homeassistant.setup import async_setup_component

Topology = namedtuple("Topology", ["device", "areas", "labels", "entities", "powerview_device"])
Areas = namedtuple("Areas", ["living_room", "kitchen"])
Labels = namedtuple("Labels", ["open", "partial", "closed", "auto"])
Entities = namedtuple(
    "Entities",
    [
        "scene_open",
        "scene_partial",
        "scene_closed",
        "switch_auto",
        "noise_scene_kitchen",
        "noise_scene_no_label",
        # input_booleans used as scene targets so we can verify activation
        "target_open",
        "target_partial",
        "target_closed",
        "target_noise_kitchen",
        "target_noise_no_label",
    ],
)


@pytest.fixture
async def hass_topology(hass, mock_zwave_config_entry, mock_powerview_config_entry):
    """Set up a standard entity topology for integration tests.

    Uses real HA components throughout so no service mocking is needed:
    - input_boolean entities are set up via async_setup_component so
      input_boolean.toggle actually flips their state.
    - scene entities are set up via async_setup_component so scene.turn_on
      actually activates them and changes their target entities' states.
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
    label_open = label_reg.async_create("Blinds Open")
    label_partial = label_reg.async_create("Blinds Partial")
    label_closed = label_reg.async_create("Blinds Closed")
    label_auto = label_reg.async_create("Automated Mode")
    labels = Labels(
        open=label_open.label_id,
        partial=label_partial.label_id,
        closed=label_closed.label_id,
        auto=label_auto.label_id,
    )
    # Scheduled event label IDs — assigned directly to entities (no label registry entry
    # needed because labels() template reads raw strings from entity registry)
    sched_label_open = "powerview.scheduledEvent_id.48860"
    sched_label_partial = "powerview.scheduledEvent_id.21095"
    sched_label_closed = "powerview.scheduledEvent_id.56009"

    # 3. Create ZEN35 Device in Living Room
    device = dev_reg.async_get_or_create(
        config_entry_id=mock_zwave_config_entry.entry_id,
        identifiers={("zwave_js", "zen35-node-5")},
        name="ZEN35 Switch",
    )
    device = dev_reg.async_update_device(device.id, area_id=areas.living_room.id)

    # PowerView hub device (configuration_url is used by blueprint to derive hub base URL)
    powerview_device = dev_reg.async_get_or_create(
        config_entry_id=mock_powerview_config_entry.entry_id,
        identifiers={("hunterdouglas_powerview", "00:26:74:60:31:FD")},
        name="PowerView Hub",
        configuration_url="http://192.168.4.22/api/shades",
    )

    # 4. Set up real input_boolean entities.
    #    Each scene targets one dedicated boolean so activating it changes
    #    observable state. Noise scenes get their own targets.
    await async_setup_component(
        hass,
        "input_boolean",
        {
            "input_boolean": {
                "living_room_blinds_central": {},
                "blinds_open_activated": {},
                "blinds_partial_activated": {},
                "blinds_closed_activated": {},
                "noise_kitchen_activated": {},
                "noise_unlabeled_activated": {},
            }
        },
    )
    await hass.async_block_till_done()

    # 5. Set up real scenes that target those input_booleans.
    #    When scene.turn_on is called the target boolean flips to "on".
    #    The "id" field gives each scene a unique_id so it is registered in
    #    the entity registry, which is required for label/area assignment.
    await async_setup_component(
        hass,
        "scene",
        {
            "scene": [
                {
                    "id": "lr_open",
                    "name": "Living Room Open",
                    "entities": {"input_boolean.blinds_open_activated": {"state": "on"}},
                },
                {
                    "id": "lr_partial",
                    "name": "Living Room Partial",
                    "entities": {"input_boolean.blinds_partial_activated": {"state": "on"}},
                },
                {
                    "id": "lr_closed",
                    "name": "Living Room Closed",
                    "entities": {"input_boolean.blinds_closed_activated": {"state": "on"}},
                },
                # Noise: same label as open but in Kitchen — must NOT be triggered by LR button
                {
                    "id": "kit_open",
                    "name": "Kitchen Open",
                    "entities": {"input_boolean.noise_kitchen_activated": {"state": "on"}},
                },
                # Noise: in Living Room but no label — must NOT be triggered
                {
                    "id": "lr_unlabeled",
                    "name": "Living Room Unlabeled",
                    "entities": {"input_boolean.noise_unlabeled_activated": {"state": "on"}},
                },
            ]
        },
    )
    await hass.async_block_till_done()

    # 6. Assign areas and labels via entity registry.
    scene_open_entry = ent_reg.async_get("scene.living_room_open")
    ent_reg.async_update_entity(
        scene_open_entry.entity_id,
        area_id=areas.living_room.id,
        labels={labels.open, sched_label_open},
    )

    scene_partial_entry = ent_reg.async_get("scene.living_room_partial")
    ent_reg.async_update_entity(
        scene_partial_entry.entity_id,
        area_id=areas.living_room.id,
        labels={labels.partial, sched_label_partial},
    )

    scene_closed_entry = ent_reg.async_get("scene.living_room_closed")
    ent_reg.async_update_entity(
        scene_closed_entry.entity_id,
        area_id=areas.living_room.id,
        labels={labels.closed, sched_label_closed},
    )

    noise_kitchen_entry = ent_reg.async_get("scene.kitchen_open")
    ent_reg.async_update_entity(
        noise_kitchen_entry.entity_id, area_id=areas.kitchen.id, labels={labels.open}
    )

    noise_no_label_entry = ent_reg.async_get("scene.living_room_unlabeled")
    ent_reg.async_update_entity(
        noise_no_label_entry.entity_id, area_id=areas.living_room.id
        # intentionally no label
    )

    switch_auto_entry = ent_reg.async_get("input_boolean.living_room_blinds_central")
    ent_reg.async_update_entity(
        switch_auto_entry.entity_id, area_id=areas.living_room.id, labels={labels.auto}
    )

    await hass.async_block_till_done()

    # Seed the PowerView scheduled events sensor (all enabled = opted in)
    hass.states.async_set(
        "sensor.powerview_scheduled_events",
        "3",
        {
            "scheduledEventData": [
                {"id": 48860, "enabled": True, "sceneId": 36156},
                {"id": 21095, "enabled": True, "sceneId": 16652},
                {"id": 56009, "enabled": True, "sceneId": 46041},
            ]
        },
    )

    return Topology(
        device=device,
        areas=areas,
        labels=labels,
        powerview_device=powerview_device,
        entities=Entities(
            scene_open=scene_open_entry.entity_id,
            scene_partial=scene_partial_entry.entity_id,
            scene_closed=scene_closed_entry.entity_id,
            switch_auto=switch_auto_entry.entity_id,
            noise_scene_kitchen=noise_kitchen_entry.entity_id,
            noise_scene_no_label=noise_no_label_entry.entity_id,
            target_open="input_boolean.blinds_open_activated",
            target_partial="input_boolean.blinds_partial_activated",
            target_closed="input_boolean.blinds_closed_activated",
            target_noise_kitchen="input_boolean.noise_kitchen_activated",
            target_noise_no_label="input_boolean.noise_unlabeled_activated",
        ),
    )
