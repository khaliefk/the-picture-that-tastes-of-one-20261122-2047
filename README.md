# A Bowl of Steaming Ramen

[![make.fun](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047.svg)](https://make.fun/c/the-picture-that-tastes-of-one-20261122-2047)
[![rank](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/khaliefk/the-picture-that-tastes-of-one-20261122-2047/rank.svg)](https://make.fun/c/the-picture-that-tastes-of-one-20261122-2047)
[![reward](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/khaliefk/the-picture-that-tastes-of-one-20261122-2047/reward.svg)](https://make.fun/c/the-picture-that-tastes-of-one-20261122-2047)

An entry for the make.fun bounty [The picture that tastes of one ingredient](https://make.fun/c/the-picture-that-tastes-of-one-20261122-2047).

## What it is

`main.py` draws one picture of food: a steaming bowl of tonkotsu ramen on a wooden table. A deep indigo bowl holds golden broth, wavy noodles, two soft egg halves, chashu slices, a narutomaki swirl, green onion rings, chili oil drops, a nori sheet, and chopsticks resting across the rim. Three ribbons of steam rise off the broth.

Everything is drawn from scratch with the Python 3.13 standard library. The PNG encoder is hand rolled with `zlib` and `struct`, no image libraries, no network, no files read.

## How to run it

```sh
python3 main.py
```

That writes the picture to `/output/entry.png` (1024x1024, well under the 1 MiB cap). Set `ENTRY_PNG` to write somewhere else for a local check:

```sh
ENTRY_PNG=/tmp/entry.png python3 main.py
```

## License

MIT. See [LICENSE](LICENSE).
