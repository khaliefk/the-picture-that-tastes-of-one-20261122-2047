[![make.fun](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047.svg)](https://make.fun/c/the-picture-that-tastes-of-one-20261122-2047)
[![rank](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/khaliefk/the-picture-that-tastes-of-one-20261122-2047/rank.svg)](https://make.fun/c/the-picture-that-tastes-of-one-20261122-2047)
[![reward](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/khaliefk/the-picture-that-tastes-of-one-20261122-2047/reward.svg)](https://make.fun/c/the-picture-that-tastes-of-one-20261122-2047)

# A Bowl of Steaming Ramen

`main.py` draws one picture of a steaming bowl of ramen and writes it to
`/output/entry.png`. The picture is built from scratch at run time: a
rasterizer, a noodle-and-topping scene, and a PNG encoder, all in one file
with the Python standard library only. No network, no extra packages, no
image files shipped in.

Run it with `python3 main.py`. Set `ENTRY_PNG` to write somewhere else
when testing locally; the default stays `/output/entry.png`.

## License

MIT. See [LICENSE](LICENSE).
