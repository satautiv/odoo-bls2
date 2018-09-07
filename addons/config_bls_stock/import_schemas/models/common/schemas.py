# -*- coding=utf-8 -*-

import decimal

from marshmallow import fields

from ...xml_schema import XMLSchema

# namespaces
ns = {
    # common
    # 'xades': r'{http://uri.etsi.org/01903/v1.3.2#}',
    # 'ds': r'{http://www.w3.org/2000/09/xmldsig#}',
    # 'ccts-cct': r'{urn:un:unece:uncefact:data:specification:CoreComponentTypeSchemaModule:2}',

    # oasis
    'cac': r'{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}',
    'cbc': r'{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}',
    'waybill': r'{urn:oasis:names:specification:ubl:schema:xsd:Waybill-2}',
    # 'udt': r'{urn:oasis:names:specification:ubl:schema:xsd:UnqualifiedDataTypes-2}',
    # 'qdt': r'{urn:oasis:names:specification:ubl:schema:xsd:QualifiedDataTypes-2}',
    # 'settings': r'{urn:oasis:names:specification:ubl:schema:xsd:Settings-1}',
    'order': r'{urn:oasis:names:specification:ubl:schema:xsd:Order-2}',
    # 'n0': r'{urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2}',
    # 'n1': r'{urn:oasis:names:specification:ubl:schema:xsd:documents}',
    'invoice': r'{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}',
    'ext': r'{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}',
    # 'documentstatus': r'{urn:oasis:names:specification:ubl:schema:xsd:DocumentStatus-2}',

    # bls
    'settings': r'{bls:document:schema:xsd:Settings-1}'
    # 'blscbc': r'{bls:document:lib:schema:xsd:CommonBasicComponents-1}',
    # 'print': r'{bls:document:schema:xsd:PrintSettings-1}',
    # 'actionhistory': r'{bls:document:schema:xsd:ActionHistory-1}',
}


class AddressLineSchema(XMLSchema):
    line = fields.String(ns=ns['cbc'])


class CountrySchema(XMLSchema):
    identification_code = fields.String(ns=ns['cbc'])
    name = fields.String(ns=ns['cbc'])


class AddressDetailSchema(XMLSchema):
    postbox = fields.String(ns=ns['cbc'])
    room = fields.String(ns=ns['cbc'])
    street_name = fields.String(ns=ns['cbc'])
    building_number = fields.String(ns=ns['cbc'])
    city_name = fields.String(ns=ns['cbc'])
    region = fields.String(ns=ns['cbc'])
    address_line = fields.Nested(AddressLineSchema, many=True, ns=ns['cac'])
    country = fields.Nested(CountrySchema, ns=ns['cac'])


class AddressSchema(XMLSchema):
    address = fields.Nested(AddressDetailSchema, ns=ns['cac'])


class SubsidiaryLocationSchema(XMLSchema):
    name = fields.String(ns=ns['cbc'])


class LocationSchema(XMLSchema):
    id = fields.String(ns=ns['cbc'])
    scheme_id = fields.String(attribute_for='id')
    scheme_name = fields.String(attribute_for='id')
    scheme_agency_id = fields.String(attribute_for='id')
    name = fields.String(ns=ns['cbc'])
    address = fields.Nested(AddressDetailSchema, ns=ns['cac'])
    subsidiary_location = fields.Nested(SubsidiaryLocationSchema, ns=ns['cac'])


class DeliveryPeriodSchema(XMLSchema):
    start_date = fields.Date(ns=ns['cbc'])
    start_time = fields.Time(ns=ns['cbc'])
    end_date = fields.Date(ns=ns['cbc'])
    end_time = fields.Time(ns=ns['cbc'])


class TaxSchemeSchema(XMLSchema):
    id = fields.String(ns=ns['cbc'])
    name = fields.String(ns=ns['cbc'])
    tax_type_code = fields.String(ns=ns['cbc'])
    currency_code = fields.String(ns=ns['cbc'])


class CorporateRegistrationSchemeSchema(XMLSchema):
    id = fields.String(required=True, ns=ns['cbc'])
    name = fields.String(ns=ns['cbc'])
    corporate_registration_type_code = fields.String(ns=ns['cbc'])
    list_id = fields.String(attribute_for='corporate_registration_type_code')


class FinancialInsitutionSchema(XMLSchema):
    id = fields.String(required=True, ns=ns['cbc'])
    name = fields.String(ns=ns['cbc'])


