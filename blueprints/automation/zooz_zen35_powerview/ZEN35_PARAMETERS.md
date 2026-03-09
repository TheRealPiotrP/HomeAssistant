# ZEN35 Z-Wave Configuration Parameters

Source: https://thesmartesthouse.happyfox.com/kb/article/1673-zen35-scene-dimmer-advanced-settings/

## LED Parameters

### Mode (when does the LED light up?)

| Parameter | Button        | Default |
|-----------|---------------|---------|
| 1         | Dimmer button | 0       |
| 2         | Button 1      | 0       |
| 3         | Button 2      | 0       |
| 4         | Button 3      | 0       |
| 5         | Button 4      | 0       |

Values:
- `0` — on when load/button is **off** (default indicator behavior)
- `1` — on when load/button is **on**
- `2` — **always off**
- `3` — **always on**

### Color

| Parameter | Button        | Default    |
|-----------|---------------|------------|
| 6         | Dimmer button | 0 (white)  |
| 7         | Button 1      | 0 (white)  |
| 8         | Button 2      | 0 (white)  |
| 9         | Button 3      | 0 (white)  |
| 10        | Button 4      | 0 (white)  |

Values:
- `0` — white
- `1` — blue
- `2` — green
- `3` — red
- `4` — magenta
- `5` — yellow
- `6` — cyan

### Brightness

| Parameter | Button        | Default       |
|-----------|---------------|---------------|
| 11        | Dimmer button | 1 (medium)    |
| 12        | Button 1      | 1 (medium)    |
| 13        | Button 2      | 1 (medium)    |
| 14        | Button 3      | 1 (medium)    |
| 15        | Button 4      | 1 (medium)    |

Values:
- `0` — bright (100%)
- `1` — medium (60%) ← default
- `2` — low (30%)

## Other Parameters

| Parameter | Name                        | Size   | Default | Values                                                                          |
|-----------|-----------------------------|--------|---------|---------------------------------------------------------------------------------|
| 16        | Auto Turn-Off Timer         | 4 byte | 0       | 0 = disabled, 1–65535 minutes                                                   |
| 17        | Auto Turn-On Timer          | 4 byte | 0       | 0 = disabled, 1–65535 minutes                                                   |
| 18        | Power Failure Behavior      | 1 byte | 2       | 0 = off, 1 = on, 2 = restore last state                                         |
| 19        | Load Control                | 1 byte | 1       | 0 = disabled, 1 = enabled, 2 = enabled (no physical control)                   |
| 21–23     | Ramp rates / dimming speeds | 1 byte | —       | Various                                                                         |
| 27–28     | Brightness limits           | 1 byte | —       | 1–99%                                                                           |
| 29–30     | Double/Single tap behavior  | 1 byte | —       | 0–3                                                                             |
| 31        | Physical Custom Brightness  | 1 byte | 0       | 0 = last level, 1–99 (%)                                                        |
| 32        | 3-Way Switch Type           | 1 byte | 0       | 0 = toggle, 1 = toggle+dim, 2 = momentary (ZAC99), 3 = momentary+smart sequence |
| 35        | Association Reports         | 1 byte | 15      | 0–15 (bitmask)                                                                  |
| 36        | Scene Control               | 1 byte | 1       | 0 = disabled, 1 = enabled                                                      |
| 40        | On/Off Switch Mode          | 1 byte | 0       | 0 = normal, 1 = on/off only                                                     |
| 42        | Multi-Tap Scene Control     | 1 byte | 0       | 0 = disabled, 1 = enabled                                                       |
