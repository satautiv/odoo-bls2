# -*- coding=utf-8 -*-

from lxml import etree
from marshmallow import fields

from ...xml_schema import XMLSchema
from ..common.schemas import (AccountingCustomerPartySchema,
                                   AccountingSupplierPartySchema,
                                   AllowanceChargeSchema,
                                   BuyerCustomerPartySchema,
                                   CreditNoteLineSchema, DeliverySchema,
                                   DocumentReferenceSchema,
                                   LegalMonetaryTotalSchema,
                                   PaymentMeansSchema, PaymentTermsSchema,
                                   SellerSupplierPartySchema, TaxTotalSchema,
                                   ns)
from ..extensions.schemas import UBLExtensionsSchema


class CreditNoteSchema(XMLSchema):
    ubl_extensions = fields.Nested(
        UBLExtensionsSchema, data_key='UBLExtensions', ns=ns['ext'])
    ubl_version_id = fields.String(data_key='UBLVersionID', ns=ns['cbc'])
    id = fields.String(required=True, ns=ns['cbc'])
    uuid = fields.UUID(data_key='UUID', ns=ns['cbc'])
    issue_date = fields.Date(ns=ns['cbc'])
    issue_time = fields.Time(ns=ns['cbc'])
    note = fields.String(ns=ns['cbc'])
    document_currency_code = fields.Constant('EUR', ns=ns['cbc'])

    additional_document_reference = fields.Nested(
        DocumentReferenceSchema, many=True, ns=ns['cac'])

    accounting_supplier_party = fields.Nested(
        AccountingSupplierPartySchema, ns=ns['cac'])
    accounting_customer_party = fields.Nested(
        AccountingCustomerPartySchema, ns=ns['cac'])
    delivery = fields.Nested(DeliverySchema, ns=ns['cac'])

    payment_means = fields.Nested(PaymentMeansSchema, ns=ns['cac'])
    payment_terms = fields.Nested(PaymentTermsSchema, ns=ns['cac'])

    allowance_charge = fields.Nested(AllowanceChargeSchema, ns=ns['cac'])
    tax_total = fields.Nested(TaxTotalSchema, ns=ns['cac'])

    legal_monetary_total = fields.Nested(
        LegalMonetaryTotalSchema, required=True, ns=ns['cac'])

    credit_note_line = fields.Nested(CreditNoteLineSchema, many=True, ns=ns['cac'])

    class Meta:
        nsmap = {
            None: 'urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2',
            'cac': ns['cac'][1:-1],
            'cbc': ns['cbc'][1:-1],
            'settings': ns['settings'][1:-1],
            'ext': ns['ext'][1:-1],
        }
        root_node = etree.Element('CreditNote', nsmap=nsmap)
