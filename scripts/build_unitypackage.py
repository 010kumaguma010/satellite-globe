"""Build release/SatelliteGlobe_VRChat.unitypackage from repo files.

A .unitypackage is a gzipped tar where each asset lives in a directory
named by its GUID, containing:
    pathname    the path under Assets/
    asset       the file bytes (absent for folders)
    asset.meta  the Unity .meta file carrying that GUID

GUIDs are deterministic (md5 of the asset path), so rebuilding the
package never breaks references in projects that already imported it —
in particular Earth.mat's link to the earth texture.

Usage: python scripts/build_unitypackage.py
"""

import hashlib
import io
import os
import tarfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "release", "SatelliteGlobe_VRChat.unitypackage")
ROOT = "Assets/SatelliteGlobe"

DATA_URL = "https://raw.githubusercontent.com/010kumaguma010/satellite-globe/main/data/orbits.csv"


def guid_for(path: str) -> str:
    return hashlib.md5(f"satellite-globe:{path}".encode()).hexdigest()


def meta_for(path: str, guid: str) -> str:
    head = f"fileFormatVersion: 2\nguid: {guid}\n"
    if path.endswith("/"):
        return head + "folderAsset: yes\nDefaultImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n"
    if path.endswith(".cs"):
        return head + (
            "MonoImporter:\n  externalObjects: {}\n  serializedVersion: 2\n"
            "  defaultReferences: []\n  executionOrder: 0\n  icon: {instanceID: 0}\n"
            "  userData: \n  assetBundleName: \n  assetBundleVariant: \n"
        )
    if path.endswith(".mat"):
        return head + (
            "NativeFormatImporter:\n  externalObjects: {}\n  mainObjectFileID: 2100000\n"
            "  userData: \n  assetBundleName: \n  assetBundleVariant: \n"
        )
    # FBX / textures / markdown: let Unity import with default settings for
    # its own version; only the GUID matters for cross-references.
    if path.endswith(".fbx"):
        return head + "ModelImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n"
    if path.endswith((".jpg", ".png")):
        return head + "TextureImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n"
    return head + "TextAssetImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n"


def earth_material(tex_guid: str) -> bytes:
    return f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_Name: Earth
  m_Shader: {{fileID: 46, guid: 0000000000000000f000000000000000, type: 0}}
  m_ValidKeywords: []
  m_InvalidKeywords: []
  m_LightmapFlags: 4
  m_EnableInstancingVariants: 0
  m_DoubleSidedGI: 0
  m_CustomRenderQueue: -1
  stringTagMap: {{}}
  disabledShaderPasses: []
  m_SavedProperties:
    serializedVersion: 3
    m_TexEnvs:
    - _MainTex:
        m_Texture: {{fileID: 2800000, guid: {tex_guid}, type: 3}}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    m_Ints: []
    m_Floats:
    - _Glossiness: 0.15
    - _Metallic: 0
    m_Colors:
    - _Color: {{r: 1, g: 1, b: 1, a: 1}}
  m_BuildTextureStacks: []
""".encode()


PACKAGE_README = f"""# SatelliteGlobe セットアップ

リアルタイム衛星表示ワンセット。前提: VRChat SDK3 (Worlds) + UdonSharp(VCC導入)。

## 手順(5分)

1. **地球儀を配置**
   `Models/earth_globe.fbx` をシーンへ。`Materials/Earth.mat`(テクスチャ設定済み)を割り当て。
   直径1m。大きさは自由に変えてOK(半径を控えておく)。

2. **ParticleSystemを追加**
   地球儀の子に ParticleSystem を作成し:
   - Main: Play On Awake **オフ** / Max Particles **30000** / Simulation Space **Local**
   - Emission と Shape: **オフ**
   - Renderer: Render Mode = Billboard、明るめの小さいマテリアル(Additive推奨)

3. **スクリプトを設定**
   空のGameObjectに `SatelliteGlobe.cs` を追加し、インスペクタで:

   | フィールド | 値 |
   |---|---|
   | Orbits Url | `{DATA_URL}` |
   | Globe | 地球儀のTransform |
   | Globe Radius Units | 0.5(直径1mのまま使う場合) |
   | Satellite Particles | 手順2のParticleSystem |
   | Altitude Scale | 1(見やすくするなら2〜5) |

4. Playモードで数秒待つと約1万機の衛星が現在位置に表示されます。

## 備考

- `Models/satellite.fbx` は特定衛星のマーカーや装飾用のローポリモデル(任意)
- 地図が経度方向にズレて見える場合: 地球儀メッシュを Globe に割り当てたTransformの
  **子** にして、子側だけをY軸回転で調整(衛星位置には影響しません)
- データは10分ごとに自動更新(GitHub Actions)。位置計算はワールド内でリアルタイム
- 詳細: https://github.com/010kumaguma010/satellite-globe
- 地球テクスチャ: NASA Blue Marble(パブリックドメイン)
"""


def build() -> None:
    entries: list[tuple[str, bytes | None]] = [
        (f"{ROOT}/", None),
        (f"{ROOT}/Models/", None),
        (f"{ROOT}/Textures/", None),
        (f"{ROOT}/Materials/", None),
        (f"{ROOT}/README_SETUP.md", PACKAGE_README.encode()),
    ]
    files = {
        f"{ROOT}/SatelliteGlobe.cs": "clients/vrchat/SatelliteGlobe.cs",
        f"{ROOT}/Models/earth_globe.fbx": "assets/earth_globe.fbx",
        f"{ROOT}/Models/satellite.fbx": "assets/satellite.fbx",
        f"{ROOT}/Textures/earth_bmng_4k.jpg": "assets/textures/earth_bmng_4k.jpg",
    }
    for dest, src in files.items():
        with open(os.path.join(REPO, src), "rb") as f:
            entries.append((dest, f.read()))
    entries.append((
        f"{ROOT}/Materials/Earth.mat",
        earth_material(guid_for(f"{ROOT}/Textures/earth_bmng_4k.jpg")),
    ))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    now = time.time()

    def add(tar: tarfile.TarFile, name: str, data: bytes) -> None:
        info = tarfile.TarInfo(name)
        info.size = len(data)
        info.mtime = int(now)
        tar.addfile(info, io.BytesIO(data))

    with tarfile.open(OUT, "w:gz") as tar:
        for path, data in entries:
            guid = guid_for(path)
            add(tar, f"{guid}/pathname", path.rstrip("/").encode() + b"\n")
            add(tar, f"{guid}/asset.meta", meta_for(path, guid).encode())
            if data is not None:
                add(tar, f"{guid}/asset", data)

    print(f"wrote {OUT} ({os.path.getsize(OUT) // 1024} KB, {len(entries)} assets)")


if __name__ == "__main__":
    build()
