# satellite-globe

[![Update satellite positions](https://github.com/010kumaguma010/satellite-globe/actions/workflows/update_satellites.yml/badge.svg)](https://github.com/010kumaguma010/satellite-globe/actions/workflows/update_satellites.yml)
[![CI](https://github.com/010kumaguma010/satellite-globe/actions/workflows/ci.yml/badge.svg)](https://github.com/010kumaguma010/satellite-globe/actions/workflows/ci.yml)

VRChat用の衛星データを自動更新するリポジトリです。10分ごとにGitHub Actionsが衛星のTLEデータを取得し、現在位置と軌道要素を計算してCSV/JSONに書き出します。

## 仕組み

```
Space-Track.org / CelesTrak (TLE)
        │
        ▼
python -m satglobe          … SGP4伝播 + WGS84測地座標変換
        │
        ├─ data/satellites.csv   現在位置スナップショット（表示用）
        ├─ data/orbits.csv       軌道要素（クライアント側リアルタイム伝播用）
        └─ data/meta.json        生成時刻・衛星数・データソース
        │
        ▼
VRChat (Udon#) が raw URL から取得
```

| パス | 役割 |
|---|---|
| `satglobe/sources.py` | TLE取得（Space-Track → CelesTrak フォールバック） |
| `satglobe/tle.py` | TLEパース（3LE / 2LE / Alpha-5番号対応） |
| `satglobe/geodesy.py` | TEME → WGS84測地座標変換 |
| `satglobe/pipeline.py` | SGP4伝播とファイル出力 |
| `.github/workflows/update_satellites.yml` | 10分ごとに自動実行 |
| `.github/workflows/ci.yml` | push/PR時にテスト実行 |
| `tests/` | ユニットテスト（pytest） |

## 出力ファイル

### `data/satellites.csv` — 現在位置スナップショット

生成時刻における各衛星の位置。従来と同じ4列フォーマットです。

```csv
name,lat,lon,alt_km
ISS (ZARYA),25.1234,139.4567,417.3
NOAA 15,-12.3456,45.6789,820.1
```

- `lat` / `lon` — WGS84測地緯度・経度（度、経度は -180〜180）
- `alt_km` — WGS84楕円体からの高度（km）
- 名前のないTLEソースの場合のみ `NORAD 25544` 形式になります

> **注意:** 位置は生成時点のスナップショットです。cron実行の遅延を含めると最大20分程度古くなることがあります（ISSは10分で約4,600km移動します）。リアルタイム表示には `orbits.csv` を使ってください。

### `data/orbits.csv` — 軌道要素（リアルタイム伝播用）

各衛星のケプラー軌道要素。クライアント側（Udon#）で現在時刻の位置を計算できるため、データが多少古くても滑らかなリアルタイム表示が可能です。

```csv
name,norad,epoch_unix,inc_deg,raan_deg,ecc,argp_deg,mean_anomaly_deg,mean_motion_rev_per_day
ISS (ZARYA),25544,1704110400,51.6400,208.9163,0.0006317,69.9862,290.2018,15.49560532
```

| 列 | 意味 |
|---|---|
| `epoch_unix` | 軌道要素の元期（Unix秒、UTC） |
| `inc_deg` | 軌道傾斜角（度） |
| `raan_deg` | 昇交点赤経（度） |
| `ecc` | 離心率 |
| `argp_deg` | 近地点引数（度） |
| `mean_anomaly_deg` | 元期における平均近点角（度） |
| `mean_motion_rev_per_day` | 平均運動（周回/日） |

簡易伝播の例（円軌道近似、LEOの可視化には十分）:

```
t     = 現在Unix秒 - epoch_unix
M     = mean_anomaly_deg + 360 * mean_motion_rev_per_day * t / 86400
半径  = (μ / n²)^(1/3)   ここで n = 平均運動 [rad/s], μ = 398600.4418 km³/s²
軌道面内の角度Mから、inc/raanで回転して地心慣性座標へ
経度にはGMST（地球自転）の補正を掛ける
```

### `data/meta.json` — メタデータ

```json
{
  "generated_at": "2026-07-02T12:00:00+00:00",
  "generated_at_unix": 1782648000,
  "source": "space-track",
  "satellites": 12211,
  "skipped": 42
}
```

`generated_at_unix` と現在時刻を比べればデータの鮮度を判定できます。

## 生データURL（VRChat/Udon#で使用）

```
https://raw.githubusercontent.com/010kumaguma010/satellite-globe/main/data/satellites.csv
https://raw.githubusercontent.com/010kumaguma010/satellite-globe/main/data/orbits.csv
https://raw.githubusercontent.com/010kumaguma010/satellite-globe/main/data/meta.json
```

## データソース

| 優先度 | ソース | 認証 |
|---|---|---|
| 1 | [Space-Track.org](https://www.space-track.org/) `gp` クラス（3LE形式・衛星名付き） | 環境変数 `SPACETRACK_USER` / `SPACETRACK_PASS` |
| 2 | [CelesTrak](https://celestrak.org/) GP API（active グループ） | 不要 |

Space-Trackを使用するには無料アカウントを作成し、GitHubリポジトリの **Settings → Secrets → Actions** に `SPACETRACK_USER` と `SPACETRACK_PASS` を登録してください。

## ローカル実行

```bash
pip install -r requirements.txt
python -m satglobe            # data/ に出力
python -m satglobe /tmp/out   # 出力先を指定
```

Space-Trackを使用する場合:

```bash
SPACETRACK_USER=your@email.com SPACETRACK_PASS=yourpassword python -m satglobe
```

## テスト

```bash
pip install pytest
python -m pytest tests/ -v
```

座標変換は [skyfield](https://rhodesmill.org/skyfield/) との突き合わせで検証済みです（緯度・経度・高度とも一致）。

## GitHub Actions

`workflow_dispatch` でも手動実行可能（Actions タブ → "Update satellite positions" → Run workflow）。
