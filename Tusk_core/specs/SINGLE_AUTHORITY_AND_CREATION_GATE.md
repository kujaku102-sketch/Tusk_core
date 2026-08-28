# Single Authority and Creation Gate

## Status

状態: `COMPLETED`

## Legacy identity

- Legacy heading: `TCS-011: Single Authority and Creation Gate`
- Legacy filename: `specs/TCS-011_SINGLE_AUTHORITY_GATE.md`

## Purpose and Requirement

Single Authority Principleを適用し、概念と正本の対応を一元化する。新規Markdown AuthorityはCreation Gateを既定とし、外部モデルを読み取り専用監査へ制限し、監査reportを一時証拠として扱う。

## Authority references

- Single Authority Principle: `GENERAL.md`
- 概念とAuthorityの機械対応: `AUTHORITY-MAP.json`
- 監査実装: `tools/authority_auditor.py`
- AI作業境界: `AGENTS.md`

## Scope and Outcome

原則、Authority map、監査Tool、Creation Gate、専用テストを対象とした。既存概念を既存正本へ戻し、未確認の新規概念を拒否し、独立概念だけを新規Authority候補とする結果を記録する。

## Acceptance

現行Authority監査が問題0件であり、監査とCreation Gateがfileを変更せず、既存Authorityへ重複規則を作らないことを確認する。

## History

- 2026-08-17: 原則、Authority map、監査Tool、Creation Gate、専用テストを追加した。
- 2026-08-17: 専用4件、Core全体98件、release integrityが成功し、Authority監査は問題0件だった。
- 2026-08-21: legacy identityを保持してnumberless Specへ移行した。

## Non-authority boundary

本SpecはCreation Gateの採用履歴を記録する。概念割当や新Authority作成を独自に決定せず、`GENERAL.md`と`AUTHORITY-MAP.json`を上書きしない。