class FinancialInsitutionBranchSchema(XMLSchema):
    financial_institution = fields.Nested(
        FinancialInsitutionSchema, ns=ns['cac'])


class FinancialAccountSchema(XMLSchema):
    id = fields.String(required=True, ns=ns['cbc'])
    name = fields.String(ns=ns['cbc'])
    account_type_code = fields.String(ns=ns['cbc'])
    account_format_code = fields.String(ns=ns['cbc'])
    currency_code = fields.String(ns=ns['cbc'])
    payment_note = fields.String(ns=ns['cbc'])
    financial_institution_branch = fields.Nested(
        FinancialInsitutionBranchSchema, ns=ns['cac'])
    country = fields.Nested(CountrySchema, ns=ns['cac'])


class PartyTaxSchemeSchema(XMLSchema):
    registration_name = fields.String(ns=ns['cbc'])
    company_id = fields.String(ns=ns['cbc'])
    scheme_id = fields.String(attribute_for='company_id')
    tax_scheme = fields.Nested(TaxSchemeSchema, ns=ns['cac'])


class PartyLegalEntitySchema(XMLSchema):
    registration_name = fields.String(ns=ns['cbc'])
    registration_date = fields.Date(ns=ns['cbc'])
    registration_expiration_date = fields.Date(ns=ns['cbc'])
    company_id = fields.String(ns=ns['cbc'])
    scheme_id = fields.String(attribute_for='company_id')
    registration_address = fields.Nested(AddressDetailSchema, ns=ns['cac'])
    corporate_registration_scheme = fields.Nested(
        CorporateRegistrationSchemeSchema, ns=ns['cac'])


class PartyIdentificationSchema(XMLSchema):
    id = fields.String(required=True, ns=ns['cbc'])
    scheme_id = fields.String(attribute_for='id')
    scheme_name = fields.String(attribute_for='id')
    scheme_agency_id = fields.String(attribute_for='id')


class PartyNameSchema(XMLSchema):
    name = fields.String(required=True, ns=ns['cbc'])


class PartySchema(XMLSchema):
    logo_reference_id = fields.String(ns=ns['cbc'])
    party_identification = fields.Nested(
        PartyIdentificationSchema, many=True, ns=ns['cac'])
    party_name = fields.Nested(PartyNameSchema, ns=ns['cac'])
    physical_location = fields.Nested(AddressSchema, ns=ns['cac'])
    party_tax_scheme = fields.Nested(PartyTaxSchemeSchema, ns=ns['cac'])
    party_legal_entity = fields.Nested(
        PartyLegalEntitySchema, many=True, ns=ns['cac'])
    financial_account = fields.Nested(FinancialAccountSchema, ns=ns['cac'])


class SellerSupplierPartySchema(XMLSchema):
    party = fields.Nested(PartySchema, ns=ns['cac'])


class BuyerCustomerPartySchema(XMLSchema):
    party = fields.Nested(PartySchema, ns=ns['cac'])


class AccountingSupplierPartySchema(XMLSchema):
    party = fields.Nested(PartySchema, ns=ns['cac'])


class AccountingCustomerPartySchema(XMLSchema):
    party = fields.Nested(PartySchema, ns=ns['cac'])


class OriginatorCustomerPartySchema(XMLSchema):
    party = fields.Nested(PartySchema, ns=ns['cac'])


class DespatchSupplierPartySchema(XMLSchema):
    party = fields.Nested(PartySchema, ns=ns['cac'])


class DeliveryCustomerPartySchema(XMLSchema):
    party = fields.Nested(PartySchema, ns=ns['cac'])


class AdditionalItemPropertySchema(XMLSchema):
    name = fields.String(required=True, ns=ns['cbc'])
    value = fields.String(ns=ns['cbc'])
    importance_code = fields.String(ns=ns['cbc'])


class LotIdentificationSchema(XMLSchema):
    lot_number = fields.String(data_key='LotNumberID', ns=ns['cbc'])
    expiry_date = fields.Date(ns=ns['cbc'])


class PaymentMeansSchema(XMLSchema):
    payment_means_code = fields.String(ns=ns['cbc'])
    payment_channel_code = fields.String(ns=ns['cbc'])


class PaymentTermsSchema(XMLSchema):
    payment_means_id = fields.String(ns=ns['cbc'])
    ammount = fields.Decimal(
        places=4, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    amount_currency_code = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='amount')


