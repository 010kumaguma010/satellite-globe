# 3Dアセット

VRChatワールド用の3Dモデルです。Blender(bpy)スクリプトで生成しています。

| ファイル | 内容 | ポリゴン数 |
|---|---|---|
| `earth_globe.fbx` / `.glb` | 地球儀(直径1m、UV球96×48分割、スムーズシェーディング) | 約9,000 tris |
| `satellite.fbx` / `.glb` | ローポリ衛星(金色バス・太陽電池パドル・ディッシュアンテナ) | 224 tris |
| `textures/earth_bmng_4k.jpg` | 地球テクスチャ 4096×2048(NASA Blue Marble Next Generation) | — |

- **FBX**: Unity / VRChat 用。テクスチャは同梱していないので、インポート後にマテリアルへ `textures/earth_bmng_4k.jpg` を割り当ててください
- **GLB**: テクスチャ埋め込み済み。プレビューや他エンジン用([three.js editor](https://threejs.org/editor/) やWindowsの3Dビューアーでそのまま確認できます)

## Unityへのインポート手順

1. `earth_globe.fbx` と `textures/earth_bmng_4k.jpg` をAssetsにドラッグ
2. FBXの Materials タブ → Extract Materials → Earth マテリアルの Albedo に `earth_bmng_4k` を割り当て
3. シーンに配置し、`SatelliteGlobe.cs`(`clients/vrchat/`)の **Globe** フィールドにこのTransformを割り当て、**Globe Radius Units** = 0.5(直径1mのまま使う場合)
4. `satellite.fbx` は任意。ISSなど特定衛星のマーカーや装飾用のローポリモデルです(全長約50cm、原点はバス中心)

## 向きについて

メッシュは「経度0°(グリニッジ)が +X、東経90°が +Z、北極が +Y」になるように作ってあり、`SatelliteGlobe.cs` の座標系と一致します。もしインポート設定の違いで地図が経度方向にズレて見える場合は、**地球儀メッシュをスクリプトに割り当てたTransformの子にして、子側だけをY軸回転**で合わせてください(スクリプトは親のTransformしか見ないため、衛星の位置に影響しません)。

## 再生成

```bash
pip install bpy basemap basemap-data pillow
python scripts/build_assets.py
```

## ライセンス

- 地球テクスチャ: [NASA Blue Marble Next Generation](https://earthobservatory.nasa.gov/features/BlueMarble)(パブリックドメイン)
- 3Dモデル: このリポジトリのライセンスに従います(自由に改変可)
