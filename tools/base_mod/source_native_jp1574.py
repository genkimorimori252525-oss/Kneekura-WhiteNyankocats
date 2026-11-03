"""Exact metadata for the owner-acquired JP15.7.4 AArch64 native image.

This profile does not establish gameplay parity. Full mapped source hashes
remain mandatory after restoring the explicitly permitted package/adapters.
Only metadata and the small displaced/safety instruction anchors are stored.
"""

NATIVE_SHA256 = "669438f86b41c10c7a387b96eb1ab5ca82a350bacc89ec06c05f699ec3727590"
BUILD_ID = "aeb33598e519122c791cb837c257016e697d9149"
DRAW_VMA = 0x3184BC
TEXT_START = 0x3182D0
TEXT_END = 0xADAEA4
TEXT_SHA256 = "718599f2094c548935eba61d05b94c911e13e101aebe84c6f3eaf9910cb68b27"
PINNED_MAPPED_RANGES = {
    "gnu_note": (0x2D0, 0x24, "9c6c07c593ee1602ec653d37ebfbc1b8f29caa9495f30d16c405e7782db98753"),
    "rodata": (0x18F900, 0x6E9A4, "c0495e77e7b1b84efca43c7c98bb9c5be9901552049fe91c6c82a895468b6132"),
    "eh_frame": (0x22B4F8, 0xECDD4, "58ae5134d7d59b7d37f92872dfc7df6afed814f75f9edf0e4230f65b023ac02b"),
    "lcxx_override": (0xADAEA4, 0x10C, "8a91c97750953cc8fa8077c1fa5f9322723111aec3896c27c96252a99c2bf9a4"),
    "plt": (0xADAFB0, 0x7020, "79182e60cd7fc274deea8ace802ba604d234ce957190c3e6bfab3cba84e0f272"),
}
SCENE_ANCHORS = {
    0x3184BC: 0xD10143FF,
    0x71F580: 0xB0002040,
    0x71F584: 0x9107C000,
    0x71F588: 0xD65F03C0,
    0x71FA64: 0xA9BB7BFD,
    0x71FAB4: 0xB9348001,
    0x53E910: 0xA9BB7BFD,
    0x53F460: 0xA9BA7BFD,
    0x8BD618: 0xD10103FF,
    0x9BF0E0: 0xD102C3FF,
    0x496190: 0x9414A3D4,
    0x824F48: 0x97F46672,
    0x85B840: 0x97F38F08,
    0x85FD78: 0x97F37DBA,
    0x863868: 0x97F36EFE,
    0x890144: 0x97F2BCC7,
    0x891EC8: 0x97F2B566,
    0x85B9D4: 0x940601A3,
    0x85B9FC: 0x9405CFF3,
}
UNSYMBOLIZED_HOOK_VMAS = (0x53E910, 0x53F460, 0x8BD618, 0x9BF0E0)
# operation, source VMA, exact displaced word, continuation / decoded BL target
BALANCE_SITES = (
    (1, 0x99FD94, 0x36000097, 0),
    (2, 0x5E87D4, 0x940ECD07, 0x99BBF0),
    (3, 0x994808, 0xB8296913, 0x99480C),
    (4, 0x8F1F7C, 0x94028A15, 0x9947D0),
    (5, 0x9A0448, 0xB8696916, 0x9A044C),
    (6, 0x9A06CC, 0x1B097D19, 0x9A06D0),
    (7, 0x48C120, 0x1B175AA8, 0x48C124),
    (8, 0x48C0D8, 0x94145219, 0x9A093C),
    (9, 0x5FDB70, 0x1A9FD7E0, 0x5FDB74),
    (10, 0x53EFD4, 0xB86A6929, 0x53EFD8),
)
