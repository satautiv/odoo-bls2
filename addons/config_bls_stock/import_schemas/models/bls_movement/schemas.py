# -*- coding=utf-8 -*-

from lxml import etree
from marshmallow import fields

from ...xml_schema import XMLSchema
from ..common.schemas import (DeliveryCustomerPartySchema,
                                   DespatchLineSchema,
                                   DespatchSupplierPartySchema,
                                   OriginatorCustomerPartySchema,
                                   ShipmentSchema, ns)
from ..extensions.schemas import UBLExtensionsSchema


class BlsMovementSchema(XMLSchema):
    ubl_extensions = fields.Nested(
        UBLExtensionsSchema, data_key='UBLExtensions', ns=ns['ext'])
    ubl_version_id = fields.String(data_key='UBLVersionID', ns=ns['cbc'])
    id = fields.String(required=True, ns=ns['cbc'])
    uuid = fields.UUID(data_key='UUID', ns=ns['cbc'])
    issue_date = fields.Date(required=True, ns=ns['cbc'])
    issue_time = fields.Time(ns=ns['cbc'])  # TODO: include timezone?
    note = fields.String(ns=ns['cbc'])
    originator_customer_party = fields.Nested(
        OriginatorCustomerPartySchema, ns=ns['cac'])
    shipment = fields.Nested(ShipmentSchema, ns=ns['cac'])
    despatch_line = fields.Nested(
        DespatchLineSchema, required=True, many=True, ns=ns['cac'])

    class Meta:
        nsmap = {
            None: 'bls:document:schema:xsd:BlsMovement-1',
            'cac': ns['cac'][1:-1],
            'cbc': ns['cbc'][1:-1],
            'settings': ns['settings'][1:-1],
            'ext': ns['ext'][1:-1],
        }
        root_node = etree.Element('BlsMovement', nsmap=nsmap)
