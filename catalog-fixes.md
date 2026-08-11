# Installed-catalog fixes

Edits applied directly to generator/vulnerability packs **as installed** under
`scenarioforge/outputs/installed_*`. That tree is `.gitignore`d (see
`.gitignore:136`, `outputs/`), so these edits live only on this machine's
filesystem — they are not in either git repo and **do not survive reinstalling
or re-importing the pack**. They must be reapplied by hand afterwards.

Same class of problem as `docker-fixes.md`, different layer: that file covers
the CORE emulator package on the CORE VM, this one covers ScenarioForge's
installed catalog content on the machine running the evaluator.

These *do* reach the CORE VM without extra work: each run's
"synced runtime subset (core package/runner/generators)" step copies the
installed generators from here to the VM, so editing the local copy is enough.

---

## 1. `https_token_debug_api` — unusable as the first step of any chain

**Pack:** `flag_node_generators/http`, pack id `07-01-26-15-10-01-6de4d6`
**File:** `outputs/installed_generators/flag_node_generators/p_07-01-26-15-10-01-6de4d6__64/manifest.yaml`
**Backup of the pre-edit file:** `manifest.yaml.orig` (same directory)

### Symptom

A run whose chain opens with this generator fails in flag-sequencing, before
any generator executes:

```
Flow validation failed before generator execution: 5: first chain step needs
['TOKEN'] to follow its access instructions, but its low hints never reveal
them; nothing earlier in the chain can supply them either. Promote the
disclosing hint to 'low' or place this generator later in the chain.
```

Seen on `dataset-artifact-web-delivery_run04`. Any length-1 chain that selects
this generator hits it, because in a one-step chain every step is the first.
Longer chains hit it only when the solver happens to place it at position 0.

### Root cause

Step 1 of the generator's own access instructions is:

```bash
curl -k 'https://{{NODE}}:{{PORT}}/api/profile?token={{TOKEN}}'
```

`{{TOKEN}}` maps to the fact `Token(service)` (see
`_ACCESS_SECRET_PLACEHOLDER_FACTS` in `webapp/app_backend.py`). A hint counts as
*disclosing* a fact only when it contains an `{{OUTPUT.<Fact>}}` placeholder
(`_flow_hint_disclosed_facts`). This generator's hints carried no such
placeholder for `Token(service)` at **any** level — the only one present was
`{{OUTPUT.File(path):basename}}` at `medium`, which discloses `File(path)`.

So the token was unobtainable when this generator opened a chain. Note the
runtime already tries to fix this automatically:
`_flow_promote_first_step_hint_levels` copies a deeper disclosing hint up into
`low` for position 0. It could not help here because there was no disclosing
line anywhere to promote.

### Fix applied

Added one line to `hint_levels.low`:

```yaml
- 'Debug token: {{OUTPUT.Token(service)}}'
```

This is the same remedy the validator's own error message recommends
("Promote the disclosing hint to 'low'"), except the line had to be written
rather than moved, since none existed. It makes the challenge marginally
easier — the token artifact is now named at the lowest hint level — which is
the intended trade: the alternative is a challenge nobody can enter.

Preferred over re-seeding the affected dataset run. A retry seed fixes one
run; this fixes the generator for every seed and every dataset that selects
it. Re-seeding also perturbs `materialize_catalog_selections.py`'s global
balancing, which rewrites unrelated specs and invalidates their existing
results (measured: one retry seed changed 27 specs, 21 of which had results).

### Verifying it

The check is pure metadata, no run required:

```bash
cd scenarioforge && python3 - <<'PY'
import yaml, re
M = "outputs/installed_generators/flag_node_generators/p_07-01-26-15-10-01-6de4d6__64/manifest.yaml"
g = yaml.safe_load(open(M))
RE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")
canon = lambda f: re.sub(r"\s+", "", f).lower()
low = g.get("hint_levels", {}).get("low") or []
disclosed = {canon(t.split(".", 1)[1]) for line in low
             for t in RE.findall(str(line)) if t.upper().startswith("OUTPUT.")}
print("Token(service) disclosed at low:", canon("Token(service)") in disclosed)
PY
```

Prints `True` when the fix is in place. End-to-end, re-running
`dataset-resolved/20-artifact-web-delivery-run04.spec.yaml` should reach
`flag_sequencing: PASS` with its original seed (`1186340165`, selecting
`https_token_debug_api`).

### Finding others like it

