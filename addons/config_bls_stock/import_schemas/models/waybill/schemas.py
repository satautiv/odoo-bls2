# -*- coding=utf-8 -*-

from lxml import etree
from marshmallow import fields

from ...xml_schema import XMLSchema
from ..common.schemas import (DocumentReferenceSchema, PartySchema,
                                   ShipmentSchema, ns)
from ..extensions.schemas import UBLExtensionsSchema


class WaybillSchema(XMLSchema):
    ubl_extensions = fields.Nested(
        UBLExtensionsSchema, data_key='UBLExtensions', ns=ns['ext'])
    ubl_version_id = fields.String(data_key='UBLVersionID', ns=ns['cbc'])
    id = fields.String(required=True, ns=ns['cbc'])
    uuid = fields.UUID(data_key='UUID', ns=ns['cbc'])
    issue_date = fields.Date(ns=ns['cbc'])
    issue_time = fields.Time(ns=ns['cbc'])
    note = fields.String(ns=ns['cbc'])
    consignor_party = fields.Nested(PartySchema, ns=ns['cac'])
    carrier_party = fields.Nested(PartySchema, ns=ns['cac'])
    shipment = fields.Nested(ShipmentSchema, ns=ns['cac'])
    document_reference = fields.Nested(
        DocumentReferenceSchema, many=True, ns=ns['cac'])

    class Meta:
        nsmap = {
            None: 'urn:oasis:names:specification:ubl:schema:xsd:Waybill-2',
            'cac': ns['cac'][1:-1],
            'cbc': ns['cbc'][1:-1],
            'settings': ns['settings'][1:-1],
            'ext': ns['ext'][1:-1],
        }
        root_node = etree.Element('Waybill', nsmap=nsmap)
