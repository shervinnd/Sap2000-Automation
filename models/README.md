# Models

Place SAP2000 `.sdb` files here, for example:

- `modelFixed.sdb`
- `m2.sdb`
- `m3.sdb`

These files are intentionally gitignored (binary + large). Point the CLI at them like:

```bash
sap2000-auto design models\modelFixed.sdb -o outputs
```
