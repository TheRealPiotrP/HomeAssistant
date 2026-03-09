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

| Parameter | Name                            | Size   | Default | Values                                                                                         |
|-----------|---------------------------------|--------|---------|-----------------------------------------------------------------------------------------------|
| 16        | Auto Turn-Off Timer             | 4 byte | 0       | 0 = disabled; 1–65535 minutes                                                                 |
| 17        | Auto Turn-On Timer              | 4 byte | 0       | 0 = disabled; 1–65535 minutes                                                                 |
| 18        | On/Off Status After Power Failure | 1 byte | 2     | 0 = always off; 1 = always on; 2 = remembers last status                                     |
| 19        | Load Control (Smart Bulb Mode)  | 1 byte | 1       | 0 = disable button; 1 = enable button + Z-Wave; 2 = disable both                             |
| 20        | Disabled Load Behavior          | 1 byte | 0       | 0 = reports status + changes LED; 1 = no reporting, no LED changes                           |
| 21        | Physical Ramp Rate ON           | 1 byte | 0       | 0 = instant; 1–99 seconds                                                                    |
| 22        | Physical Ramp Rate OFF          | 1 byte | 2       | 0 = instant; 1–99 seconds                                                                    |
| 23        | Physical Dimming Speed          | 1 byte | 5       | 1–99 seconds                                                                                  |
| 24        | Z-Wave Ramp Rate ON             | 1 byte | 255     | 0–99 seconds; 255 = match parameter 21                                                        |
| 25        | Z-Wave Ramp Rate OFF            | 1 byte | 255     | 0–99 seconds; 255 = match parameter 22                                                        |
| 26        | Remote Z-Wave Dimming Duration  | 1 byte | 5       | 1–99 seconds                                                                                  |
| 27        | Minimum Brightness              | 1 byte | 1       | 1–99 percent                                                                                  |
| 28        | Maximum Brightness              | 1 byte | 99      | 1–99 percent                                                                                  |
| 29        | Dimmer Button Double Tap        | 1 byte | 0       | 0 = full brightness; 1 = custom brightness; 2 = max brightness; 3 = disabled                 |
| 30        | Dimmer Button Single Tap        | 1 byte | 0       | 0 = last level; 1 = custom brightness; 2 = max brightness; 3 = full brightness               |
| 31        | Physical Custom Brightness On   | 1 byte | 0       | 0 = last level; 1–99 percent                                                                  |
| 32        | 3-Way Switch Type               | 1 byte | 0       | 0 = toggle; 1 = toggle with dimming; 2 = momentary (ZAC99); 3 = momentary with smart sequence |
| 33        | Multilevel Dimming Reports      | 1 byte | 2       | 0–2 (reporting behavior variants)                                                             |
| 34        | Disable Button Programming      | 1 byte | 0       | 0 = enabled; 1 = disabled                                                                    |
| 35        | Association Reports             | 1 byte | 15      | 0–15 (combinatorial: physical / Z-Wave / timer triggers)                                      |
| 36        | Dimmer Button Scene Control     | 1 byte | 1       | 0 = disabled; 1 = enabled                                                                    |
| 37        | Scene Control From 3-Way Switch | 1 byte | 0       | 0 = disabled; 1 = enabled                                                                    |
| 38        | Disable LED Flash On Setting Change | 1 byte | 0   | 0 = flashes; 1 = no flash                                                                    |
| 39        | Disable LED Flash On Button Press | 1 byte | 0     | 0 = flashes; 1 = no flash                                                                    |
| 40        | On/Off Switch Mode              | 1 byte | 0       | 0 = disabled; 1 = enabled                                                                    |
| 41        | Basic Set Custom Brightness On  | 1 byte | 0       | 0 = last level; 1–99 percent                                                                  |
| 42        | Scene Control Multi-Tap         | 1 byte | 0       | 0 = enabled; 1 = disabled                                                                    |
| 43        | Gamma Factor                    | 1 byte | —       | 10–50 (represents 1.0–5.0)                                                                   |
