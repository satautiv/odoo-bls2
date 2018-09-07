# -*- coding=utf-8 -*-

from lxml import etree
from marshmallow import fields

from ...xml_schema import XMLSchema
from ..common.schemas import (AccountingCustomerPartySchema,
                                   AccountingSupplierPartySchema,
                                   BuyerCustomerPartySchema, DeliverySchema,
                                   DocumentReferenceSchema, InvoiceLineSchema,
                                   LegalMonetaryTotalSchema,
                                   OriginatorCustomerPartySchema,
                                   SellerSupplierPartySchema, TaxTotalSchema,
                                   ns)
from ..extensions.schemas import UBLExtensionsSchema


class BlsDespatchAdviceSchema(XMLSchema):
    ubl_extensions = fields.Nested(
        UBLExtensionsSchema, data_key='UBLExtensions', ns=ns['ext'])
    ubl_version_id = fields.String(data_key='UBLVersionID', ns=ns['cbc'])
    id = fields.String(required=True, ns=ns['cbc'])
    uuid = fields.UUID(data_key='UUID', ns=ns['cbc'])
    issue_date = fields.Date(required=True, ns=ns['cbc'])
    issue_time = fields.Time(ns=ns['cbc'])
    note = fields.String(ns=ns['cbc'])
    document_currency_code = fields.Constant('EUR', ns=ns['cbc'])
    additional_document_reference = fields.Nested(
        DocumentReferenceSchema, many=True, ns=ns['cac'])

    accounting_supplier_party = fields.Nested(
        AccountingSupplierPartySchema, ns=ns['cac'])
    accounting_customer_party = fields.Nested(
        AccountingCustomerPartySchema, ns=ns['cac'])
    originator_customer_party = fields.Nested(
        OriginatorCustomerPartySchema, ns=ns['cac'])
    buyer_customer_party = fields.Nested(
        BuyerCustomerPartySchema, ns=ns['cac'])
    seller_supplier_party = fields.Nested(
        SellerSupplierPartySchema, ns=ns['cac'])
    delivery = fields.Nested(DeliverySchema, ns=ns['cac'])

    # payment_means = fields.Nested(PaymentMeansSchema, ns=ns['cac'])
    # payment_terms = fields.Nested(PaymentTermsSchema, ns=ns['cac'])

    tax_total = fields.Nested(TaxTotalSchema, ns=ns['cac'])
    legal_monetary_total = fields.Nested(
        LegalMonetaryTotalSchema, required=True, ns=ns['cac'])

    invoice_line = fields.Nested(
        InvoiceLineSchema, required=True, many=True, ns=ns['cac'])

    class Meta:
        nsmap = {
            None: 'bls:document:schema:xsd:BlsDespatchAdvice-1',
            'cac': ns['cac'][1:-1],
            'cbc': ns['cbc'][1:-1],
            'settings': ns['settings'][1:-1],
            'ext': ns['ext'][1:-1],
        }
        root_node = etree.Element('BlsDespatchAdvice', nsmap=nsmap)
