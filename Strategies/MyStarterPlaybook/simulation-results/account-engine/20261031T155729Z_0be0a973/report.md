# Single historical evaluation replay

Validated run: `20261025T1948510645143Z_da023b58acb14391a3d93cbeb2cf8a67`.
Input: 547 trades across 195 observed sessions.
Outcome: **breached**; data-end outcome: **breached**.
Balance: $24208.00; net P&L: $-792.00; loss floor: $24266.00.
Applied trades: 42; DLL skipped: 0; terminal ignored: 505.
Full source net after assumed commissions: $-2979.50 (validation total, not account outcome).

This is one historical replay, not a pass-rate estimate. Checks use completed trades; intratrade limit touches are excluded. The last session is not force-closed.
Details and source hashes are in `account-study.json`.
