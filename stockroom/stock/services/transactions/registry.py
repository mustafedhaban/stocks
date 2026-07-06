# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

from stockroom.stock.services.transactions.quick_adjust import QuickAdjustHandler
from stockroom.stock.services.transactions.quick_receive import QuickReceiveHandler
from stockroom.stock.services.transactions.quick_sell import QuickSellHandler
from stockroom.stock.services.transactions.quick_transfer import QuickTransferHandler

_HANDLERS = {
	h.transaction_type: h()
	for h in (
		QuickReceiveHandler,
		QuickSellHandler,
		QuickAdjustHandler,
		QuickTransferHandler,
	)
}


def get_handler(transaction_type: str):
	handler = _HANDLERS.get(transaction_type)
	if not handler:
		from frappe import _

		frappe.throw(_("Unsupported transaction type: {0}").format(transaction_type))
	return handler
