# -*- coding=utf-8 -*-

import decimal

from marshmallow import fields

from ...xml_schema import XMLSchema
from ..common.schemas import ns


class PutAwayStrategySchema(XMLSchema):
    parcel_company_id = fields.String(
        data_key='ParcelCompanyID', ns=ns['settings'])
    separate_picking = fields.Boolean(ns=ns['settings'])
    order_priority = fields.String(ns=ns['settings'])
    clear_after_close = fields.Boolean(ns=ns['settings'])
    pick_from_stock = fields.Boolean(ns=ns['settings'])
    pick_from_inbound = fields.Boolean(ns=ns['settings'])
    pick_from_inbound_document_id = fields.String(
        data_key='PickFromInboundDocumentID', ns=ns['settings'])
    wms_process_type = fields.String(ns=ns['settings'])


class TransportationStrategySchema(XMLSchema):
    # TODO: validuoti, nes tik kelios enum reikšmės galimos
    delivery_type = fields.String(ns=ns['settings'])
    transitional_warehouse = fields.String(ns=ns['settings'])
    handling_code = fields.String(ns=ns['settings'])
    split_order_to_few_deliveries = fields.Boolean(ns=ns['settings'])


class SettingsSchema(XMLSchema):
    document_source_id = fields.String(ns=ns['settings'])
    shipment_type = fields.String(ns=ns['settings'])
    bls_shipment_id = fields.String(
        data_key='BLSShipmentID', ns=ns['settings'])
    edi_exchange_type = fields.String(
        data_key='EDIExchangeType', ns=ns['settings'])
    details_group_by_product_parameters = fields.Boolean(ns=ns['settings'])
    details_group_by_transport_units = fields.Boolean(ns=ns['settings'])
    separate_document = fields.Boolean(ns=ns['settings'])
    document_number = fields.String(ns=ns['settings'])
    tare_total_sum = fields.Decimal(
        places=2, rounding=decimal.ROUND_HALF_UP, ns=ns['settings'])
    tare_to_total_sum = fields.Boolean(ns=ns['settings'])
    document_form_id = fields.String(ns=ns['settings'])
    note = fields.String(ns=ns['settings'])
    print_copies = fields.Integer(ns=ns['settings'])
    # TODO: validuoti galimas reikšmes
    waybill_to_wmi = fields.Integer(data_key='Waybill2VMI', ns=ns['settings'])
    one_time_customer = fields.Boolean(ns=ns['settings'])
    language_code = fields.String(ns=ns['settings'])
    movement_reason = fields.String(ns=ns['settings'])
    movement_reason_code = fields.String(ns=ns['settings'])
    adjustment_type = fields.String(ns=ns['settings'])
    document_origin = fields.String(ns=ns['settings'])
    sender_document_type = fields.String(ns=ns['settings'])
    sender_document_id = fields.String(ns=ns['settings'])
    packet_id = fields.String(ns=ns['settings'])
    document_receive_date = fields.Date(ns=ns['settings'])
    document_receive_time = fields.Time(ns=ns['settings'])
    put_away_strategy = fields.Nested(PutAwayStrategySchema, ns=ns['settings'])
    transportation_strategy = fields.Nested(
        TransportationStrategySchema, ns=ns['settings'])


class ExtensionContentSchema(XMLSchema):
    settings = fields.Nested(SettingsSchema, ns=ns['settings'])


class UBLExtensionSchema(XMLSchema):
    extension_reason_code = fields.String(ns=ns['ext'])
    extension_content = fields.Nested(ExtensionContentSchema, ns=ns['ext'])


class UBLExtensionsSchema(XMLSchema):
    ubl_extension = fields.Nested(
        UBLExtensionSchema, data_key='UBLExtension', many=True, ns=ns['ext'])
