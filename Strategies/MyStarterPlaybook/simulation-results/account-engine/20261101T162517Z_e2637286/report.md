# Single historical evaluation replay

Validated run: `20261025T1948510645143Z_da023b58acb14391a3d93cbeb2cf8a67`.
Selected period: 2026-04-01 through 2026-06-30 (inclusive session dates).
Selected input: 176 trades across 63 sessions; full source has 547 trades.
Outcome: **breached**; data-end outcome: **breached**.
Balance: $23996.00; net P&L: $-1004.00; loss floor: $24000.
Applied trades: 54; DLL skipped: 0; terminal ignored: 122.
Full source net after assumed commissions: $-2979.50 (validation total, not account outcome).

This is one historical replay, not a pass-rate estimate. Checks use completed trades; intratrade limit touches are excluded. The last session is not force-closed.
Details and source hashes are in `account-study.json`.