class AllowanceChargeSchema(XMLSchema):
    charge_indicator = fields.Boolean(ns=ns['cbc'])
    allowance_charge_reason = fields.String(ns=ns['cbc'])
    multiplier_factor_numeric = fields.Decimal(ns=ns['cbc'])
    amount = fields.Decimal(
        places=4, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    amount_currency_code = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='amount')
    base_amount = fields.Decimal(
        places=4, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    base_amount_currency_code = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='base_amount')
    per_unit_amount = fields.Decimal(
        places=4, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    per_unit_amount_currency_code = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='per_unit_amount')


class DespatchSchema(XMLSchema):
    despatch_location = fields.Nested(LocationSchema, ns=ns['cac'])


class DeliverySchema(XMLSchema):
    delivery_location = fields.Nested(LocationSchema, ns=ns['cac'])
    alternative_delivery_location = fields.Nested(AddressSchema, ns=ns['cac'])
    promised_delivery_period = fields.Nested(
        DeliveryPeriodSchema, ns=ns['cac'])
    estimated_delivery_period = fields.Nested(
        DeliveryPeriodSchema, ns=ns['cac'])
    actual_delivery_date = fields.Date(ns=ns['cbc'])
    actual_delivery_time = fields.Time(ns=ns['cbc'])
    carrier_party = fields.Nested(PartySchema, ns=ns['cac'])
    despatch = fields.Nested(DespatchSchema, ns=ns['cac'])


