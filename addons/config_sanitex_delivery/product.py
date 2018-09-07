# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo.tools.translate import _
from odoo.api import Environment
from odoo import api, models, fields, tools
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp

from .stock import get_local_time_timestamp


import threading
import json
import time
# import traceback
import logging

# from stock import ROUTE_IMPORT_CREATE_OBJECTS, ROUTE_IMPORT_UPDATE_OBJECTS

DEFAULT_PRODUCT_UNIT_XML_ID = 'product.product_uom_unit'
DEFAULT_PRODUCT_UNIT_ID = False
DEFAULT_PRODUCT_UNIT_ID_DICT = {}

PRODUCT_TAX_DICT = {}

_logger = logging.getLogger(__name__)


class ProductPacking(models.Model):
    _name = 'product.packing'
    _description = 'Packing for Products'
    
    type = fields.Selection([
        ('primary','Primary'),
        ('secondary','Secondary'),
        ('tertiary','Tertiary'),
    ], 'Type')
    neto_weight = fields.Float('Neto Weight', digits=(16, 3))
    bruto_weight = fields.Float('Bruto Weight', digits=(16, 3))
    material = fields.Char('Material', size=128)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    
    
    @api.model
    def create_if_not_exist(self, vals):
        return self.env['product.product'].create_object_if_not_exist(
            vals, self._name
        )


class ProductBarcode(models.Model):
    _name = 'product.barcode'
    _description = 'Product Barcode'
    
    type = fields.Selection([
        ('unit','Unit'),
        ('primary_packaging','Primary Packaging'),
        ('additional_packaging','Additional Packaging'),
        ('pallet_barcode','Pallet Barcode'),
    ], 'Type')
    barcode = fields.Char('Barcode', size=64)
    product_id = fields.Many2one('product.product', 'Product', readonly=True, index=True)
    
    _rec_name = 'barcode'

    @api.model
    def create_if_not_exist(self, vals):
        return self.env['product.product'].create_if_not_exist(
            vals, self._name
        )

    @api.model
    def create(self, vals):
        barcode_line = super(ProductBarcode, self).create(vals)
        if barcode_line.product_id:
            barcode_line.product_id.fill_barcode_to_show_field()
        return barcode_line

    @api.multi
    def write(self, vals):
        res = super(ProductBarcode, self).write(vals)
        if 'product_id' in vals.keys():
            self.mapped('product_id').fill_barcode_to_show_field()
        return res

class ProductOwner(models.Model):
    _name = 'product.owner'
    _description = 'Product Owner'
    
    @api.model
    def _get_languages(self):
        return [('lt', 'LT'),('ee','EE'),('lv','LV'),('ru','RU')]

    product_owner_external_id = fields.Char('External ID', size=64, readonly=True)
    owner_code = fields.Char('Owner Code', size=128, readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    name = fields.Char('Name', size=256, readonly=True)
    ref = fields.Char('Registration Code', size=64, readonly=True)
    waybill_declare_date_from = fields.Date('Waybill Declare Date From', readonly=True)
    vat = fields.Char('Vat Code', size=64, readonly=True)
    waybill_declare = fields.Boolean('Waybill Declare', default=False, readonly=True)
    active = fields.Boolean('Active', default=True, readonly=True)
    intermediate_id = fields.Many2one('stock.route.integration.intermediate', 'Created By Intermediate Obj', readonly=True)
    lang = fields.Selection(_get_languages, 'Language', readonly=True)
    load_address = fields.Char("Load Address", readonly=True)
    reg_address = fields.Char("Registration Address", readonly=True)
    registrar = fields.Char("Registrar", readonly=True)
    phone = fields.Char("Phone", readonly=True)
    logistics_phone = fields.Char("Logistics Phone", readonly=True)
    logistics_email = fields.Char("Logistics Email", readonly=True)
    fax = fields.Char("Fax", readonly=True)
    alcohol_license_type = fields.Char("Alcohol License Type", readonly=True)
    alcohol_license_sale_type = fields.Char("Alcohol License Sale Type", readonly=True)
    alcohol_license_no = fields.Char("Alcohol License No.", readonly=True)
    alcohol_license_date = fields.Date("Alcohol License Date", readonly=True)
    tobac_license_type = fields.Char("Tobac License Type", readonly=True)
    tobac_license_sale_type = fields.Char("Tobac License Sale Type", readonly=True)
    tobac_license_no = fields.Char("Tobac License No.", readonly=True)
    tobac_license_date = fields.Date("Tobac License Date", readonly=True)
    extra_text = fields.Text("Extra Text", readonly=True)
    text_invoice_end = fields.Text("Text in the Invoice End", readonly=True)
    logo = fields.Binary("Logo", attachment=True, readonly=True)
    bank_name = fields.Char("Bank Name", readonly=True)
    bank_account = fields.Char("Bank Account", readonly=True)
    id_version = fields.Char('POD Version', size=128, readonly=True)
    document_setting_line_ids = fields.One2many('document.type.settings.line', 'owner_id', 'Document Numbering Sequences')
    assign_manager_information = fields.Char('Assigned Manager Information', size=512, readonly=True)
    ignored = fields.Boolean('Ignored', default=False)
    
#     _rec_name = 'owner_code'

    @api.multi
    def get_owner_dict_for_tare_export(self, owner_type='owner'):
        owner_dict = self.get_owner_dict()
        return {
           owner_type+"CompanyCode": self and self.owner_code or '',
           owner_type+"RegCode": owner_dict['RegCode'],
           owner_type+"VatCode": owner_dict['VATCode'],
           owner_type+"RegAddress": owner_dict['RegAddress']
        }

    @api.model_cr
    def init(self):
        self.env.cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('product_owner_intermediate_id_index',))
        if not self.env.cr.fetchone():
            self.env.cr.execute('CREATE INDEX product_owner_intermediate_id_index ON product_owner (intermediate_id)')

    @api.model
    def create_owner(self, vals):
        interm_obj = self.env['stock.route.integration.intermediate']
        
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        ctx = context.copy()
        
        owner = self.with_context(ctx).search([
            ('product_owner_external_id','=',vals['product_owner_external_id'])
        ])
        
        if owner:
            own_vals = {}
        else:
            own_vals = self.default_get(self._fields)
        own_vals.update(vals)
                
        if owner:
            interm_obj.remove_same_values(owner, own_vals)
            if own_vals:
                owner.write(own_vals)
                if 'updated_owner_ids' in context:
                    context['updated_owner_ids'].append((vals['product_owner_external_id'], owner.id))
            
        else:
            own_vals['intermediate_id'] = context.get('intermediate_id', False)
            owner = self.with_context(ctx).create(own_vals)
            if 'created_owner_ids' in context:
                context['created_owner_ids'].append((vals['product_owner_external_id'], owner.id))
        if commit:
            self.env.cr.commit()
        return owner

    @api.model
    def CreateOwner(self, list_of_owner_vals):
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        inter_obj = self.env['stock.route.integration.intermediate']
        log_obj = self.env['delivery.integration.log']
        
        create_datetime = time.strftime('%Y-%m-%d %H:%M:%S')
        
        ctx_en = context.copy()
        ctx_en['lang'] = 'en_US'
        error = self.with_context(ctx_en).check_imported_owner_values(list_of_owner_vals)
        if error:
            log_vals = {
                'create_date': create_datetime,
                'function': 'CreateOwner',
                'received_information': str(json.dumps(list_of_owner_vals, indent=2)),
                'returned_information': str(json.dumps(error, indent=2))
            }
            log_obj.create(log_vals)
            return error
        
        itermediate = inter_obj.create({
            'datetime': create_datetime,
            'function': 'CreateOwner',
            'received_values': str(json.dumps(list_of_owner_vals, indent=2)),
            'processed': False
        })
        if commit:
            self.env.cr.commit()
        itermediate.process_intermediate_objects_threaded()
        return itermediate.id

    @api.model
    def check_imported_owner_values(self, list_of_client_vals):
        result = {}
        return result
    
    @api.multi
    @api.depends('name','owner_code')
    def name_get(self):
        res = []
        if not self:
            return res
        for owner in self:
            res.append((owner.id, "%s (%s)" % (owner.owner_code or '', owner.name or '')))
        return res

    @api.multi
    def get_related_partner(self):
        partner_sql = '''
            SELECT
                rp.id
            FROM
                res_partner rp,
                product_owner po 
            WHERE
                po.id = %s
                AND rp.ref=po.ref
                AND rp.active = True
                AND rp.customer=True
        '''
        partner_where = (self.id,)
        self.env.cr.execute(partner_sql, partner_where)
        partner_id, = self.env.cr.fetchone() or (False,)
        if partner_id:
            return self.env['res.partner'].browse(partner_id)
        return self.env['res.partner']


    @api.multi
    def get_owner_dict(self):
        return {
            'Name': self.name or '',
            'RegCode': self.ref or '',
            'VATCode': self.vat or self.env['res.partner'].get_vat_by_ref(self.ref) or '',
            'LoadAddress': '',
            'RegAddress': self.reg_address or '',
            'Phone': self.phone or '',
            'LogisticsPhone': self.logistics_phone or '',
            'LogisticsEMail': '',
            'Fax': self.fax or '',
        }

    @api.multi
    def owner_to_dict_for_rest(self):
        return {
            'ownerId': self.product_owner_external_id or '',
            'deleted': False, #niekada pas mus nebūna štrintas
            'shortName': self.owner_code or '', #ar tinka kodas
            'companyId': self.ref or '', #ar tinka registracijos kodas
            'companyName': self.name or '',
            'countryCode': '', #neturim šalies prie sąvininko
        }
        
    @api.model
    def create(self, vals):
        vals['id_version'] = get_local_time_timestamp()
        return super(ProductOwner, self).create(vals)
    
    @api.multi
    def write(self, vals):
        res = super(ProductOwner, self).write(vals)
        if set(vals.keys()) & {
            'product_owner_external_id', 'owner_code',
            'ref', 'name', 'active'
        }:
            self.set_version()
        return res
        
    @api.model
    def get_pod_domain(self, obj):
        return []
    
    @api.multi
    def set_version(self):
        for owner in self:
            self._cr.execute('''
                UPDATE
                    product_owner
                SET
                    id_version = %s
                WHERE id = %s
            ''', (get_local_time_timestamp(), owner.id))
        return True
    
    @api.multi
    def to_dict_for_pod_integration(self, obj):
        partner_env = self.env['res.partner']
        country_code = ""
        if self.ref:
            partner = partner_env.search([
                ('ref','=',self.ref),
                ('country_id','!=', False)
            ], limit=1)
            if partner:
                country_code = partner.country_id.code
        res = {
            'ownerId': self.product_owner_external_id or '',
            'deleted': False,
            'shortName': self.owner_code or '',
            'companyId': self.ref or '',
            'companyName': self.name or '',
            'countryCode': country_code,
            'active': self.active,
            "id_version": self.id_version,
        }
        
        return res


    @api.model
    def _search(
        self, args, offset=0, limit=None,
        order=None, count=False,
        access_rights_uid=None
    ):
        context = self.env.context or {}
        owner_ids = super(ProductOwner, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )

        if not context.get('find_ignored', False) and owner_ids and not count:
            # Čia padaryta todėl nes yra du identiški savininkai su skirtingais ID ir nors sanitexas paduoda
            # juos abu, reikia kad naudotųsi tik vienas
            owners = self.browse(owner_ids)
            ignored_owners = owners.filtered('ignored')
            if ignored_owners:
                new_owners = self.env['product.owner']
                for owner in owners:
                    if owner.ignored:
                        new_owner = self.with_context(find_ignored=False).search([
                            ('owner_code','=',owner.owner_code),
                            ('id','!=',owner.id)
                        ], limit=1)
                        if new_owner and new_owner not in new_owners:
                            new_owners += new_owner
                        elif not new_owner:
                            new_owners += owner
                    else:
                        new_owners += owner
                owners = new_owners
                owner_ids = owners.ids
        return owner_ids

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    name = fields.Char('Name', required=True, translate=False)
    