Worth checking whether other generators demand a secret their hints never
disclose. The test is **not** "does `low` disclose it" — that flags 33 of the
34 secret-gated generators in this catalog, nearly all false positives,
because `_flow_promote_first_step_hint_levels` copies a disclosing line from
`medium`/`high` into `low` at position 0. A generator is only broken when
*no* level discloses the fact, leaving promotion nothing to work with:

```bash
cd scenarioforge && python3 - <<'PY'
import glob, re, yaml
ALT = {
 'USERNAME': ('Credential(user, password)','Credential(user)'),
 'USER': ('Credential(user, password)','Credential(user)'),
 'PASSWORD': ('Credential(user, password)','Credential(user, hash)'),
 'PASS': ('Credential(user, password)','Credential(user, hash)'),
 'HASH': ('Credential(user, hash)',),
 'TOKEN': ('Token(service)',),
 'APIKEY': ('APIKey(service)',), 'API_KEY': ('APIKey(service)',),
 'SECRET': ('ExposedSecret(service)',),
 'PASSPHRASE': ('DecryptionKey(id)','Credential(user, password)'),
 'DECRYPTION_KEY': ('DecryptionKey(id)',),
 'KEY': ('DecryptionKey(id)','APIKey(service)'),
}
RE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")
canon = lambda f: re.sub(r"\s+", "", f).lower()
for m in glob.glob("outputs/installed_generators/*/*/manifest.yaml"):
    g = yaml.safe_load(open(m)) or {}
    access = yaml.safe_dump(g.get("access_instructions") or {})
    needed = {t.strip().upper() for t in RE.findall(access)} & set(ALT)
    if not needed:
        continue
    hl = g.get("hint_levels") or {}
    seen = {canon(t.split(".", 1)[1])
            for lv in ("low", "medium", "high")
            for line in (hl.get(lv) or [])
            for t in RE.findall(str(line)) if t.upper().startswith("OUTPUT.")}
    missing = [n for n in sorted(needed) if not ({canon(a) for a in ALT[n]} & seen)]
    if missing:
        print(f"{g.get('id') or m}: needs {missing}, no level discloses them")
PY
```

Last run over 147 manifests: 34 secret-gated, 33 rescued by promotion, and
`https_token_debug_api` the only genuine break — now fixed, so the sweep
should print nothing.

---

## 2. Comma-split facts across 32 of 87 generator manifests

**Files:** `outputs/installed_generators/*/*/manifest.yaml`
**Backups:** `manifest.yaml.prefacts` beside each repaired file
**Repair script:** `scripts/repair_generator_manifest_facts.py` (idempotent)

### Symptom

Dependency analysis reports requirements nothing can satisfy, and generators
appear to produce facts no one consumes. Chains that look unsolvable are
really being compared against fact names that do not exist.

### Root cause

A fact name may contain a comma — `Credential(user, password)`,
`PortForward(host, port)`, `Directory(host, path)`. In the packs installed
here, each of those was stored as *two* entries, split on that comma. Two
shapes occur:

```yaml
artifacts:
  requires:
  - Knowledge(ip)
  - Credential(user       # one fact, split
  - password)

inputs:
- name: Credential(user
  password): null         # tail became a stray mapping key
  type: string
```

Not produced by the current code: `_split_artifact_list` was checked against
list, dict, newline and comma-separated inputs and preserves commas in every
case. This is damage carried inside the packs (installed 2026-07-01), from an
older importer or the upstream export.

It matters because a fragment never matches a real producer.
`_normalize_fact_names` does not rejoin them either, so `Credential(user` and
`password)` reach chain validation as two distinct, unsatisfiable facts.

### Fix applied

`scripts/repair_generator_manifest_facts.py --sf-path ../scenarioforge --apply`

Rejoins any entry whose parentheses are unbalanced with the entries that
follow, until balanced; handles the stray-mapping-key shape as well. Backs up
each file it touches and is safe to re-run.

### Effect (measured)

| | before | after |
|---|---|---|
| manifests with split facts | 32 / 87 | 0 |
| `Credential(user, password)` producers | fragmented | 36 |
| `PortForward(host, port)` producers | fragmented | 87 |
| required facts with no producer anywhere | several phantoms | `Ticket(id)` only |

### Remaining, and not a repair job

`Ticket(id)` has **zero** producers in the catalog, so any generator requiring
it cannot be satisfied by any chain. That is a catalog gap — either add a
generator that produces it, or stop selecting its consumers — and no amount of
solver or dataset work fixes it.

### Verifying

```bash
python3 scripts/repair_generator_manifest_facts.py --sf-path ../scenarioforge
```

Prints `0 need repair` when the catalog is clean.
