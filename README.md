# はてな展 診断システム

マークシートをiPadで撮影して16タイプ診断結果をA5用紙に印刷するシステム。

## システム構成
## 必要環境

- **macOS 推奨**（Windows/Linux は動作未確認）
- Python **3.9以上**（3.8以下は型ヒント構文エラーになる）
- Node.js 18以上
- Google Chrome（`/Applications/Google Chrome.app` にインストール済み）
- CUPSプリンター（A5印刷対応）
- mkcert（HTTPS証明書生成用）

## セットアップ

### 1. クローン

```bash
git clone https://github.com/Makoto-entaku/hatena-diagnosis.git
cd hatena-diagnosis
```

### 2. バックエンド

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. フロントエンド

```bash
cd frontend
npm install
```

### 4. SSL証明書の生成（必須）

iPadからHTTPSでアクセスするために必要。**自分のMacのLAN IPに合わせて実行すること。**

```bash
# mkcert インストール（初回のみ）
brew install mkcert
mkcert -install

# LAN IPを確認
ipconfig getifaddr en0

# 証明書を生成（IPは自分の環境に合わせて変更）
cd frontend
mkcert 192.168.1.10
# → 192.168.1.10.pem と 192.168.1.10-key.pem が生成される
```

生成後、`frontend/server.js` を開いてSSL証明書のファイル名をIPアドレスに合わせて修正する。

### 5. type_images の配置

`frontend/public/type_images/` に各タイプのイラスト画像（PNG）を手動で配置する。  
ファイル名は `data/types.json` の `type_id` フィールドに合わせること（例: `capybara.png`, `beaver.png` など）。

## 起動

### バックエンド

```bash
cd backend
source .venv/bin/activate

# 接続プリンターの名前を確認
lpstat -p

# 起動（IPとプリンター名は環境に合わせて変更）
PRINTER_1=EPSON_PX_S887 \
PRINTER_2=EPSON_PX_S887 \
FRONTEND_BASE_URL=https://192.168.1.10:3443 \
nohup uvicorn main:app --host 0.0.0.0 --port 8000 &

# 動作確認
curl -s http://localhost:8000/health
# → {"status":"ok"} が返れば OK
```

### フロントエンド

```bash
cd frontend
npm run build
node server.js &
```

iPadのSafariで `https://[LAN_IP]:3443/scan` を開く。

## 環境変数一覧

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `PRINTER_1` | station=1 のプリンター名（`lpstat -p` で確認） | `EPSON_PX_S887` |
| `PRINTER_2` | station=2 のプリンター名 | `EPSON_PX_S887` |
| `FRONTEND_BASE_URL` | フロントエンドのURL（PDF生成に使用） | `https://192.168.1.10:3443` |

## よくあるトラブル

**iPadからアクセスできない（証明書エラー）**  
→ `mkcert -install` を実行後、`mkcert [LAN_IP]` で証明書を再生成。Safariで初回アクセス時に「このWebサイトを信頼」をタップ。

**印刷が500エラーになる**  
→ `lpstat -p` でプリンター名を確認し、`PRINTER_1` の値と完全一致させる。

**マークシートが検出されない**  
→ マークシートの4隅が画面に収まるよう正面から撮影する。斜め撮影・暗い照明はNG。

**`ModuleNotFoundError: No module named 'cv2'`**  
→ `.venv` が有効化されていない。`source backend/.venv/bin/activate` を実行してから起動する。

**Python 3.8以下でエラー**  
→ `tuple[int, int]` 型ヒントを使用しているため Python 3.9以上が必要。`python3 --version` で確認。

**`node server.js` でCertificate not found エラー**  
→ `frontend/` 直下に `mkcert` で生成した `.pem` ファイルが存在するか確認。`server.js` 内のファイル名が生成した証明書名と一致しているか確認。

## OMR仕様（開発者向け）

- 用紙: A5（419.53 × 595.28 pt）
- レジマーク: 4隅のピンク■で射影変換補正
- Q1–Q12: 左列 ABCD4択バブル（HALF_ROWS=12）
- Q13–Q16: 右列 ABCD4択バブル
- Q17–Q20: 番号選択バブル（座席位置など）
- ワープ後解像度: 800 × 1135 px
- バブル検出半径: 4.8pt × スケール × 0.7
