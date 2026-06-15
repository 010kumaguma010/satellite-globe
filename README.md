# satellite-globe

[![Update satellite positions](https://github.com/010kumaguma010/satellite-globe/actions/workflows/update_satellites.yml/badge.svg)](https://github.com/010kumaguma010/satellite-globe/actions/workflows/update_satellites.yml)

VRChat用の衛星位置データを自動更新するリポジトリです。10分ごとにGitHub Actionsが衛星のTLEデータを取得し、現在の緯度・経度・高度を計算してCSVに書き出します。

## 仕組み

```
Space-Track.org / CelesTrak (TLE) → generate_positions.py → data/satellites.csv → VRChat (Udon#)
```

| ファイル | 役割 |
|---|---|
| `generate_positions.py` | TLE取得 → 座標計算 → CSV出力 |
| `.github/workflows/update_satellites.yml` | 10分ごとに自動実行 |
| `data/satellites.csv` | VRChatが読むCSV |
| `vrchat/SatelliteGlobe.cs` | VRChat用 Udon# スクリプト |
| `requirements.txt` | Python依存ライブラリ |

## CSV フォーマット

```csv
name,lat,lon,alt_km
ISS (ZARYA),25.1234,139.4567,408.3
NOAA 15,-12.3456,45.6789,807.1
```

衛星名が含まれないTLEソース（Space-Track GP catalog）の場合はNORAD番号（例: `NORAD-25544`）が入ります。

## 生データURL（VRChat/Udon#で使用）

```
https://raw.githubusercontent.com/010kumaguma010/satellite-globe/main/data/satellites.csv
```

## データソース

| 優先度 | ソース | 認証 |
|---|---|---|
| 1 | [Space-Track.org](https://www.space-track.org/) `tle_latest` | 環境変数 `SPACETRACK_USER` / `SPACETRACK_PASS` |
| 2 | [CelesTrak](https://celestrak.org/) `pub/TLE/active.txt` | 不要 |

Space-Trackを使用するには無料アカウントを作成し、GitHubリポジトリの **Settings → Secrets → Actions** に `SPACETRACK_USER` と `SPACETRACK_PASS` を登録してください。

## ローカル実行

```bash
pip install -r requirements.txt
python generate_positions.py
```

Space-Trackを使用する場合:

```bash
SPACETRACK_USER=your@email.com SPACETRACK_PASS=yourpassword python generate_positions.py
```

## GitHub Actions

`workflow_dispatch` でも手動実行可能（Actions タブ → "Update satellite positions" → Run workflow）。

## VRChat セットアップ（Udon#）

`vrchat/SatelliteGlobe.cs` をUnityプロジェクトにコピーして使用します。

### 軌道帯と色分け

| 帯 | 高度 | 表示半径 | 推奨カラー | 例 |
|---|---|---|---|---|
| LEO | 0 – 2,000 km | 1.10 – 1.35 × 地球儀半径 | 白 / シアン | Starlink, ISS |
| MEO | 2,000 – 35,785 km | 1.60 – 1.90 × 地球儀半径 | 黄 | GPS, Galileo |
| GEO+ | ≥ 35,785 km | 2.10 – 2.50 × 地球儀半径 | オレンジ | 静止衛星 |

高度は視認性のために圧縮されています（実際の比率ではありません）。

### 手順

1. **マーカー Prefab を3種類作成**  
   小さな Sphere（スケール `(0.015, 0.015, 0.015)` 程度）にそれぞれ色違いのマテリアルを割り当て、Prefab 化する。

2. **スクリプトをアタッチ**  
   地球儀メッシュの中心に空の GameObject を作り、`SatelliteGlobe` をアタッチする。

3. **Inspector で設定**

   | フィールド | 説明 | 目安 |
   |---|---|---|
   | `Csv Url` | CSVのURL（デフォルト値のまま使用可） | — |
   | `Refresh Interval Seconds` | 再取得間隔（秒） | `600`（10分） |
   | `Globe Radius` | 地球儀メッシュの半径（Unity単位） | 例: `1.0` |
   | `Leo Prefab` | LEO用マーカー（白/シアン） | — |
   | `Meo Prefab` | MEO用マーカー（黄） | — |
   | `Geo Prefab` | GEO+用マーカー（オレンジ） | — |
   | `Max Leo` | LEO表示上限 | `500` |
   | `Max Meo` | MEO表示上限 | `100` |
   | `Max Geo` | GEO+表示上限 | `150` |

4. **URL許可リスト**  
   VRChat SDK の **Allow Listed URLs** に以下を追加する：
   ```
   https://raw.githubusercontent.com/010kumaguma010/satellite-globe/main/data/satellites.csv
   ```

### 座標系

地球儀の向きは以下を前提としています（Unity Y-up）：
- 北極 → +Y
- (緯度0, 経度0) → +X
- (緯度0, 経度90°E) → +Z

地球儀メッシュがこの向きと異なる場合は、`SatelliteGlobe` GameObject を回転させて合わせてください。
