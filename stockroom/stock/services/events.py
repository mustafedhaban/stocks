# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

"""Domain event names and emit helpers — version 1 contract."""

from __future__ import annotations

import frappe

EVENT_STOCK_VOUCHER_SUBMITTED = "stock.voucher.submitted"
EVENT_STOCK_VOUCHER_CANCELLED = "stock.voucher.cancelled"
EVENT_BUY_GOODS_RECEIVED = "buy.goods.received"
EVENT_SELL_GOODS_FULFILLED = "sell.goods.fulfilled"

EVENT_VERSION = 1


def emit(event_name: str, payload: dict) -> None:
	"""Publish domain event for hooks, realtime, and future outbox."""
	payload = {**payload, "event": event_name, "event_version": EVENT_VERSION}
	frappe.publish_realtime(event_name, payload, after_commit=True)

	handlers = frappe.get_hooks("stockroom_domain_events", {}).get(event_name, [])
	for handler in handlers:
		frappe.call(handler, event=payload)


def transaction_payload(doc, stock_entry) -> dict:
	lines = [
		{
			"item_code": row.item_code,
			"qty": row.qty,
			"rate": row.rate,
			"amount": row.amount,
			"warehouse": row.warehouse,
		}
		for row in doc.items
	]
	return {
		"company": doc.company,
		"transaction_type": doc.transaction_type,
		"transaction": doc.name,
		"stock_entry": stock_entry.name,
		"party_name": doc.party_name,
		"total_amount": doc.total_amount,
		"posting_date": str(doc.posting_date),
		"lines": lines,
	}
