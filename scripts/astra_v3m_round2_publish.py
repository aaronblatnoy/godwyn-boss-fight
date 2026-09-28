"""Round-2 publisher for the world-space V3 mocap pass (black-sky only).

This reuses the validated native/GLB checks from ``astra_v3m_publish`` while
pinning the expected Round-1 canonical hashes.  The pre-mocap original is
preserved separately before ``_prev`` advances to the Round-1 canonical.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import astra_v3m_publish as publish


publish.WIP = publish.ROOT / "models/astra_character_v3m_round2_wip.blend"
publish.TEMP_BLEND = publish.ROOT / "models/astra_character_v3_round2_publish_tmp.blend"
publish.TEMP_GLB = publish.ROOT / "models/astra_character_v3_round2_publish_tmp.glb"
publish.OUT = publish.ROOT / "renders/astra/char2/astra_v3m_round2_publish.json"
publish.ROUNDTRIP_OUT = publish.ROOT / "renders/astra/char2/astra_v3m_round2_roundtrip.json"
publish.EXPECTED_SOURCE_BLEND = "32afac85f2676bfb4ab5db22156bfee14b9aae1844d0b3a12aa1977a117c1ba0"
publish.EXPECTED_SOURCE_GLB = "351a3ef83baee9ed4b315f1c042f76a72846af905680f17a51bf75b08b4b03ab"

PRE_MOCAP_BLEND = publish.ROOT / "models/astra_character_v3_pre_mocap.blend"
PRE_MOCAP_GLB = publish.ROOT / "models/astra_character_v3_pre_mocap.glb"
ORIGINAL_BLEND = "e254ac97530c265ee1ac36b659f4d5ae752e8d27ec6842254e8b79277ca2abc9"
ORIGINAL_GLB = "e2577625e35af133ef3fe0e240016e59108a10e9453430c4a58d4ca95e6b9fe9"
ROUND1_BLEND = "49ff778d2279723230a6c9bdc1ebd2d423d67d7db58f746aa19544e3669b5a72"
ROUND1_GLB = "2aeb5782c4736660a58bd867737e0c5c9f3c7f4fb50e2b728f1ae753d94443e7"
HOLD_BLEND = publish.ROOT / "models/astra_character_v3_round1_hold.blend"
HOLD_GLB = publish.ROOT / "models/astra_character_v3_round1_hold.glb"


def preserve_pre_mocap():
    assert PRE_MOCAP_BLEND.exists() and PRE_MOCAP_GLB.exists()
    assert publish.sha256(PRE_MOCAP_BLEND) == ORIGINAL_BLEND
    assert publish.sha256(PRE_MOCAP_GLB) == ORIGINAL_GLB


def annotate():
    report = json.loads(publish.OUT.read_text())
    report["schema"] = "astra-v3m-round2-publish"
    report["pre_mocap_backup"] = {
        "blend": str(PRE_MOCAP_BLEND.relative_to(publish.ROOT)),
        "blend_sha256": publish.sha256(PRE_MOCAP_BLEND),
        "glb": str(PRE_MOCAP_GLB.relative_to(publish.ROOT)),
        "glb_sha256": publish.sha256(PRE_MOCAP_GLB),
    }
    report["backup"] = {
        "blend": str(publish.PREV_BLEND.relative_to(publish.ROOT)),
        "blend_sha256": publish.sha256(publish.PREV_BLEND),
        "glb": str(publish.PREV_GLB.relative_to(publish.ROOT)),
        "glb_sha256": publish.sha256(publish.PREV_GLB),
    }
    publish.OUT.write_text(json.dumps(report, indent=2) + "\n")
    roundtrip = json.loads(publish.ROUNDTRIP_OUT.read_text())
    roundtrip["schema"] = "astra-v3m-round2-roundtrip"
    publish.ROUNDTRIP_OUT.write_text(json.dumps(roundtrip, indent=2) + "\n")


if __name__ == "__main__":
    preserve_pre_mocap()
    # A four-action candidate was promoted before the inherited p99<=1.6
    # acceptance gate was rechecked.  Preserve the actual Round-1 canonical as
    # the rollback copy while replacing that rejected intermediate publish.
    assert publish.sha256(publish.PREV_BLEND) == ROUND1_BLEND
    assert publish.sha256(publish.PREV_GLB) == ROUND1_GLB
    shutil.copy2(publish.PREV_BLEND, HOLD_BLEND)
    shutil.copy2(publish.PREV_GLB, HOLD_GLB)
    publish.main()
    shutil.copy2(HOLD_BLEND, publish.PREV_BLEND)
    shutil.copy2(HOLD_GLB, publish.PREV_GLB)
    HOLD_BLEND.unlink()
    HOLD_GLB.unlink()
    assert publish.sha256(publish.PREV_BLEND) == ROUND1_BLEND
    assert publish.sha256(publish.PREV_GLB) == ROUND1_GLB
    annotate()
