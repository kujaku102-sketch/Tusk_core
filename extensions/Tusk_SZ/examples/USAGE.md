# Usage examples

Read-only web inspection:

```powershell
python tools/tusk_sz.py --profile web --workspace D:\projects\txt-analyze\simple-zeke --probe-timeout 10
```

Read-only Illustrator inspection:

```powershell
python tools/tusk_sz.py --profile illustrator --workspace D:\projects\siege-zeke
```

Real web evidence run:

```powershell
python tools/tusk_sz.py --profile web `
  --workspace D:\projects\txt-analyze\simple-zeke `
  --evidence-dir <workspace-root>\work\runs\<RUN-ID>\web `
  --probe-timeout 10 --build-timeout 180 --scenario-timeout 180 --apply
```

Real Illustrator run (only after the template exists):

```powershell
python tools/tusk_sz.py --profile illustrator `
  --workspace D:\projects\siege-zeke --card-id STD-127 `
  --evidence-dir <workspace-root>\work\runs\<RUN-ID>\illustrator --apply
```
