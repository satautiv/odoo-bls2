# -*- coding=utf-8 -*-

import decimal

from lxml import etree
from marshmallow import fields

from ...xml_schema import XMLSchema
from ..common.schemas import (DeliveryCustomerPartySchema,
                                   DespatchSupplierPartySchema, ItemSchema,
                                   OriginatorCustomerPartySchema,
                                   ShipmentSchema, ns)
from ..extensions.schemas import UBLExtensionsSchema


class BlsAdjustmentLineSchema(XMLSchema):
    id = fields.String(required=True, ns=ns['cbc'])
    adjustment = fields.Decimal(
        places=3, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    adjustment_unit_code = fields.String(
        attribute_for='adjustment', data_key='unitCode')
    item = fields.Nested(ItemSchema, ns=ns['cac'])
    shipment = fields.Nested(ShipmentSchema, ns=ns['cac'])


class BlsAdjustmentSchema(XMLSchema):
    ubl_extensions = fields.Nested(
        UBLExtensionsSchema, data_key='UBLExtensions', ns=ns['ext'])
    ubl_version_id = fields.String(data_key='UBLVersionID', ns=ns['cbc'])
    id = fields.String(required=True, ns=ns['cbc'])
    uuid = fields.UUID(data_key='UUID', ns=ns['cbc'])
    issue_date = fields.Date(required=True, ns=ns['cbc'])
    issue_time = fields.Time(ns=ns['cbc'])
    note = fields.String(ns=ns['cbc'])
    despatch_supplier_party = fields.Nested(
        DespatchSupplierPartySchema, required=True, ns=ns['cac'])
    delivery_customer_party = fields.Nested(
        DeliveryCustomerPartySchema, required=True, ns=ns['cac'])
    originator_customer_party = fields.Nested(
        OriginatorCustomerPartySchema, ns=ns['cac'])
    shipment = fields.Nested(ShipmentSchema, ns=ns['cac'])
    adjustment_line = fields.Nested(
        BlsAdjustmentLineSchema, required=True, many=True, ns=ns['cac'])

    class Meta:
        nsmap = {
            None: 'bls:document:schema:xsd:BlsAdjustment-1',
            'cac': ns['cac'][1:-1],
            'cbc': ns['cbc'][1:-1],
            'settings': ns['settings'][1:-1],
            'ext': ns['ext'][1:-1],
        }
        root_node = etree.Element('BlsAdjustment', nsmap=nsmap)
