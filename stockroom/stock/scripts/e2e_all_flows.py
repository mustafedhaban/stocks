# Copyright (c) 2026, alool technologies and contributors
"""Run all stockroom E2E flow scripts."""

from __future__ import annotations

from stockroom.stock.scripts import (
	e2e_payment_flow,
	e2e_receive_flow,
	e2e_sell_flow,
	e2e_standard_buy_flow,
	e2e_standard_sell_flow,
)


def run(cleanup: bool = False) -> dict:
	from stockroom.stock.scripts.e2e_receive_flow import _cleanup as cleanup_e2e

	if cleanup:
		cleanup_e2e()

	results = {}
	all_pass = True

	for name, module in (
		("receive", e2e_receive_flow),
		("sell", e2e_sell_flow),
		("standard_buy", e2e_standard_buy_flow),
		("standard_sell", e2e_standard_sell_flow),
		("payment", e2e_payment_flow),
	):
		report = module.run(cleanup=False)
		results[name] = {"pass": report.get("pass"), "transaction": report.get("transaction")}
		all_pass = all_pass and bool(report.get("pass"))

	summary = {"flows": results, "pass": all_pass}
	print("\n" + "=" * 60)
	print("STOCKROOM E2E — ALL FLOWS")
	print("=" * 60)
	for name, row in results.items():
		print(f"  {'PASS' if row['pass'] else 'FAIL'} — {name}")
	print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
	print("=" * 60 + "\n")
	return summary
