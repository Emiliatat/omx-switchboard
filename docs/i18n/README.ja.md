# omx-switchboard

> Codex 向けの自律型ワークフロールーター。AI が自分で、ネイティブのまま進めるべきか、先に計画すべきか、より強いワークフローへ昇格すべきかを判断します。

## Languages

- [English](../../README.md)
- [简体中文](./README.zh-CN.md)
- [日本語](./README.ja.md)

## これは何か

`omx-switchboard` は Codex 向けのスキル兼ランチャープロジェクトです。目的は、ユーザーが毎回 `native`、`deep-interview`、`ralplan`、`ralph`、`team` を手動で選ぶことではなく、タスクの性質に応じてシステムが適切なモードを選べるようにすることです。

主な役割は次のとおりです。

- 小さく明確なタスクはネイティブ Codex に残す
- 曖昧で要件が未整理なタスクは `deep-interview` に回す
- 設計や方針づくり中心のタスクは `ralplan` に回す
- 実行準備が整った逐次作業は `ralph` に回す
- 本当に並列化が有効な場合だけ `team` に回す
- 問題発見が中心の依頼は `code-review` または `security-review` に回す

提供形態は 2 層です。

1. `$omx-switchboard` スキル
2. すべてのタスクに対して自動ルーティングを挟める `omxr` ランチャー

## なぜ必要か

ネイティブ Codex、`deep-interview`、`ralplan`、`ralph`、`team` はどれも有用ですが、それぞれ向いているタスクの形が違います。

このプロジェクトの主眼は「OMX の方が高コストだから避ける」ことではありません。大事なのは、AI が適切なタイミングで軽量に進めるか、先に計画するか、より強いワークフローへ移るかを自律的に判断できることです。

実際には次のように働きます。

- 単純なタスクは軽量のまま進める
- 要件が曖昧なタスクは先に探索と整理を行う
- 設計中心のタスクは先に計画へ回す
- 実装条件が揃ったタスクはそのまま実行へ進める
- 並列化に意味があるときだけ `team` を使う

つまり、モード選択をユーザーの手作業ではなく、システムの振る舞いとして組み込みます。

## このリポジトリでインストールされるもの

このリポジトリは現時点では実用的なインストールフローを提供しており、marketplace 型のワンクリックプラグイン配布ではありません。

インストール後に得られるもの：

- `~/.codex/skills/omx-switchboard` 配下のスキル
- `~/.local/bin` 配下の `omxr` と `omx-switchboard` ランチャー

現在やらないこと：

- Codex marketplace への自動登録
- 別カタログ経由での自動表示

一番簡単な理解としては：

- GitHub からインストールできるスキル兼ランチャーパッケージ
- 将来的なプラグイン配布に備えた manifest も同梱

## 自動ルーティングの仕組み

ここでいう「自動」には 2 つの意味があります。

### 1. 暗黙的なスキル呼び出し

同梱の `openai.yaml` により、関連タスクであれば Codex が `$omx-switchboard` を暗黙的に取り込めます。

### 2. 決定論的なデフォルト入口

すべてのプロンプトで確実にタスク判定を通したい場合は、`omxr` または `omx-switchboard` ランチャーを使います。

これらのランチャーは：

- 先にタスク形状を分類する
- 選ばれたルートを表示または実行する
- `team` や `ralph` の前提が満たされない場合は安全に降格する

これが「常時オンの自動ルーティング」を実現する確実な方法です。

## ルーティング規則

ルーターは 3 つの軸でタスクを評価します。

1. `ambiguity_score`
2. `scope_score`
3. `parallelism_score`

### 曖昧さ `ambiguity_score`

次に当てはまるごとに 1 点：

- 望ましい最終状態が不明確
- 受け入れ条件がない
- 境界や非目標が定義されていない
- `improve` や `optimize` のような広い動詞だけで範囲が固定されていない
- 実装依頼というより、まだプロダクト要求の段階に近い

解釈：

- `0-1`: 低い
- `2-3`: 中程度
- `4-5`: 高い

### 規模 `scope_score`

次に当てはまるごとに 1 点：