class ProductProduct(models.Model):
    _inherit = 'product.product'

    external_product_id = fields.Char('External ID', size=64, readonly=True)
    intermediate_id = fields.Many2one(
        'stock.route.integration.intermediate', 'Created by', readonly=True
    )
    type_of_product = fields.Selection([
        ('package', 'Tare'),
        ('deposit_package', 'Deposit Tare'),
        ('product', 'Product'),
        ('advertisement', 'Advertisement'),
        ('tabacco', 'Tabacco'),
        ('alcohol', 'Alcohol'),
        ('fruit', 'Fruit'),
        ('vegetable', 'Vegetable'),
    ], 'Type', default='product')
    state = fields.Selection([
        ('0', 'Normal Product'),
        ('1', 'Not Listed (to be discontinued)'),
        ('2', 'Temporarily Unavailable (Not for Sanitex fault)'),
        ('3', 'Temporarily Unavailable')
    ], 'State')
    owner_id = fields.Many2one(
        'product.owner', 'Owner',
    )
    # certificate = fields.Boolean("Certificate is Required", default=False)
    small_package_size = fields.Float("Small Package Size", digits=(12, 3))
    big_package_size = fields.Float("Big Package Size", digits=(12, 3))
#     minimal_qty_multiple = fields.Float("Minimal Quantity Multiple", digits=(12, 3))
    name_english = fields.Char('Name in English', size=128)
    name_russian = fields.Char('Name in Russian', size=128)
    weight_neto = fields.Float('Neto Weight', digits=dp.get_precision('Stock Weight'))
    weight_type = fields.Selection([
        ('variable_weight','Variable Weight'),
        ('fixed_weight','Fixed Weight'),
        ('piece_goods','Piece-Goods')
    ], 'Weight Type')
    
    related_product_id = fields.Many2one('product.product', 'Related Product')
    deposit_id = fields.Many2one('product.product', 'Deposit Product')
    deposit_qty = fields.Float('Deposit Quantity', digits=(12, 3))
    vat_tariff_id = fields.Many2one('account.tax', 'Vat Tariff', size=64)
    barcode_ids = fields.One2many('product.barcode', 'product_id', 'Barcodes')
    packing_ids = fields.One2many('product.packing', 'product_id', 'Packings')
    barcode_to_show = fields.Char("Barcode", size=64)
    average_weight = fields.Float('Average Weight', digits=dp.get_precision('Stock Weight'))
    packages_per_pallet = fields.Integer('Quantity Per Pallet', default=1)
    uom_english = fields.Char('UoM English')
    product_type = fields.Selection([
        ('unit', 'Unit'),
        ('fixed', 'Fixed Weight'),
        ('variable', 'Variable Weight')
    ], 'Product Type', required=True, default='unit')
    package_count_in_row = fields.Integer('Package Number in a Row', default=1)
    supplier_id = fields.Many2one('res.partner', 'Supplier')
    supplier_code = fields.Char('Supplier Code', size=64, readonly=True)
    
    minimal_qty_multiple = fields.Float("Minimal Quantity Multiple (Retail, Logistics)", digits=(12, 3))
    minimal_qty_multiple_fs = fields.Float("Minimal Quantity Multiple (Food Service)", digits=(12, 3))
    certificate = fields.Selection([
        ('N', 'No Certificate'),
        ('T', 'Certificate Required (1 Certif.)'),
        ('G', 'Expiration Date Required (Many Certif.)'),
    ], 'Certificate')
    bls_import_timestamp = fields.Integer('Bls TimeStamp', readonly=True, default=1)
    weight_uom_id = fields.Many2one('product.uom', "Weight UOM")
    tlic = fields.Char('Tlic', size=32, readonly=True)


    _sql_constraints = [
        ('external_product_id', 'unique (external_product_id)', 'External ID of product has to be unique')
    ]


    _order = 'default_code, id'

    @api.multi
    def get_product_dict_for_report(self):
        barcode = self.barcode_ids.filtered(lambda barcode_rec: barcode_rec.type == 'unit')
        barcode_code = barcode and barcode[0].barcode or ''
        return {
            'Line_No': 1,
            'ProductCode': self.default_code or '',
            'Inf_Prek': self.default_code or '',
            'ProductId': str(self.id) or '',
            'Barcode': barcode_code,
            'CodeAtClient': '',
            'ProductDescription': self.name or '',
            'MeasUnit': self.uom_id and self.uom_id.name or '',
            'Price': str(self.standard_price or 0),
            'PriceVat': str(self.standard_price or 0),
            'VatTrf': str(0),
            'Netto': str(self.weight_neto or 0),
            'Brutto': str(self.weight or 0),
            'Tobacco': str(0),
            'Alco': str(0),
            'Tara': 'U',
        }


    @api.multi
    def check_product_owner(self, object_for_validation=None):
        if len(self.mapped('owner_id')) > 1:
            if object_for_validation:
                raise UserError(_('Error. There cant be more than one owner in document(%s, ID: %s, type of document: %s). Owners in document: %s') % (
                    object_for_validation.name_get()[0][1], str(object_for_validation.id),
                    object_for_validation._description, ', '.join(self.mapped('owner_id').mapped('name'))
                ))
            else:
                raise UserError(_('Error. There cant be more than one owner in document'))


    @api.multi
    def get_price(self):
        return self.standard_price

    @api.model
    def reset_tax_cache(self):
        global PRODUCT_TAX_DICT
        PRODUCT_TAX_DICT = {}

    @api.multi
    def update_taxes(self):
        tax_env = self.env['account.tax']
        global PRODUCT_TAX_DICT
        for product in self:
            if product.vat_tariff_id:
                if product. vat_tariff_id.type_tax_use == 'sale':
                    sale_taxe = product.vat_tariff_id
                    key = (product.vat_tariff_id.amount, 'purchase')
                    if key in PRODUCT_TAX_DICT:
                        purchase_taxe = PRODUCT_TAX_DICT[key]
                    else:
                        purchase_taxe = tax_env.search([
                            ('amount','=',product.vat_tariff_id.amount),
                            ('type_tax_use','=','purchase')
                        ])[0]
                        PRODUCT_TAX_DICT[key] = purchase_taxe
                else:
                    purchase_taxe = product.vat_tariff_id
                    key = (product.vat_tariff_id.amount, 'sale')
                    if key in PRODUCT_TAX_DICT:
                        sale_taxe = PRODUCT_TAX_DICT[key]
                    else:
                        sale_taxe = tax_env.search([
                            ('amount','=',product.vat_tariff_id.amount),
                            ('type_tax_use','=','sale')
                        ])[0]
                        PRODUCT_TAX_DICT[key] = sale_taxe
                product.write({
                    'supplier_taxes_id': [(6, 0, [purchase_taxe.id])],
                    'taxes_id': [(6, 0, [sale_taxe.id])],
                })
    
    @api.model
    def create_if_not_exist(self, vals, model):
        domain = [(key,'=',vals[key]) for key in vals.keys()]
        objects = self.env[model].search(domain)
        if objects:
            return objects[0]
        else:
            return self.env[model].create(vals)

    @api.multi
    def get_product_packages_qty(self):
        prod = self.read([
            'small_package_size', 'big_package_size'
        ])[0]
        return {
            'small_package_size': prod['small_package_size'] or 0.0,
            'big_package_size': prod['big_package_size'] or 0.0,   
        }

    @api.model_cr
    def init(self):
        cr = self.env.cr
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('product_product_external_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX product_product_external_id_index ON product_product (external_product_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('product_product_intermediate_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX product_product_intermediate_id_index ON product_product (intermediate_id)')

    @api.model
    def check_product_vals(self, prod_vals):
        if not prod_vals.get('name', False):
            raise UserError(_('Product has to have \'%s\' filled') % _('Name'))
        return True

    @api.model
    def clear_default_cashe(self):
        global DEFAULT_PRODUCT_UNIT_ID
        global DEFAULT_PRODUCT_UNIT_ID_DICT
        DEFAULT_PRODUCT_UNIT_ID = None
        DEFAULT_PRODUCT_UNIT_ID_DICT = {}

    @api.model
    def get_default_uom_for_product(self, uom_name=None):
        global DEFAULT_PRODUCT_UNIT_ID
        global DEFAULT_PRODUCT_UNIT_ID_DICT
        if uom_name is None:
            if DEFAULT_PRODUCT_UNIT_ID:
                uom_id = DEFAULT_PRODUCT_UNIT_ID
            else:
                ex_id_obj = self.env['ir.model.data']
                model_data = ex_id_obj.search([
                    ('model', '=', 'product.uom'),
                    ('module', '=', DEFAULT_PRODUCT_UNIT_XML_ID.split('.')[0]),
                    ('name', '=', DEFAULT_PRODUCT_UNIT_XML_ID.split('.')[1])
                ], limit=1)
                if model_data:
                    uom_id = model_data.res_id
                    DEFAULT_PRODUCT_UNIT_ID = uom_id
                else:
                    uom_id = False
            return uom_id
        else:
            if uom_name in DEFAULT_PRODUCT_UNIT_ID_DICT.keys():
                return DEFAULT_PRODUCT_UNIT_ID_DICT[uom_name]
            else:
                uom = self.env['product.uom'].search([('name','=',uom_name)], limit=1)
                if not uom:
                    uom = self.env['product.uom'].create({
                        'name': uom_name,
                        'active': True,
                        'category_id': self.env['product.uom.categ'].search(['|',('name','=','Weight'),('name','=','Svoris')], limit=1).id,
                        'uom_type': 'reference',
                        'rounding': 0.00100
                    })
                DEFAULT_PRODUCT_UNIT_ID_DICT[uom_name] = uom.id
            return uom.id

    @api.model
    def create_product(self, vals):
        interm_obj = self.env['stock.route.integration.intermediate']
        usr_obj = self.env['res.users']

        context = self.env.context or {}
        commit = not context.get('no_commit', False)

        ctx = context.copy()
        ctx['allow_to_create_product'] = True
        ctx_active = context.copy()
        ctx_active['active_test'] = False

        product = self.with_context(ctx_active).search([
            ('external_product_id','=',vals['external_product_id'])
        ], limit=1)
        if product and 'bls_import_timestamp' in vals.keys():
            import_timestamp = product.read(['bls_import_timestamp'])[0]['bls_import_timestamp']
            if import_timestamp > vals['bls_import_timestamp']:
                return product
        if product and context.get('do_not_update_product', False):
            return product
        company = usr_obj.browse(self.env.uid).company_id
        
        if product:
            prod_vals = {}
        else:
            prod_vals = self.default_get(self._fields)
        prod_vals.update(vals)


        uom_id = self.get_default_uom_for_product()

        if 'type_of_product' in prod_vals:
            if prod_vals['type_of_product'] == 'produktas':
                prod_vals['type_of_product'] = 'product'
            if prod_vals['type_of_product'] == u'pakuotė':
                prod_vals['type_of_product'] = 'package'
        
        if 'product_type' in prod_vals:
            if prod_vals['product_type'] == u'vienetinė prekė':
                prod_vals['product_type'] = 'unit'
            if prod_vals['product_type'] == 'kintamas svoris':
                prod_vals['product_type'] = 'variable'
            if prod_vals['product_type'] == u'pastovaus svorio prekė':
                prod_vals['product_type'] = 'fixed'
        else:
            prod_vals['product_type'] = 'fixed'
         
        if product:
            if 'type_of_product' in prod_vals and not context.get('update_type', False):
                del prod_vals['type_of_product']
            interm_obj.remove_same_values(product, prod_vals)
            if prod_vals:
                prod_vals['intermediate_id'] = context.get('intermediate_id', False)
                product.write(prod_vals)
                if 'updated_product_ids' in context:
                    context['updated_product_ids'].append((vals['external_product_id'], product.id))
            
        else:
            if not company.packaging_category_id:
                msg = _('You have to select \'Default Product Category\' in company settings') + '\n'
                raise UserError(msg)
            elif not uom_id:
                msg = _('Can\'t found unit of measurement with external id: %s') % DEFAULT_PRODUCT_UNIT_XML_ID + '\n'
                raise UserError(msg)
            prod_vals['categ_id'] = company.packaging_category_id.id
            prod_vals['type'] = 'product'
            if not prod_vals.get('active', True) and not prod_vals.get('name', ''):
                prod_vals['name'] = prod_vals['external_product_id']
                
            ############
#             prod_vals['product_type'] = 'fixed'
            ##############
            prod_vals['uom_po_id'] = uom_id
            prod_vals['uom_id'] = uom_id
            prod_vals['intermediate_id'] = context.get('intermediate_id', False)
            self.check_product_vals(prod_vals)
            product = self.with_context(ctx).create(prod_vals)
            if 'created_product_ids' in context:
                context['created_product_ids'].append((prod_vals['external_product_id'], product.id))
        if commit:
            self.env.cr.commit()
        return product

    @api.model
    def check_imported_packing_values(self, list_of_product_vals):
        inter_obj = self.env['stock.route.integration.intermediate']
        result = {}
        inter_obj.check_import_values(
            list_of_product_vals,
            ['product_default_code', 'external_product_id'],
            result
        )
        
        i = 0
        for prod_dict in list_of_product_vals:
            i = i + 1
            index = str(i)
            if prod_dict.get('active', 'N') == 'Y' and not prod_dict.get('product_name', ''):
                msg = _('\'Active\' is marked in product.') + ' ' +  _('You have to fill in value: %s') % 'product_name'
                if index in result.keys():
                    result[index].append(msg)
                else:
                    result[index] = [msg]
        return result

    @api.model
    def create_packing(self, list_of_product_vals):
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        inter_obj = self.env['stock.route.integration.intermediate']
        log_obj = self.env['delivery.integration.log']
        
        create_datetime = time.strftime('%Y-%m-%d %H:%M:%S')
        
        ctx_en = context.copy()
        ctx_en['lang'] = 'en_US'
        error = self.with_context(ctx_en).check_imported_packing_values(list_of_product_vals)
        if error:
            log_vals = {
                'create_date': create_datetime,
                'function': 'create_packing',
                'received_information': str(json.dumps(list_of_product_vals, indent=2)),
                'returned_information': str(json.dumps(error, indent=2))
            }
            log_obj.create(log_vals)
            return error
        
        itermediate = inter_obj.create({
            'datetime': create_datetime,
            'function': 'create_packing',
            'received_values': str(json.dumps(list_of_product_vals, indent=2)),
            'processed': False
        })
        if commit:
            self.env.cr.commit()
        itermediate.process_intermediate_objects_threaded()
        return itermediate.id

    @api.model
    def check_imported_quantity_values(self, product_stock_dict_list):
        inter_obj = self.env['stock.route.integration.intermediate']
        result = {}
        required_values = [
            'external_customer_id',
            'external_customer_address_id',
            'external_product_id', 'product_name',
            'product_default_code', 'product_qty',
            'firm_id'
        ]
        inter_obj.check_import_values(product_stock_dict_list, required_values, result)
        return result

    @api.model
    def quantity_by_customer(self, product_stock_dict_list):
        context = self.env.context or {}
        inter_obj = self.env['stock.route.integration.intermediate']
        log_obj = self.env['delivery.integration.log']
        
        create_datetime = time.strftime('%Y-%m-%d %H:%M:%S')
        
        ctx_en = context.copy()
        ctx_en['lang'] = 'en_US'
        ctx_del = context.copy()
        ctx_del['allow_to_delete_integration_obj'] = True
        ctx_force = context.copy()
        ctx_force['force_process_intermediate'] = True
        
        error = self.with_context(ctx_en).check_imported_quantity_values(product_stock_dict_list)
        if error:
            log_vals = {
                'create_date': create_datetime,
                'function': 'quantity_by_customer',
                'received_information': str(json.dumps(product_stock_dict_list, indent=2)),
                'returned_information': str(json.dumps(error, indent=2))
            }
            log_obj.create(log_vals)
            return error

        itermediate = inter_obj.create({
            'datetime': create_datetime,
            'function': 'quantity_by_customer',
            'received_values': str(json.dumps(product_stock_dict_list, indent=2)),
            'processed': False
        })
        self.env.cr.commit()
        itermediate.with_context(ctx_force).process_intermediate_objects_threaded()
        return itermediate.id
   
    @api.model
    def update_args(self, args):
        context = self.env.context or {}
        if context.get('args_updated', False):
            return True
        
        if context.get('search_by_warehouse_id', False):
            # Grąžina tik tuos produktus kurie yra priskirti prie per contextą gaunamo sandėlio.
            wh_obj = self.env['stock.warehouse']
            wh = wh_obj.browse(context['search_by_warehouse_id'])
            args.append(('id','in',wh.product_ids.mapped('id')))
            
        
        if context.get('search_by_route', False):
            # Grąžina tuos produktus, kurie buvo priskirti prie per contextą perduodamo maršruto
            route_obj = self.env['stock.route']
            route = route_obj.browse(context['search_by_route'])
            prod_ids = []
            if route.picking_id:
                for move in route.picking_id.move_lines:
                    if move.product_id and move.product_id.id not in prod_ids:
                        prod_ids.append(move.product_id.id)
            args.append(('id','in',prod_ids))
            
        return True

    @api.model
    def _search(
        self, args, offset=0, limit=None,
        order=None, count=False,
        access_rights_uid=None
    ):
        context = self.env.context or {}
        
        new_args = []
            
        for arg in args:
            if arg[0] == 'barcode_ids' and arg[1] == 'ilike':
                product_ids = []
                barcode_obj = self.env['product.barcode']
                barcodes = barcode_obj.search([
                    ('barcode','ilike',arg[2])
                ])
                if barcodes:
                    for barcode in barcodes.read(['product_id']):
                        if barcode['product_id']:
                            product_ids.append(barcode['product_id'][0])
                if product_ids:
                    product_ids = list(set(product_ids))
                    new_args.append(['id','in',product_ids])
                else:
                ### Tuo atveju, jei nerado tinkamu produktu, kad ir searchas negrazintu jokiu id
                    new_args = [('id','=',-1)]
                    
            elif arg[0] == 'seller_ids' and arg[1] == 'ilike':
                product_ids = []
                supplier_obj = self.env['product.supplierinfo']
                suppliers = supplier_obj.search([
                    ('supplier_code','ilike',arg[2])
                ])
                if suppliers:
                    for supplier in suppliers.read(['product_id']):
                        if supplier['product_id']:
                            product_ids.append(supplier['product_id'][0])
                if product_ids:
                    product_ids = list(set(product_ids))
                    new_args.append(['id','in',product_ids])
                else:
                    new_args = [('id','=',-1)]
            else:
                new_args.append(arg)
            
        ctx = context.copy()
        self.with_context(ctx).update_args(new_args)
        return super(ProductProduct, self)._search(
            new_args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self.env.context or {}
        if context.get('open_search_dialog', False):
            # Kartais kažkokia nesamonė būna kur iš JavaScript ateina domainas ['id','in',[None, None, None.....]]
            for arg in args:
                if len(arg) > 2 and arg[0] == 'id' and arg[1] == 'in' and isinstance(arg[2], list) and None in arg[2]:
                    list_of_id = list(set(arg[2]))
                    while list_of_id and None in list_of_id:
                        list_of_id.remove(None)
                    if not list_of_id:
                        args.remove(arg)
        ctx = context.copy()
        self.with_context(ctx).update_args(args)
        return super(ProductProduct, self).search(
            args, offset=offset, limit=limit,
            order=order, count=count
        )
        
    @api.multi
    def fill_barcode_to_show_field(self):
        for product in self:
            if not product.barcode_ids:
                continue
            barcode = product.barcode_ids[0].barcode
            for bc in product.barcode_ids:
                if bc.type == 'unit':
                    barcode = bc.barcode
                    break
            product.write({'barcode_to_show': barcode})

    @api.model
    def update_vals(self, vals):
        if 'supplier_id' in vals.keys():
            if vals.get('supplier_id', False):
                vals['supplier_code'] = self.env['res.partner'].browse(vals['supplier_id']).supplier_code
            else:
                vals['supplier_code'] = ''

    @api.model
    def create(self, vals):
        self.update_vals(vals)
        context = self.env.context or {}
        if self.env.uid != 1 and not context.get('allow_to_create_product', False):
            raise UserError(_('You can\'t create product'))
        if 'standard_price' not in vals:
            vals['standard_price'] = 0.0
        product = super(ProductProduct, self).create(vals)
        if vals.get('barcode_ids', False):
            product.fill_barcode_to_show_field()
        
        if 'vat_tariff_id' in vals.keys():
            product.update_taxes()
        return product
    

    @api.multi
    def _export_rows(self, fields):
        if self.env.user.company_id.user_faster_export:
            res = self.env['ir.model'].export_rows_with_psql(fields, self)
        else:
            res = super(ProductProduct, self)._export_rows(fields)
        return res
    
    @api.multi
    def write(self, vals):
        self.update_vals(vals)
        context = self.env.context or {}
        if self.env.uid != 1 and not context.get('allow_to_edit_product', False):
            raise UserError(_('You can\'t edit product'))
        res = super(ProductProduct, self).write(vals)
        if vals.get('barcode_ids', False):
            self.fill_barcode_to_show_field()
        
        if 'vat_tariff_id' in vals.keys():
            self.update_taxes()
        return res

    @api.model
    def recalculate_stocks(
        self, product_ids=[], location_ids=[],
        partner_ids=[]
    ):
        context = self.env.context or {}
        move_obj = self.env['stock.move']
        loc_stock_obj = self.env['sanitex.product.location.stock']
        
        ctx = context.copy()
        ctx['from_xmlrpc'] = True
        
        _logger.info('Recalculating Stocks')
        if not product_ids:
            self.env.cr.execute('''
                SELECT
                    distinct(product_id)
                FROM
                    stock_move
            ''')
            product_ids = [cr_line[0] for cr_line in self.env.cr.fetchall()]
            product_ids = list(set(product_ids))
        if not location_ids:
            self.env.cr.execute('''
                SELECT
                    distinct(location_id)
                FROM
                    stock_move
            ''')
            location_ids = [cr_line[0] for cr_line in self.env.cr.fetchall()]
            self.env.cr.execute('''
                SELECT
                    distinct(location_dest_id)
                FROM
                    stock_move
            ''')
            location_ids += [cr_line[0] for cr_line in self.env.cr.fetchall()]
            location_ids = list(set(location_ids))
        
        i = 0
        all_products = len(product_ids)
        for product_id in product_ids:
            i += 1
            res = i*100/all_products

            if res/10 > ((i-1)*100/all_products)/10:
                _logger.info('Progress: %s / %s' % (str(i), str(all_products)))
                
            for location_id in location_ids:
                qty = 0.0
                moves = move_obj.search([
                    ('state','=','done'),
                    ('product_id','=',product_id),
                    ('location_id','=',location_id)
                ])
                for move in moves:
                    qty -= move.product_uom_qty
                _logger.info('    product_id: %s, location_id: %s, qty: %s' % (str(product_id), str(location_id), str(qty)))
                moves = move_obj.search([
                    ('state','=','done'),
                    ('product_id','=',product_id),
                    ('location_dest_id','=',location_id)
                ])
                for move in moves:
                    qty += move.product_uom_qty
                _logger.info('    2 product_id: %s, location_id: %s, qty: %s' % (str(product_id), str(location_id), str(qty)))
                try:
                    loc_stock_obj.replace_quantity(location_id, product_id, qty)
                except Exception as e:
                    err_note = _('Error while updating debt: %s') % (tools.ustr(e),)
                    _logger.info(err_note)
                    self.env.cr.rollback()

        _logger.info('Recalculating Stocks Finished')
        return True

    @api.model
    def thread_recalculate(
        self, product_ids,
        location_ids, partner_ids
    ):
        with Environment.manage():
            new_cr = self.pool.cursor()
            new_self = self.with_env(self.env(cr=new_cr))
            try:
                new_self.recalculate_stocks(
                    product_ids, location_ids, partner_ids
                )
                new_cr.commit()
            finally:
                new_cr.close()
        return True

    @api.model
    def recalculate_threaded(
        self, product_ids=[], location_ids=[], partner_ids=[]
    ):
        
        t = threading.Thread(target=self.thread_recalculate, args=(
            product_ids, location_ids, partner_ids
        ))
        t.start()
        return {'type':'ir.actions.act_window_close'}
    
    @api.multi
    @api.depends('name')
    def name_get(self):
        res = []
        if not self:
            return res
        context = self.env.context or {}
        for product in self:
            if product.type_of_product == 'package' and context.get('show_code_in_product_name', False):
                res.append((product.id, "%s - %s" % (product.default_code or '', product.name)))
            else:
                res.append((product.id, product.name))
        return res

    @api.multi
    def get_product_code(self):
        code = ''
        if self.exists():
            code = self.default_code or ''
        return code

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        if ('description_purchase' in fields or 'description_sale' in fields) and 'name' not in fields:
            fields.append('name')
        res = super(ProductProduct, self).read(fields=fields, load=load)
        
        if 'description_purchase' in fields or 'description_sale' in fields:
            if type(res) != type([]):
                ress = [res]
            else:
                ress = res
            for p_read in ress:
                if 'description_purchase' in fields:
                    if not p_read['description_purchase']:
                        p_read['description_purchase'] = p_read['name']
                if 'description_sale' in fields:
                    if not p_read['description_sale']:
                        p_read['description_sale'] = p_read['name']
                
        return res

    @api.multi
    def get_product_quantity(self, location_id=False):
        quant_env = self.env['sanitex.product.location.stock']
        return quant_env.get_quantity(product_id=self.id, location_id=location_id)

    @api.multi
    def get_product_quantity_with_sql(self, location_id=False):
        return self.env['stock.move'].get_sumed_qty_with_sql(location_id, self.id)

    @api.multi
    def get_name_for_error(self):
        return '[' + self.default_code + '] ' + self.name

    @api.multi
    def get_weight(self, qty=1):
        total_weight = self.weight
        if self.product_type in ['fixed', 'variable']:
            total_weight = qty
        else:
            total_weight = total_weight*qty
        return total_weight

class SanitexProductLocationStock(models.Model):
    _name = 'sanitex.product.location.stock'
    _description = 'Product Stock by Location'

    product_id = fields.Many2one(
        'product.product', 'Product',
        required=True, ondelete='cascade',
        readonly=True, index=True
    )
    product_code = fields.Char('Product Code',
        readonly=True, size=128
    )
    location_id = fields.Many2one(
        'stock.location', 'Location',
        required=True, ondelete='cascade',
        readonly=True, index=True
    )
    qty_available = fields.Float(
        'Debt', digits=(16,2)
    )
    additional_qty_available = fields.Float(
        'Additional Stock', readonly=True, default=0.0
    )
    owner_id = fields.Many2one('product.owner', 'Owner Code', readonly=True)
    product_name = fields.Char('Product Name', size=128, readonly=True)
    location_name = fields.Char('Location Name', size=128, readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', "Warehouse")
    warehouse_name = fields.Char('Warehouse Name', size=128, readonly=True)

    _sql_constraints = [
        ('product_location_uniq', 'UNIQUE(product_id, location_id)', 
            'Product and location combination must be unique in products by location.'
        ),
    ]

    @api.multi
    def update_values_sql(self):
        if self:
            update_sql = '''
                UPDATE
                    sanitex_product_location_stock spls
                SET
                    product_code = pp.default_code,
                    owner_id = pp.owner_id,
                    product_name = pt.name,
                    location_name = sl.name
                FROM
                    product_product pp,
                    product_template pt,
                    stock_location sl
                WHERE
                    pp.id = spls.product_id
                    AND pt.id = pp.product_tmpl_id
                    AND sl.id = spls.location_id
                    AND psls.id in %s           
            '''
            update_where = (tuple(self.ids),)
            self.env.cr.execute(update_sql, update_where)

    @api.multi
    def check_quantity(self):
        for quant in self:
            if quant.location_id.driver and quant.qty_available < 0.0:
                raise UserError(
                    _('After executing this action product\'s %s debt for driver %s will be negative(%s). It is forbidden') % (
                        quant.product_id.get_name_for_error(), quant.location_id.name, str(quant.qty_available)
                    )
                )
        return True


    @api.multi
    def _export_rows(self, fields):
        if self.env.user.company_id.user_faster_export:
            res = self.env['ir.model'].export_rows_with_psql(fields, self)
        else:
            res = super(SanitexProductLocationStock, self)._export_rows(fields)
        return res

    @api.model
    def update_vals(self, vals):
        if vals.get('location_id', False):
            vals['location_name'] = self.env['stock.location'].browse(vals['location_id']).name
            if not vals.get('warehouse_id', False):
                location = self.env['stock.location'].browse(vals['location_id'])
                warehouse = location.get_location_warehouse_id()
                if warehouse:
                    vals['warehouse_id'] = warehouse.id
                    vals['warehouse_name'] = warehouse.name
    @api.model
    def create(self, vals):
        prod_obj = self.env['product.product']
        if vals.get('product_id', False):
            product = prod_obj.browse(vals['product_id']).read(['default_code', 'owner_id', 'name'])[0]
            if product.get('default_code', False):
                vals['product_code'] = product['default_code']
            if product.get('name', False):
                vals['product_name'] = product['name']
            if product.get('owner_id', False):
                vals['owner_id'] = product['owner_id'][0]
        self.update_vals(vals)
        stock = super(SanitexProductLocationStock, self).create(vals)
        stock.check_quantity()
        if stock.location_id:
            stock.location_id.update_drivers_total_debt()
        return stock

    @api.multi
    def write(self, vals):
        prod_obj = self.env['product.product']
        if vals.get('product_id', False):
            product = prod_obj.browse(vals['product_id']).read(['default_code','name'])[0]
            if product.get('default_code', False):
                vals['default_code'] = product['default_code']
            if product.get('name', False):
                vals['product_name'] = product['name']
        self.update_vals(vals)
        res = super(SanitexProductLocationStock, self).write(vals)
        self.check_quantity()
        if set(vals.keys()).intersection(['location_id', 'qty_available']):
            self.mapped('location_id').update_drivers_total_debt()
        return res

    @api.model
    def get_quantity(self, product_id=False, location_id=False):
        qty = 0.0
        domain = []
        limit = 1
        if product_id:
            domain.append(('product_id','=',product_id))
            limit = None
        if location_id:
            domain.append(('location_id','=',location_id))
            limit = None
        quants = self.search(domain, limit=limit)
        if quants:
            qty = sum(quants.mapped('qty_available'))
        return qty

    @api.multi
    def get_moves_from_stock_by_location(self):
        data_obj = self.env['ir.model.data']
        view_obj = self.env['ir.ui.view']
        
        data = data_obj.search([
            ('model','=','ir.ui.view'),
            ('name','=','view_stock_move_sanitex_alternative_tree')
        ], limit=1)
        view_id = data.res_id
        tree_view = view_obj.browse(view_id)
        
        data = data_obj.search([
            ('model','=','ir.ui.view'),
            ('module','=','stock'),
            ('name','=','view_move_form')
        ])
        view_id = data.res_id
        form_view = view_obj.browse(view_id)
        return {
            'name': _('%s moves (location: %s)') % (self.product_id.name, self.location_id.name),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.move',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id,'tree'),(form_view.id,'form')],
            'domain': [
                ('state','=','done'),
                ('product_id','=',self.product_id.id),
                '|',('location_id','=',self.location_id.id),
                ('location_dest_id','=',self.location_id.id)
            ]
        }
    
    @api.multi
    @api.depends('location_id', 'product_code', 'qty_available')
    def name_get(self):
        result = []
        for obj in self:
            result.append((obj.id, (obj.location_id and obj.location_id.name or '') + ' - [' + (obj.product_code or '') + '] ' + str(obj.qty_available) ))
        return result

    @api.multi
    def unlink(self):
        context = self.env.context or {}
        if not context.get('allow_to_location_stock', False):
            raise UserError(_('You are not allowed to unlink location stocks (IDs: %s)') % str(self.mapped('id')))
        return super(SanitexProductLocationStock, self).unlink()

    @api.model
    def update_quantity(self, location_id, product_id, qty, add=False):
        context = self._context

        self._cr.execute('''
                SELECT
                    id, qty_available
                FROM
                    sanitex_product_location_stock
                WHERE location_id = %s
                    AND product_id = %s
                LIMIT 1
            ''', (location_id, product_id))
        sql_res = self._cr.fetchone()
        if sql_res:
            debt_id, qty_available = sql_res
        else:
            debt_id = False

        if debt_id:
            if add:
                qty += qty_available

            if context.get('qty_sql_write', False):
                self._cr.execute('''
                        UPDATE
                            sanitex_product_location_stock
                        SET
                            qty_available = %s
                        WHERE id = %s
                    ''', (qty, debt_id))
            else:
                self.browse(debt_id).write({
                    'qty_available': qty
                })
        else:
            self.create({
                'product_id': product_id,
                'location_id': location_id,
                'qty_available': qty
            })
        return True
    
    @api.model
    def replace_quantity(self, location_id, product_id, qty):
        return self.update_quantity(location_id, product_id, qty, add=False)
        
    @api.model
    def add_quantity(self, location_id, product_id, qty):
        return self.update_quantity(location_id, product_id, qty, add=True)

    @api.multi
    def update(self, commit=True):
        if self:
            move_env = self.env['stock.move']
            update_sql = '''
                SELECT
                    id,
                    product_id,
                    location_id,
                    qty_available
                FROM
                    sanitex_product_location_stock
                WHERE
                    id in %s
            '''
            update_where = (tuple(self.ids),)
            self.env.cr.execute(update_sql, update_where)
            results = self.env.cr.fetchall()
            for result in results:
                qty = move_env.get_sumed_qty_with_sql(result[2], result[1])
                if not qty:
                    qty = 0.0
                if qty != result[3]:
                    change_sql = '''
                        UPDATE
                            sanitex_product_location_stock
                        SET
                            qty_available = %s
                        WHERE
                            id = %s
                    '''
                    change_where = (qty, result[0])
                    self.env.cr.execute(change_sql, change_where)
                    _logger.info('Updated id: %s. %s --> %s' % (str(result[0]), str(result[3]), str(qty)))
                    if commit:
                        self.env.cr.commit()




class SanitexProductPartnerStock(models.Model):
    _name = 'sanitex.product.partner.stock'
    _description = 'Product Stock by Partner'

    product_id = fields.Many2one(
        'product.product', 'Product',
        required=True, ondelete='cascade'
    )
    product_code = fields.Char('Product Code',
        readonly=True, size=128
    )
    partner_id = fields.Many2one(
        'res.partner', 'Partner', ondelete='cascade',
    )
    organisation_id = fields.Many2one(
        'res.partner', 'Client', ondelete='cascade',
        readonly=True
    )
    client = fields.Char('Client', size=256, readonly=True)
    address = fields.Char('Address', size=512, readonly=True)
    possid = fields.Char('POSSID', size=64, readonly=True)
    address_id = fields.Many2one(
        'res.partner', 'Address', ondelete='cascade',
        readonly=True
    )
    qty_available = fields.Integer('Debt')
    additional_qty_available = fields.Integer(
        'Additional Stock', default=0
    )
    intermediate_id = fields.Many2one(
        'stock.route.integration.intermediate', 'Last modified by by', readobly=True
    )
    address_possid_code = fields.Char('Address POSSID Code', size=256, readonly=True)
    company_id = fields.Many2one('res.company', 'Company')
    reconciliation_date = fields.Datetime('Reconciliation Date')
    owner_id = fields.Many2one('product.owner', 'Owner Code', readonly=True)
    external_posid_id = fields.Char('POSSID External ID', size=256, readonly=True)
    product_name = fields.Char('Product Name', size=128, readonly=True)
    product_price = fields.Float('Product Price', digits=(16, 2), required=True)
    partner_ref = fields.Char('Company Code', readonly=True)
    
    _sql_constraints = [
        ('product_location_uniq', 'UNIQUE(product_id, partner_id, external_posid_id, product_price)', 
            'Product, price and location combination must be unique in products by partner.'
        ),
    ]

    @api.multi
    def update_values_sql(self):
        # Skolos eilutei užpildoma papiloma info pagal susijusius objektus.

        if self:
            update_sql = '''
                UPDATE
                    sanitex_product_partner_stock spps
                SET
                    product_code = pp.default_code,
                    owner_id = pp.owner_id,
                    product_name = pt.name,
                    client = rp.name,
                    address = rpp.street,
                    possid = rpp.possid_code,
                    address_possid_code = rpp.possid_code,
                    partner_ref = rp.ref
                FROM
                    product_product pp,
                    product_template pt,
                    res_partner rp,
                    res_partner rpp
                WHERE
                    pp.id = spps.product_id
                    AND pt.id = pp.product_tmpl_id
                    AND rp.id = spps.organisation_id
                    AND rpp.id = spps.partner_id
                    AND spps.id in %s           
            '''
            update_where = (tuple(self.ids),)
            self.env.cr.execute(update_sql, update_where)

    @api.model
    def cron_fix_bad_lines(self):
        # Kartais kuriant kliento skolos eilutę neegzistuoja produktas ir tas produktas yra sukuriamas
        # be dalies informacijos(owneris). Vėliau kai tas produktas ateina su produktų integracija
        # jis gauna reikalingą informaciją, bet jinai neužsipildo prie partnerio skolos eilučių.
        # Ši funkcija paieško ar yra tokių eilučių ir joms iškviečia updeitą.

        _logger.info('Fixing partner stocklines.')
        search_sql = '''
            SELECT
                spps.id
            FROM
                sanitex_product_partner_stock spps
                JOIN product_product pp on (pp.id = spps.product_id)
            WHERE
                spps.owner_id is null
                AND pp.owner_id is not null
        '''
        self.env.cr.execute(search_sql)
        ids = [id_to_fix[0] for id_to_fix in self.env.cr.fetchall()]
        _logger.info('%s lines found: %s' %(len(ids), str(ids)))
        if ids:
            self.browse(ids).update_values_sql()
        _logger.info('Fixing partner stocklines finished.')

    @api.model_cr
    def init(self):
        cr = self.env.cr
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('sanitex_product_partner_stock_intermediate_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX sanitex_product_partner_stock_intermediate_id_index ON sanitex_product_partner_stock (intermediate_id)')
    
    
    @api.multi
    @api.depends('client', 'possid', 'product_code', 'qty_available')
    def name_get(self):
        result = []
        for obj in self:
            result.append((obj.id, (obj.client or '') + ' (' + (obj.possid or '') + ') ' + ' - [' + (obj.product_code or '') + '] ' + str(obj.qty_available) ))
        return result



    @api.multi
    def check_quantity(self):
#         for id in ids:
#             quant = self.browse(cr, uid, id, context=context)
#             if quant.qty_available:
#                 raise osv.except_osv(
#                     _('Error'),
#                     _('After executing this action product\'s %s debt for client %s will be negative(%s). It is forbidden') % (
#                         quant.product_id.name, quant.partner_id.name, str(quant.qty_available)
#                     )
#                 )
                
        return True

    @api.multi
    def _export_rows(self, fields):
        if self.env.user.company_id.user_faster_export:
            res = self.env['ir.model'].export_rows_with_psql(fields, self)
        else:
            res = super(SanitexProductPartnerStock, self)._export_rows(fields)
        return res

    @api.model
    def update_vals(self, vals):
        part_obj = self.env['res.partner']
        prod_obj = self.env['product.product']
        if vals.get('partner_id',False):
            part = part_obj.browse(vals['partner_id'])
            if part.is_company:
                vals['organisation_id'] = part.id
                vals['client'] = part.name or ''
                vals['partner_ref'] = part.ref
            elif part.parent_id:
                vals['organisation_id'] = part.parent_id.id
                vals['address_id'] = part.id
                vals['client'] = part.parent_id.name or ''
                vals['possid'] = part.possid_code or ''
                vals['partner_ref'] = part.parent_id.ref
                vals['address'] = part.get_address()
        if vals.get('product_id', False):
            product = prod_obj.browse(vals['product_id']).read(
                ['default_code','owner_id', 'name']
            )[0]
            if product.get('default_code', False):
                vals['product_code'] = product['default_code']
            if product.get('name', False):
                vals['product_name'] = product['name']
            if product.get('owner_id', False):
                vals['owner_id'] = product['owner_id'][0]
        return True

    @api.multi
    def unlink(self):
        context = self.env.context or {}
        if not context.get('allow_to_partner_stock', False):
            raise UserError(_('You are not allowed to unlink partner stocks (IDs: %s)') % str(self.mapped('id')))
        return super(SanitexProductPartnerStock, self).unlink()

    @api.model
    def create(self, vals):
        self.update_vals(vals)

        stock = super(SanitexProductPartnerStock, self).create(vals)
        if stock.partner_id and stock.partner_id.parent_id:
            self.calculate_parent(
                stock.partner_id.parent_id.id,
                stock.product_id.id
            )
        stock.check_quantity()
        return stock

    @api.multi
    def write(self, vals):
        context = self.env.context or {}
        self.update_vals(vals)
        if 'additional_qty_available' in vals and not context.get('from_xmlrpc', False):
            for quant in self:
                qty = quant.qty_available - quant.additional_qty_available
                qty += vals['additional_qty_available']
                vals['qty_available'] = qty
            
        res = super(SanitexProductPartnerStock, self).write(vals)
        for quant in self:
            if quant.partner_id and quant.partner_id.parent_id:
                self.calculate_parent(
                    quant.partner_id.parent_id.id,
                    quant.product_id.id
            )
        
        self.check_quantity()
        return res
    
    @api.model
    def calculate_parent(self, partner_id, product_id):
        partner_env = self.env['res.partner']
        posids = partner_env.search([('parent_id','=',partner_id)])
        debts = self.search([
            ('partner_id','in',posids.mapped('id')),
            ('product_id','=',product_id)
        ])
        debt_dict_by_price = {}
        for debt in debts:
            if debt.product_price not in debt_dict_by_price.keys():
                debt_dict_by_price[debt.product_price] = 0.0
            debt_dict_by_price[debt.product_price] += debt.qty_available
        
        for price in debt_dict_by_price.keys():
            self.replace_quantity(partner_id, product_id, debt_dict_by_price[price], price)
        return True

    @api.model
    def get_quantity(self, product_id, partner_id, price=None):
        context = self.env.context or {}
        qty = 0.0
        if context.get('calculate_fast', False):
            price_where = ''
            if price is not None:
                price_where = ' and product_price = %.3f ' % price
            self.env.cr.execute("""
                SELECT
                    sum(qty_available)            
                FROM
                    sanitex_product_partner_stock 
                WHERE 
                    partner_id = %s
                    and product_id = %s
                    %s
            """ % (str(partner_id), str(product_id), price_where))
            results = self.env.cr.fetchone()
            if results:
                return results[0]
        else:
            domain = [
                ('product_id','=',product_id),
                ('partner_id','=',partner_id)
            ]
            if price is not None:
                domain.append(('product_price','=',price))
            quants = self.search(domain)
            if quants:
                qty = sum(quants.mapped('qty_available'))
        
        return qty

    @api.multi
    def get_moves_from_stock_by_partner(self):
        data_obj = self.env['ir.model.data']
        view_obj = self.env['ir.ui.view']
        
        data = data_obj.search([
            ('model','=','ir.ui.view'),
            ('name','=','view_stock_move_sanitex_alternative_tree')
        ], limit=1)
        view_id = data.res_id
        view = view_obj.browse(view_id)
        
        data = data_obj.search([
            ('model','=','ir.ui.view'),
            ('module','=','stock'),
            ('name','=','view_move_form')
        ])
        view_id = data.res_id
        form_view = view_obj.browse(view_id)
        if self.partner_id.is_company:
            domain = [
                ('state','=','done'),
                ('product_id','=',self.product_id.id),
                ('address_id.parent_id','=',self.partner_id.id),
                '|',('picking_id.picking_type_id.code','=','incoming'),
                ('picking_id.picking_type_id.code','=','outgoing'),
            ]
        else:
            domain = [
                ('state','=','done'),
                ('product_id','=',self.product_id.id),
                ('address_id','=',self.partner_id.id),
                '|',('picking_id.picking_type_id.code','=','incoming'),
                ('picking_id.picking_type_id.code','=','outgoing'),
            ]
        return {
            'name': _('%s moves (partner: %s)') % (self.product_id.name, self.partner_id.name),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.move',
            'views': [(view.id,'tree'),(form_view.id,'form')],
            'type': 'ir.actions.act_window',
            'domain': domain
        }
    
    @api.model
    def update_quantity(self, partner_id, product_id, qty, price=None, add=False, no_address=False):
        product = self.env['product.product'].browse(product_id)
        if price is None:
            price = product.get_price()
            
        domain = [
            ('product_id','=',product_id),
            ('product_price','=',round(price, 3))
        ]
        if no_address:
            domain.append(('external_posid_id','=',partner_id))
        else:
            domain.append(('partner_id','=',partner_id))
            
        debts = self.search(domain)
        if debts:
            debt = debts[0]
            if add:
                qty = debt.qty_available + qty
            else:
                debt.write({
                    'qty_available': qty
                })
        else:
            if no_address:
                self.create({
                    'product_id': product_id,
                    'external_posid_id': partner_id,
                    'possid': partner_id,
                    'product_price': price,
                    'qty_available': qty
                })
            else:
                self.create({
                    'product_id': product_id,
                    'partner_id': partner_id,
                    'product_price': price,
                    'qty_available': qty
                })
        return True
    
    @api.model
    def replace_quantity(self, partner_id, product_id, qty, price=None, no_address=False):
        return self.update_quantity(partner_id, product_id, qty, price=price, add=False, no_address=no_address)
        
    @api.model
    def add_quantity(self, partner_id, product_id, qty, price=None, no_address=False):
        return self.update_quantity(partner_id, product_id, qty, price=price, add=True, no_address=no_address)
    
    @api.model
    def get_quantities_by_price(self, product_id, partner_id, qty=None):
        res = {}
        quants = self.search([
            ('partner_id','=',partner_id),
            ('product_id','=',product_id),
            ('qty_available','>',0.0)
        ], order='product_price')
        for quant in quants:
            if qty is None:
                res[quant.product_price] = quant.qty_available
            else:
                res[quant.product_price] = min(quant.qty_available, qty)
                qty = qty - res[quant.product_price]
                if qty <= 0:
                    break
        return res


class ProductStockSerial(models.Model):
    _name = 'product.stock.serial'
    
    sequence = fields.Integer("Sequence", default=5)
    name = fields.Char("Serial", size=64, required=True)
    container_line_id = fields.Many2one(
        'account.invoice.container.line', "Container Line"
    )
    lot_id = fields.Many2one('stock.production.lot', "Lot")
    
class ProductCertificate(models.Model):
    _name = 'product.certificate'
    
#     @api.model
#     def create_link_in_obj(self,objs, certificate):
#         for obj in objs:
#         
    
    @api.multi
    def write(self, vals):
        context = self._context
        if not context.get('stop_certificate_linking', False):
            for certificate in self:
                if 'invoice_line_ids' in vals:
                    for inv_line in certificate.invoice_line_ids:
                        inv_line.with_context({'stop_certificate_linking':True}).write({
                            'certificate_id': False,
                        })
                if 'prod_lot_ids' in vals:
                    for lot in certificate.prod_lot_ids:
                        lot.with_context({'stop_certificate_linking':True}).write({
                            'certificate_id': False,
                        })
    
            res = super(ProductCertificate, self).write(vals)
            
            for certificate in self:
                if 'invoice_line_ids' in vals:
                    for inv_line in certificate.invoice_line_ids:
                        inv_line.with_context({'stop_certificate_linking':True}).write({
                            'certificate_id': certificate.id,
                        })
                if 'prod_lot_ids' in vals:
                    for lot in certificate.prod_lot_ids:
                        lot.with_context({'stop_certificate_linking':True}).write({
                            'certificate_id': certificate.id,
                        })
        else:
            res = super(ProductCertificate, self).write(vals)
        
        return res
    
    @api.model
    def create(self, vals):
        context = self._context
        res = super(ProductCertificate, self).create(vals)

        if not context.get('stop_certificate_linking', False):
            if vals.get('invoice_line_ids', False):
                for inv_line in res.invoice_line_ids:
                    inv_line.with_context({'stop_certificate_linking':True}).write({
                        'certificate_id': res.id,
                    })
            if vals.get('prod_lot_ids', False):
                for lot in res.prod_lot_ids:
                    lot.with_context({'stop_certificate_linking':True}).write({
                        'certificate_id': res.id,
                    })
        return res
    
    name = fields.Char("Name", size=64, required=True)
    valid_from = fields.Date("Valid From")
    valid_to = fields.Date("Valid To")
    country_origin_id = fields.Many2one('res.country', 'Country or Origin')
    invoice_id = fields.Many2one('account.invoice', 'Invoice')
#     invoice_line_ids = new_api_fields.One2many('account.invoice.line', 'certificate_id', "Invoice Lines")
#     prod_lot_ids = new_api_fields.One2many('stock.production.lot', 'certificate_id', "Lots")
    invoice_line_ids = fields.Many2many(
        'account.invoice.line', 'certificate_inv_line_rel', 'certificate_id',
        'inv_line_id', string="Invoice Lines"
    )
    prod_lot_ids = fields.Many2many(
        'stock.production.lot', 'certificate_lot_rel', 'certificate_id', 
        'lot_id', string="Lots"
    )
    organization_id = fields.Many2one(
        'product.certificate.organization', "Organization"
    )
    partner_id = fields.Many2one(
        'res.partner', "Importer",
        domain=[('possid_code','=',False)]
    )
    giving_date = fields.Date("Giving Date")
    
class ProductCertificateOrganization(models.Model):
    _name = 'product.certificate.organization'
    
    name = fields.Char("Name", size=64)
    
class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'
    
    supplier_code = fields.Char("Supplier Code", readonly=True)
    
    ### Defaulte keistai yra, kad name - many2one laukelis i res.partner lentele
    @api.onchange('name')
    def onchange_suppleir(self):
        if self.name:
            self.supplier_code = self.name.supplier_code

    @api.model
    def get_readonly_fields_vals(self, vals):
        res = {}
        if vals.get('name', False):
            partner_env = self.env['res.partner']
            res['supplier_code'] = partner_env.search([('id','=',vals['name'])], limit=1).supplier_code
        if vals.get('product_tmpl_id', False) and not vals.get('product_id', False):
            product_env = self.env['product.product']
            product = product_env.search([('product_tmpl_id','=',vals['product_tmpl_id'])], limit=1)
            if product:
                res['product_id'] = product.id
        return res
            
            
    @api.model
    def create(self, vals):    
        vals.update(self.get_readonly_fields_vals(vals))
        return super(ProductSupplierinfo, self).create(vals)
    
    @api.multi
    def write(self, vals):    
        if 'name' in vals:
            vals.update(self.get_readonly_fields_vals(vals))
        return super(ProductSupplierinfo, self).write(vals)
    