# -*- coding=utf-8 -*-

from lxml import etree
from marshmallow import fields

from ...xml_schema import XMLSchema
from ..common.schemas import (BuyerCustomerPartySchema,
                                   DeliveryCustomerPartySchema,
                                   DespatchLineSchema,
                                   DespatchSupplierPartySchema,
                                   DocumentReferenceSchema,
                                   OriginatorCustomerPartySchema,
                                   SellerSupplierPartySchema, ShipmentSchema,
                                   ns)
from ..extensions.schemas import UBLExtensionsSchema


class DespatchAdviceSchema(XMLSchema):
    ubl_extensions = fields.Nested(
        UBLExtensionsSchema, data_key='UBLExtensions', ns=ns['ext'])
    ubl_version_id = fields.String(data_key='UBLVersionID', ns=ns['cbc'])
    id = fields.String(required=True, ns=ns['cbc'])
    uuid = fields.UUID(data_key='UUID', ns=ns['cbc'])
    issue_date = fields.Date(required=True, ns=ns['cbc'])
    # issue_time = fields.Time(format='%H:%M:%S', ns=ns['cbc'])  # TODO: include timezone?
    issue_time = fields.Time(ns=ns['cbc'])  # TODO: include timezone?
    note = fields.String(ns=ns['cbc'])
    additional_document_reference = fields.Nested(
        DocumentReferenceSchema, many=True, ns=ns['cac'])

    despatch_supplier_party = fields.Nested(
        DespatchSupplierPartySchema, required=True, ns=ns['cac'])
    delivery_customer_party = fields.Nested(
        DeliveryCustomerPartySchema, required=True, ns=ns['cac'])
    buyer_customer_party = fields.Nested(
        BuyerCustomerPartySchema, ns=ns['cac'])
    seller_supplier_party = fields.Nested(
        SellerSupplierPartySchema, ns=ns['cac'])
    originator_customer_party = fields.Nested(
        OriginatorCustomerPartySchema, ns=ns['cac'])
    shipment = fields.Nested(ShipmentSchema, ns=ns['cac'])
    despatch_line = fields.Nested(
        DespatchLineSchema, required=True, many=True, ns=ns['cac'])

    class Meta:
        nsmap = {
            None: 'urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2',
            'cac': ns['cac'][1:-1],
            'cbc': ns['cbc'][1:-1],
            'settings': ns['settings'][1:-1],
            'ext': ns['ext'][1:-1],
        }
        root_node = etree.Element('DespatchAdvice', nsmap=nsmap)
