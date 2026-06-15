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

### 前提

- VRChat Creator Companion (VCC) でプロジェクトを作成済み
- UdonSharp がインポート済み（VCC から追加可能）

---

### Step 1 — スクリプトをインポート

1. このリポジトリの `vrchat/SatelliteGlobe.cs` をダウンロード
2. Unity の **Project** ウィンドウの `Assets` フォルダ内（例: `Assets/Scripts/`）にドラッグ＆ドロップ
3. コンパイルエラーが出なければOK

---

### Step 2 — マーカー Prefab を3種類作成

衛星を軌道帯ごとに色分けするため、色違いの小さな球を3つ作ります。

**以下を3回繰り返す（LEO・MEO・GEO用）：**

1. **Hierarchy** で右クリック → `3D Object > Sphere` を作成
2. **Inspector** で Transform の Scale を `(0.015, 0.015, 0.015)` に変更
3. **Project** ウィンドウで右クリック → `Create > Material` でマテリアルを作成し、色を設定
   - LEO用: 白 または シアン `(0, 1, 1)`
   - MEO用: 黄 `(1, 1, 0)`
   - GEO用: オレンジ `(1, 0.5, 0)`
4. 作ったマテリアルを Sphere にドラッグして適用
5. Sphere を **Project** ウィンドウの `Assets` フォルダにドラッグして **Prefab 化**
6. **Hierarchy** の Sphere は削除してOK

---

### Step 3 — 地球儀の中心に Controller オブジェクトを作成

1. **Hierarchy** で地球儀メッシュの **子オブジェクト** として空の GameObject を作成
   - 右クリック（地球儀を選択した状態で）→ `Create Empty`
   - 名前を `SatelliteController` などに変更
2. この GameObject の Transform Position が `(0, 0, 0)` になっていることを確認

> **ポイント:** 地球儀が回転・移動しても衛星が一緒に動くよう、必ず子オブジェクトにします。

---

### Step 4 — スクリプトをアタッチして設定

1. `SatelliteController` を選択した状態で **Inspector** の `Add Component` をクリック
2. `SatelliteGlobe` を検索してアタッチ
3. Inspector に表示された各フィールドを設定する：

| フィールド | 設定値 |
|---|---|
| **Csv Url** | デフォルトのままでOK（変更不要） |
| **Refresh Interval Seconds** | `600`（10分ごとに更新） |
| **Globe Radius** | 地球儀メッシュの半径（Unity単位）※下記参照 |
| **Leo Prefab** | Step 2 で作った白/シアンの Prefab |
| **Meo Prefab** | Step 2 で作った黄色の Prefab |
| **Geo Prefab** | Step 2 で作ったオレンジの Prefab |
| **Max Leo** | `500`（Starlink等LEO衛星の表示上限） |
| **Max Meo** | `100`（GPS等MEO衛星の表示上限） |
| **Max Geo** | `150`（静止衛星等の表示上限） |

**Globe Radius の調べ方：**
地球儀オブジェクトを選択 → Inspector の Scale X を確認。
標準の Sphere は直径 1（半径 0.5）なので、Scale X が `2` なら Globe Radius = `1.0`。

---

### Step 5 — URL 許可リストに追加

1. Unity メニューから `VRChat SDK > Settings` を開く
2. **Allow Listed URLs** の `+` ボタンをクリック
3. 以下のURLを入力して追加：

```
https://raw.githubusercontent.com/010kumaguma010/satellite-globe/main/data/satellites.csv
```

---

### Step 6 — 動作確認

1. Unity の **Play** ボタンを押す
2. しばらく待つと（数秒〜10秒）Console に以下のようなログが出れば成功：
   ```
   [SatelliteGlobe] Placed — LEO: 500, MEO: 87, GEO+: 142
   ```
3. Scene ビューで地球儀の周りに点が表示されているか確認

---

### 軌道帯と表示位置

| 帯 | 高度 | 表示位置 | 色 | 代表例 |
|---|---|---|---|---|
| LEO | 0 – 2,000 km | 地表から10〜35%上 | 白/シアン | Starlink, ISS |
| MEO | 2,001 – 35,785 km | 地表から60〜90%上 | 黄 | GPS, Galileo |
| GEO+ | ≥ 35,785 km | 地表から2.1倍以上 | オレンジ | 静止衛星 |

> 高度は視認性のために圧縮しています（実際の比率ではありません）。

---

### 地球儀の向きが合わない場合

このスクリプトは以下の向きを前提にしています（Unity Y-up）：

```
北極 → +Y（上）
経度0°/緯度0° → +X（前）
経度90°E/緯度0° → +Z（右）
```

地球儀のテクスチャがズレている場合は、`SatelliteController` の Rotation Y を調整してください。
北極が上を向いていない場合は Rotation X も調整します。
