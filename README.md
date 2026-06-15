# satellite-globe

VRChat用の衛星位置データを自動更新するリポジトリです。

## 仕組み

```
CelesTrak (TLE) → generate_positions.py → data/satellites.csv → VRChat (Udon#)
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
```

## 生データURL（VRChat/Udon#で使用）

```
https://raw.githubusercontent.com/010kumaguma010/satellite-globe/main/data/satellites.csv
```

## ローカル実行

```bash
pip install -r requirements.txt
python generate_positions.py
```

## GitHub Actions

`workflow_dispatch` でも手動実行可能（Actions タブ → "Update satellite positions" → Run workflow）。
