# -*- coding=utf-8 -*-

import decimal

from lxml import etree
from marshmallow import fields

from ...xml_schema import XMLSchema
from ..common.schemas import (AccountingCustomerPartySchema,
                                   AllowanceChargeSchema,
                                   BuyerCustomerPartySchema, DeliverySchema,
                                   DocumentReferenceSchema, ItemSchema,
                                   OriginatorCustomerPartySchema,
                                   PaymentMeansSchema, PaymentTermsSchema,
                                   PriceSchema, SellerSupplierPartySchema,
                                   TaxTotalSchema, ns)
from ..extensions.schemas import UBLExtensionsSchema


class LineItemSchema(XMLSchema):
    id = fields.String(required=True, ns=ns['cbc'])
    quantity = fields.Decimal(
        places=3, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    quantity_unit_code = fields.String(
        attribute_for='quantity', data_key='unitCode')
    line_extension_amount = fields.Decimal(
        places=2, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    line_extension_amount_currency_code = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='line_extension_amount')
    total_tax_amount = fields.Decimal(
        places=2, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    total_tax_amount_currency_code = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='total_tax_amount')
    delivery = fields.Nested(DeliverySchema, ns=ns['cac'])
    price = fields.Nested(PriceSchema, ns=ns['cac'])
    item = fields.Nested(ItemSchema, ns=ns['cac'])
    sub_line_item = fields.Nested(
        'LineItemSchema', many=True, exclude=('sub_line_item',), ns=ns['cac'])
    tax_total = fields.Nested(TaxTotalSchema, ns=ns['cac'])


class OrderLineSchema(XMLSchema):
    line_item = fields.Nested(LineItemSchema, ns=ns['cac'])


class OrderSchema(XMLSchema):
    ubl_extensions = fields.Nested(
        UBLExtensionsSchema, data_key='UBLExtensions', ns=ns['ext'])
    ubl_version_id = fields.String(data_key='UBLVersionID', ns=ns['cbc'])
    id = fields.String(required=True, ns=ns['cbc'])
    uuid = fields.UUID(data_key='UUID', ns=ns['cbc'])
    issue_date = fields.Date(required=True, ns=ns['cbc'])
    issue_time = fields.Time(ns=ns['cbc'])
    order_type_code = fields.String(ns=ns['cbc'])
    note = fields.String(ns=ns['cbc'])
    requested_invoice_currency_code = fields.Constant('EUR', ns=ns['cbc'])
    document_currency_code = fields.Constant('EUR', ns=ns['cbc'])
    pricing_currency_code = fields.Constant('EUR', ns=ns['cbc'])
    tax_currency_code = fields.Constant('EUR', ns=ns['cbc'])
    additional_document_reference = fields.Nested(
        DocumentReferenceSchema, many=True, ns=ns['cac'])

    buyer_customer_party = fields.Nested(
        BuyerCustomerPartySchema, required=True, ns=ns['cac'])
    seller_supplier_party = fields.Nested(
        SellerSupplierPartySchema, required=True, ns=ns['cac'])
    originator_customer_party = fields.Nested(
        OriginatorCustomerPartySchema, ns=ns['cac'])
    accounting_customer_party = fields.Nested(
        AccountingCustomerPartySchema, ns=ns['cac'])
    delivery = fields.Nested(DeliverySchema, ns=ns['cac'])

    payment_means = fields.Nested(PaymentMeansSchema, ns=ns['cac'])
    payment_terms = fields.Nested(PaymentTermsSchema, ns=ns['cac'])

    allowance_charge = fields.Nested(AllowanceChargeSchema, ns=ns['cac'])

    order_line = fields.Nested(
        OrderLineSchema, required=True, many=True, ns=ns['cac'])

    class Meta:
        nsmap = {
            None: 'urn:oasis:names:specification:ubl:schema:xsd:Order-2',
            'cac': ns['cac'][1:-1],
            'cbc': ns['cbc'][1:-1],
            'settings': ns['settings'][1:-1],
            'ext': ns['ext'][1:-1],
        }
        root_node = etree.Element('Order', nsmap=nsmap)