- 複数モジュールや複数サブシステムにまたがりそう
- 少なくとも 3 つ以上の意味ある実装ステップが含まれる
- 検証やテスト自体に実作業が必要
- 移行や互換性リスクがある
- 短い 1 回の実行では終わりそうにない

解釈：

- `0-1`: 小さい
- `2-3`: 中くらい
- `4-5`: 大きい

### 並列性 `parallelism_score`

次に当てはまるごとに 1 点：

- 少なくとも 2 本の独立した作業レーンを定義できる
- 実装と検証を並行して進められる
- ドキュメント、移行、展開を独立して進められる
- 永続 tmux や worktree の調整が実際に役立つ

解釈：

- `0-1`: `team` は使わない
- `2`: 場合による
- `3-4`: `team` の有力候補

## 判定順序

次の順番で適用します。

1. `route:team` や `route:native` などの明示指定
2. 問題発見中心の依頼 -> `review`
3. セキュリティ中心の依頼 -> `security`
4. `ambiguity_score >= 3` -> `deep`
5. `scope_score >= 3` かつ実行準備未完了 -> `plan`
6. `scope_score >= 3`、`parallelism_score >= 3`、tmux 前提が成立 -> `team`
7. `scope_score >= 2` かつ実行準備完了 -> `ralph`
8. それ以外 -> `native`

ここでいう「実行準備完了」とは、目標、期待結果、検証方法が十分具体的で、追加の探索なしに実装へ入れる状態を指します。

## 降格ポリシー

より強いルートが使えない場合は：

- `team -> ralph -> plan -> native`
- `ralph -> plan -> native`
- `plan -> native`

ランチャーは説明出力の中で降格理由も示します。

## インストール

### 前提条件

事前に次を用意してください。

- `git`
- Unix 系なら `python3`
- Windows なら `python` または `py -3`
- Codex の基本セットアップ完了

推奨：

- `~/.local/bin` を `PATH` に追加する

追加しなくても、フルパスで起動できます。

- Unix-like: `~/.local/bin/omxr`
- Windows: `$HOME\\.local\\bin\\omxr.cmd`

### Unix-like

```bash
git clone https://github.com/Emiliatat/omx-switchboard.git
cd omx-switchboard
bash ./scripts/install.sh
```

### Windows PowerShell

```powershell
git clone https://github.com/Emiliatat/omx-switchboard.git
cd omx-switchboard
.\scripts\install.ps1
```

デフォルトのインストール内容：

- スキルを `~/.codex/skills/omx-switchboard` へコピー
- ランチャーを `~/.local/bin` へ配置

インストールされるランチャー：

- `omxr`
- `omx-switchboard`

## 使い方

### スキルを直接使う

```text
$omx-switchboard
Fix the login timeout and choose the safest workflow automatically.
```

```text
$omx-switchboard route:plan
Design the safest migration path first. Do not execute yet.
```

```text
$omx-switchboard route:team
Split implementation, verification, and docs into parallel lanes.
```

### 常時自動ルーティングのランチャーを使う

選ばれたルートを説明する：

```bash
omxr route "Design the safest auth migration"
```

実行されるコマンドを表示する：

```bash
omxr print "Fix the login timeout with verification"
```

自動ルーティングして実行する：

```bash
omxr "Fix the login timeout with verification"
```

明示的な等価形式：

```bash
omxr exec "Fix the login timeout with verification"
```

## 単体ディスパッチスクリプト

コアの補助スクリプトを直接使うこともできます。

```bash
python3 skills/omx-switchboard/scripts/dispatch_omx.py \
  --route auto \
  --task "Split implementation, tests, and docs in parallel" \
  --format json
```

## 公開情報

現在の公開リポジトリ：

- `https://github.com/Emiliatat/omx-switchboard`

Fork する場合は、次の公開メタデータも自分用に更新してください。

- `.codex-plugin/plugin.json`
- `LICENSE`
- `README.md`

## 帰属表示

このプロジェクトは `oh-my-codex` から影響を受け、相互運用を想定しています。

`oh-my-codex` や `cli-in-wechat` からコピーまたは改変した内容を含む場合は、上流の MIT ライセンス表示と帰属情報を維持してください。詳細は [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md) を参照してください。
