# VRChat クライアント (UdonSharp)

`SatelliteGlobe.cs` は `data/orbits.csv` をダウンロードし、各衛星の位置を**ワールド内でリアルタイムに計算**して地球儀の周りに表示するUdonSharpスクリプトです。データ側は10分ごとの更新ですが、伝播計算をクライアントで行うため表示は常に現在時刻の位置になり、滑らかに動きます。

軌道計算モデル(ケプラー伝播 + J2永年摂動)のリファレンス実装とテストは `satglobe/kepler.py` / `tests/test_kepler.py` にあります。SGP4との誤差はLEOで10km前後(軌道半径の0.2%)で、地球儀表示では判別できません。

## 必要環境

- VRChat SDK3 (Worlds)
- [UdonSharp](https://udonsharp.docs.vrchat.com/)(VCC経由で導入)

## セットアップ

1. **地球儀**: `assets/earth_globe.fbx`(直径1m・NASA Blue Marbleテクスチャは `assets/textures/` に同梱)をインポートして配置。自作の球体でも可。半径をワールド単位で控えておく(例: 直径1mなら 0.5)
2. **ParticleSystem**: 地球儀の子にParticleSystemを追加し、以下を設定
   - Main: `Play On Awake` オフ / `Max Particles` を 30000 に / `Simulation Space` = Local
   - Emission / Shape: **オフ**(粒子はスクリプトが直接配置します)
   - Renderer: Render Mode = Billboard、小さめのマテリアル(Additiveなど)
3. **スクリプト**: 空のGameObjectに `SatelliteGlobe.cs` を付け ─ インスペクタで設定:

| フィールド | 値 |
|---|---|
| Orbits Url | `https://raw.githubusercontent.com/010kumaguma010/satellite-globe/main/data/orbits.csv` |
| Refresh Minutes | 15(再ダウンロード間隔) |
| Globe | 地球儀のTransform |
| Globe Radius Units | 地球儀の半径(ワールド単位) |
| Altitude Scale | 1 = 実スケール。LEOを見やすくするなら 2〜5 |
| Satellite Particles | 手順2のParticleSystem |
| Updates Per Frame | 300(重い場合は下げる。全衛星一巡は 衛星数÷この値 フレーム) |

## 動作の仕組み

- `VRCStringDownloader` でCSVを取得(VRChatの制約: URLはインスペクタで固定、ダウンロードは5秒に1回まで)
- パースはフレーム分割(`parsesPerFrame` 行/フレーム)でヒッチを防止
- 毎フレーム `updatesPerFrame` 個の衛星位置を再計算し、パーティクル配列を `SetParticles` で反映
- 座標系: ECEF (X, Y, Z) → Unity (X, Z, Y)。地球儀のテクスチャは経度0°がUnityの+X方向を向くように合わせてください
