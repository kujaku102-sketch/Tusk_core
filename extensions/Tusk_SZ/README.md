# Tusk SZ

Siege-Zeke固有のrenderer / UI / E2E実行アダプター。Coreへ製品機能を混ぜず、
外部ワークスペースを明示して既存コマンドを実行し、レイヤー別JSONを残す。

最初に`AGENTS.md`と`TUSK_SZ_SPEC.md`を読む。通常実行はinspectのみ。実処理は
`--apply`と現行child work itemに紐づく`--evidence-dir`が必須。
Web inspectはVite/PlaywrightをNodeで実importする読取専用probeを含む。
ファイルが存在するだけでは`ready`にしない。
