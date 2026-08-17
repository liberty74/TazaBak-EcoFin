"""Safe procedural SVG generation for Eco-NFTs."""

from __future__ import annotations

import hashlib
from html import escape


PALETTES = (
    ("#E8F7EE", "#1B8A5A", "#0D5B3B", "#F4C95D"),
    ("#E6F4FF", "#247BA0", "#16506B", "#70C1B3"),
    ("#FFF4D6", "#D99000", "#7A5100", "#73A942"),
    ("#F2E9FF", "#7551A8", "#442B70", "#7BC8A4"),
)


def generate_nft_svg(nft_id: int, token_id: str, title: str) -> str:
    """Generate deterministic, script-free SVG from server-owned values."""

    digest = hashlib.sha256(f"{nft_id}:{token_id}".encode("utf-8")).digest()
    background, leaf, dark, accent = PALETTES[digest[0] % len(PALETTES)]
    safe_title = escape(title[:64], quote=True)

    pattern_elements: list[str] = []
    for index in range(16):
        x = 18 + digest[(index + 1) % len(digest)] % 284
        y = 18 + digest[(index + 9) % len(digest)] % 244
        radius = 2 + digest[(index + 17) % len(digest)] % 7
        opacity = 0.18 + (digest[(index + 23) % len(digest)] % 40) / 100
        pattern_elements.append(
            f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{accent}" '
            f'opacity="{opacity:.2f}"/>'
        )

    bend = 18 + digest[4] % 34
    leaf_path = (
        f"M160 214 C{88 - bend} 164,{92 + bend} 72,160 44 "
        f"C{228 - bend} 72,{232 + bend} 164,160 214 Z"
    )
    veins = "".join(
        f'<path d="M160 {190 - step * 18} L{118 - step * 2} {150 - step * 15}"/>'
        f'<path d="M160 {190 - step * 18} L{202 + step * 2} {150 - step * 15}"/>'
        for step in range(4)
    )
    short_hash = hashlib.sha256(token_id.encode("ascii")).hexdigest()[:12].upper()

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 320" '
        'role="img" aria-label="Eco NFT">'
        f'<rect width="320" height="320" rx="32" fill="{background}"/>'
        + "".join(pattern_elements)
        + f'<path d="{leaf_path}" fill="{leaf}" stroke="{dark}" stroke-width="5"/>'
        + f'<g fill="none" stroke="{dark}" stroke-width="4" stroke-linecap="round">'
        + '<path d="M160 224 L160 88"/>'
        + veins
        + "</g>"
        + f'<rect x="42" y="254" width="236" height="44" rx="16" fill="{dark}"/>'
        + f'<text x="160" y="274" text-anchor="middle" fill="#fff" '
        + f'font-family="Arial,sans-serif" font-size="14" font-weight="700">{safe_title}</text>'
        + f'<text x="160" y="290" text-anchor="middle" fill="#fff" opacity=".75" '
        + f'font-family="monospace" font-size="10">#{nft_id} · {short_hash}</text>'
        + "</svg>"
    )

