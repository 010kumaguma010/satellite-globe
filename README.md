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
