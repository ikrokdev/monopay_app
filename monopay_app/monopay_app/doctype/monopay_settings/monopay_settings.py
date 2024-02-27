# Copyright (c) 2024, iKrok and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document

from monopay import MonoPay
from monopay.utils import webhook_authentication

from decimal import Decimal


class MonoPaySettings(Document):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monopay = MonoPay(api_token=self.get_password(fieldname="token", raise_exception=False))
        self.logger = frappe.logger()
        
    def validate_transaction_currency(self, currency):
        if currency not in ["UAH", "USD", "EUR"]:
            raise ValueError
    
    def validate_minimum_transaction_amount(self, currency, amount):
        if amount <= 1:
            raise ValueError(f"Invalid Transaction Amount. Minimum is 1, current: {amount}")
        
    def get_payment_url(
        self,
        order_id: str,
        amount,
        title: str = "Default Title",
        description: str = "",
        currency: str = "UAH",
        product_name: str = None,
        product_url: str = None,
        **kwargs                    
    ):
        
        ccy_dict:dict[str, int] = {
			"UAH": 980,
			"USD": 840,
            "EUR": 978
		} 
        currency_code = ccy_dict.get(currency)
        
        if not currency_code:
            raise ValueError(f"Unsupported currency provided, {currency} is not supported. Possible values: {list(ccy_dict)}")
        
        payment_request = frappe.get_doc("Payment Request", {'name': order_id})
        sales_order_name = payment_request.reference_name
        
        invoice = self.monopay.invoice.create(
			amount = int(Decimal(amount) * 100),
            # web_hook_url=f"http://91.236.250.201:8000/api/method/monopay_app.monopay_app.doctype.monopay_settings.monopay_settings.callback_handler",
            web_hook_url=f"{frappe.utils.get_url() if not self.webhook_url else self.webhook_url}/api/method/monopay_app.monopay_app.doctype.monopay_settings.monopay_settings.callback_handler",
            # redirect_url=f"{frappe.utils.get_url('orders')}/{sales_order_name}",
            redirect_url=f"{frappe.utils.get_url('orders')}/{sales_order_name}" if not self.redirect_url else self.redirect_url,
            ccy=currency_code
		)
        
        cache = frappe.cache()
        
        cache.hset("mono_invoices", invoice.invoice_id, payment_request.name)
        print(invoice)
        
        return invoice.page_url


@frappe.whitelist(allow_guest=True, methods=["POST"])
def callback_handler():
    mono = frappe.get_single("MonoPay Settings")
    monopay: MonoPay = MonoPay(api_token=mono.get_password(fieldname="token", raise_exception=False))
    
    pub_key = monopay.merchant.pubkey().key
    sign = frappe.request.headers.get('X-Sign')
    body = frappe.request.data.decode('utf-8')
    
    verified = webhook_authentication(pub_key, sign, body)
    print(verified)
    data = json.loads(body)
    status = data.get('status')
        
    order_id = data.get('invoiceId')
    print(data)
    print(monopay.invoice.info(order_id))
    
    if status == "success":
        print(f"Payment of order {order_id} succeed")
        
        cache = frappe.cache()
        
        payment_request_name = cache.hget("mono_invoices", order_id)
        print(payment_request_name)
        
        
        payment_request = frappe.get_doc("Payment Request", {'name': payment_request_name})
        payment_request.set_as_paid()
        
        cache.hdel("mono_invoices", order_id)
        print(f"Payment request {payment_request_name} set as paid")
        