class PriceSchema(XMLSchema):
    price_amount = fields.Decimal(
        places=4, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    price_amount_currency_code = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='price_amount')
    base_quantity = fields.Decimal(
        places=3, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    base_quantity_unit_code = fields.String(
        data_key='unitCode', attribute_for='base_quantity')
    allowance_charge = fields.Nested(AllowanceChargeSchema, ns=ns['cac'])


class ItemIdentification(XMLSchema):
    id = fields.String(required=True, ns=ns['cbc'])
    scheme_id = fields.String(attribute_for='id')
    scheme_name = fields.String(attribute_for='id')
    scheme_agency_id = fields.String(attribute_for='id')
    barcode_symbology_id = fields.String(ns=ns['cbc'])


class CommodityIdentification(XMLSchema):
    item_classification_code = fields.String(required=True, ns=ns['cbc'])


class ValidityPeriodSchema(XMLSchema):
    start_date = fields.Date(ns=ns['cbc'])
    end_date = fields.Date(ns=ns['cbc'])


class DocumentReferenceSchema(XMLSchema):
    id = fields.String(required=True, ns=ns['cbc'])
    uuid = fields.UUID(data_key='UUID', ns=ns['cbc'])
    issue_date = fields.Date(ns=ns['cbc'])
    issue_time = fields.Time(ns=ns['cbc'])
    document_type = fields.String(ns=ns['cbc'])
    version_id = fields.String(ns=ns['cbc'])
    validity_period = fields.Nested(ValidityPeriodSchema, ns=ns['cac'])


class CertificateSchema(XMLSchema):
    id = fields.String(ns=ns['cbc'])
    certificate_type_code = fields.String(required=True, ns=ns['cbc'])
    certificate_type = fields.String(required=True, ns=ns['cbc'])
    issuer_party = fields.Nested(PartySchema, ns=ns['cac'])
    document_reference = fields.Nested(DocumentReferenceSchema, ns=ns['cac'])


class ItemInstanceSchema(XMLSchema):
    additional_item_property = fields.Nested(
        AdditionalItemPropertySchema, many=True, ns=ns['cac'])
    lot_identification = fields.Nested(LotIdentificationSchema, ns=ns['cac'])


# class ItemDescriptionSchema(XMLSchema):
#     description = fields.String(required=True, ns=ns['cbc'])
#     language_id = fields.String(attribute_for='description')


class ItemSchema(XMLSchema):
    # description = fields.Nested(
    #     ItemDescriptionSchema, required=True, many=True, inline=True, ns=ns['cbc'])

    description = fields.String(required=True, ns=ns['cbc'])
    language_id = fields.String(attribute_for='description')

    buyers_item_identification = fields.Nested(
        ItemIdentification, ns=ns['cac'])
    sellers_item_identification = fields.Nested(
        ItemIdentification, ns=ns['cac'])
    manufacturers_item_identification = fields.Nested(
        ItemIdentification, ns=ns['cac'])
    standard_item_identification = fields.Nested(
        ItemIdentification, ns=ns['cac'])
    additional_item_identification = fields.Nested(
        ItemIdentification, many=True, ns=ns['cac'])
    commodity_classification = fields.Nested(
        CommodityIdentification, many=True, ns=ns['cac'])
    item_instance = fields.Nested(ItemInstanceSchema, ns=ns['cac'])
    certificate = fields.Nested(CertificateSchema, many=True, ns=ns['cac'])


class TaxCategorySchema(XMLSchema):
    percent = fields.Decimal(
        places=2, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    tax_scheme = fields.Nested(TaxSchemeSchema, required=True, ns=ns['cac'])


class TaxSubtotalSchema(XMLSchema):
    taxable_amount = fields.Decimal(
        places=2, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    taxable_currency = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='taxable_amount')
    tax_amount = fields.Decimal(required=True, ns=ns['cbc'])
    tax_currency = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='tax_amount')
    percent = fields.Decimal(
        places=2, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    tax_category = fields.Nested(
        TaxCategorySchema, required=True, ns=ns['cac'])


class TaxTotalSchema(XMLSchema):
    tax_amount = fields.Decimal(required=True, ns=ns['cbc'])
    tax_currency = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='tax_amount')
    rounding_amount = fields.Decimal(
        places=4, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    rounding_currency = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='rounding_amount')
    tax_subtotal = fields.Nested(TaxSubtotalSchema, many=True, ns=ns['cac'])


class ConsignmentSchema(XMLSchema):
    id = fields.String(required=True, ns=ns['cbc'])
    consignment_quantity = fields.Decimal(ns=ns['cbc'])
    consignment_quantity_unit_code = fields.String(
        attribute_for='consignment_quantity', data_key='unitCode')
    handling_code = fields.String(ns=ns['cbc'])


class RoadTransportSchema(XMLSchema):
    license_plate_id = fields.String(ns=ns['cbc'])
    scheme_id = fields.String(attribute_for='license_plate_id')


class TransportMeansSchema(XMLSchema):
    road_transport = fields.Nested(RoadTransportSchema, ns=ns['cac'])


class TransportHandlingUnitSchema(XMLSchema):
    transport_means = fields.Nested(
        TransportMeansSchema, many=True, ns=ns['cac'])


class OrderReferenceSchema(XMLSchema):
    id = fields.String(required=True, ns=ns['cbc'])
    uuid = fields.UUID(data_key='UUID', ns=ns['cbc'])
    sales_order_id = fields.String(ns=ns['cbc'])


class OrderLineReferenceSchema(XMLSchema):
    line_id = fields.String(required=True, ns=ns['cbc'])
    sales_order_line_id = fields.String(ns=ns['cbc'])
    order_reference = fields.Nested(OrderReferenceSchema, ns=ns['cac'])


class DespatchLineReferenceSchema(XMLSchema):
    line_id = fields.String(required=True, ns=ns['cbc'])
    document_reference = fields.Nested(DocumentReferenceSchema, ns=ns['cac'])


class LegalMonetaryTotalSchema(XMLSchema):
    line_extension_amount = fields.Decimal(
        places=2, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    line_extension_amount_currency_code = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='line_extension_amount')
    tax_exclusive_amount = fields.Decimal(
        places=2, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    tax_exclusive_amount_currency_code = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='tax_exclusive_amount')
    tax_inclusive_amount = fields.Decimal(
        places=2, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    tax_inclusive_amount_currency_code = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='tax_inclusive_amount')
    allowance_total_amount = fields.Decimal(
        places=2, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    allowance_total_amount_currency_code = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='allowance_total_amount')
    charge_total_amount = fields.Decimal(
        places=2, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    charge_total_amount_currency_code = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='charge_total_amount')
    prepaid_amount = fields.Decimal(
        places=2, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    prepaid_amount_currency_code = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='prepaid_amount')
    payable_rounding_amount = fields.Decimal(
        places=2, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    payable_rounding_amount_currency_code = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='payable_rounding_amount')
    payable_amount = fields.Decimal(
        places=2, rounding=decimal.ROUND_HALF_UP, required=True, ns=ns['cbc'])
    payable_amount_currency_code = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='payable_amount')


