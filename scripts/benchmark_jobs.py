from __future__ import annotations

import argparse
import io
import time

import requests
from PIL import Image, ImageDraw


def make_image() -> bytes:
    img = Image.new('RGB', (256, 256), 'white')
    draw = ImageDraw.Draw(img)
    draw.rectangle((40, 40, 220, 220), fill='green')
    out = io.BytesIO()
    img.save(out, format='PNG')
    return out.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--count', type=int, default=10)
    args = parser.parse_args()

    image = make_image()
    started = time.time()

    for _ in range(args.count):
        resp = requests.post(
            f"{args.url}/api/jobs/remove-bg",
            files={'file': ('bench.png', image, 'image/png')},
            data={'feather_radius': '0', 'alpha_boost': '1'},
            timeout=30,
        )
        resp.raise_for_status()

    elapsed = time.time() - started
    print({'submitted': args.count, 'elapsed_sec': round(elapsed, 2), 'rps': round(args.count / elapsed, 2)})


if __name__ == '__main__':
    main()