class InvoiceLineSchema(XMLSchema):
    id = fields.String(required=True, ns=ns['cbc'])
    invoiced_quantity = fields.Decimal(
        places=3, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    invoiced_quantity_unit_code = fields.String(
        attribute_for='invoiced_quantity', data_key='unitCode')
    line_extension_amount = fields.Decimal(
        places=2, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    line_extension_amount_currency_code = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='line_extension_amount')
    order_line_reference = fields.Nested(
        OrderLineReferenceSchema, many=True, ns=ns['cac'])
    despatch_line_reference = fields.Nested(
        DespatchLineReferenceSchema, many=True, ns=ns['cac'])
    delivery = fields.Nested(DeliverySchema, ns=ns['cac'])
    tax_total = fields.Nested(TaxTotalSchema, ns=ns['cac'])
    item = fields.Nested(ItemSchema, ns=ns['cac'])
    price = fields.Nested(PriceSchema, ns=ns['cac'])
    sub_invoice_line = fields.Nested(
        'InvoiceLineSchema', many=True, exclude=('sub_invoice_line',), ns=ns['cac'])


class GoodsItemSchema(XMLSchema):
    id = fields.String(ns=ns['cbc'])
    quantity = fields.Decimal(
        places=3, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    quantity_unit_code = fields.String(
        attribute_for='quantity', data_key='unitCode')
    item = fields.Nested(ItemSchema, ns=ns['cac'])
    invoice_line = fields.Nested(InvoiceLineSchema, many=True, ns=ns['cac'])
    contained_goods_item = fields.Nested(
        'GoodsItemSchema', many=True, exclude=('contained_goods_item',), ns=ns['cac'])


class ShipmentSchema(XMLSchema):
    id = fields.String(required=True, ns=ns['cbc'])
    consignment = fields.Nested(ConsignmentSchema, many=True, ns=ns['cac'])
    goods_item = fields.Nested(GoodsItemSchema, many=True, ns=ns['cac'])
    delivery = fields.Nested(DeliverySchema, ns=ns['cac'])
    transport_handling_unit = fields.Nested(
        TransportHandlingUnitSchema, ns=ns['cac'])


class CreditNoteLineSchema(XMLSchema):
    id = fields.String(required=True, ns=ns['cbc'])
    credited_quantity = fields.Decimal(
        places=3, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    credited_quantity_unit_code = fields.String(
        attribute_for='credited_quantity', data_key='unitCode')
    line_extension_amount = fields.Decimal(
        places=2, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    line_extension_amount_currency_code = fields.Constant(
        'EUR', data_key='currencyID', attribute_for='line_extension_amount')
    order_line_reference = fields.Nested(
        OrderLineReferenceSchema, ns=ns['cac'])
    delivery = fields.Nested(DeliverySchema, ns=ns['cac'])
    tax_total = fields.Nested(TaxTotalSchema, ns=ns['cac'])
    item = fields.Nested(ItemSchema, ns=ns['cac'])
    price = fields.Nested(PriceSchema, ns=ns['cac'])
    sub_credit_note_line = fields.Nested(
        'CreditNoteLineSchema', many=True, exclude=('sub_credit_note_line',), ns=ns['cac'])


class DespatchLineSchema(XMLSchema):
    id = fields.String(required=True, ns=ns['cbc'])
    delivered_quantity = fields.Decimal(
        places=3, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    delivered_quantity_unit_code = fields.String(
        attribute_for='delivered_quantity', data_key='unitCode')
    order_line_reference = fields.Nested(
        OrderLineReferenceSchema, required=True, many=True, ns=ns['cac'])
    item = fields.Nested(ItemSchema, ns=ns['cac'])
    shipment = fields.Nested(ShipmentSchema, ns=ns['cac'])


class ReceiptLineSchema(XMLSchema):
    id = fields.String(required=True, ns=ns['cbc'])
    received_quantity = fields.Decimal(
        places=3, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    received_quantity_unit_code = fields.String(
        attribute_for='received_quantity', data_key='unitCode')
    rejected_quantity = fields.Decimal(
        places=3, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    rejected_quantity_unit_code = fields.String(
        attribute_for='rejected_quantity', data_key='unitCode')
    reject_reason_code = fields.String(ns=ns['cbc'])
    reject_reason = fields.String(ns=ns['cbc'])
    reject_action_code = fields.String(ns=ns['cbc'])
    oversupply_quantity = fields.Decimal(
        places=3, rounding=decimal.ROUND_HALF_UP, ns=ns['cbc'])
    oversupply_quantity_unit_code = fields.String(
        attribute_for='oversupply_quantity', data_key='unitCode')
    received_date = fields.Date(ns=ns['cbc'])
    timing_complaint_code = fields.String(ns=ns['cbc'])
    order_line_reference = fields.Nested(
        OrderLineReferenceSchema, required=True, ns=ns['cac'])
    despatch_line_reference = fields.Nested(
        DespatchLineReferenceSchema, required=True, ns=ns['cac'])
    item = fields.Nested(ItemSchema, ns=ns['cac'])
    shipment = fields.Nested(ShipmentSchema, ns=ns['cac'])
