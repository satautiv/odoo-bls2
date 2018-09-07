# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################
from odoo import models, fields, api, _
from openerp.exceptions import UserError
from odoo.osv.expression import get_unaccent_wrapper

import time
import json

from .stock import get_local_time_timestamp


class ResCountry(models.Model):
    _inherit = 'res.country'


    code = fields.Char('Country Code', size=5,
        help='The ISO country code in two chars. You can use this field for quick search.'
    )
    vat_code = fields.Char('VAT Code', size=2)


class PartnerOwnerLanguage(models.Model):
    _name = 'partner.owner.language'
    _description = 'Packing for Products'
    
    @api.model
    def _get_languages(self):
        return self.env['product.owner']._get_languages()
    
    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    lang = fields.Selection(_get_languages, 'Language', required=True)
    owner_id = fields.Many2one('product.owner', 'Owner', required=True)
    
    _sql_constraints = [
        ('partner_owner_unique', 'unique (partner_id, owner_id)', 'Owner has to be unique per partner')
    ]   

    @api.model
    def create_if_not_exist(self, vals):
        lang = self.search([
            ('partner_id','=',vals['partner_id']),
            ('lang','=',vals['lang']),
            ('owner_id','=',vals['owner_id']),
        ], limit=1)
        if not lang:
            lang = self.create(vals)
        return lang

class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'mail.thread']

    driving_contract_number = fields.Char(
        'Transfer Contract Number', size=128,
        track_visibility='onchange'
    )
    product_contract_number = fields.Char(
        'Product Contract Number', size=128,
        track_visibility='onchange'
    )
    intermediate_id = fields.Many2one(
        'stock.route.integration.intermediate', 'Created by Intermediate Object',
        track_visibility='onchange', readobly=True
    )
    external_customer_id = fields.Char(
        'External ID', size=64,
        track_visibility='onchange', readonly=True
    )
    external_customer_address_id = fields.Char(
        'External Address ID', size=64,
        track_visibility='onchange', readonly=True
    )
    customer_vip = fields.Boolean('VIP', track_visibility='onchange')
    possid_code = fields.Char('POSSID', size=64,
        track_visibility='onchange'
    )
    name = fields.Char('Name',
        track_visibility='onchange'
    )
    parent_id = fields.Many2one('res.partner', 'Related Company',
        track_visibility='onchange'
    )
    child_ids = fields.One2many('res.partner', 'parent_id',
        'Contacts', domain=[('active', '=', True)],
         track_visibility='onchange'
    )
    ref = fields.Char('Contact Reference', track_visibility='onchange')
    vat = fields.Char('TIN', track_visibility='onchange',
        help="Tax Identification Number. Check the box if this contact is subjected to taxes. Used by the some of the legal statements."
    )
    comment = fields.Text('Notes', track_visibility='onchange')
    active = fields.Boolean('Active', track_visibility='onchange', default=True)
    street = fields.Char('Street', track_visibility='onchange')
    street2 = fields.Char('Street2', track_visibility='onchange')
    zip = fields.Char('Zip', size=24,track_visibility='onchange', change_default=True)
    city = fields.Char('City', track_visibility='onchange')
    state_id = fields.Many2one("res.country.state", 'State',
        track_visibility='onchange', ondelete='restrict'
    )
    country_id = fields.Many2one('res.country', 'Country',
        ondelete='restrict', track_visibility='onchange'
    )
    email = fields.Char('Email', track_visibility='onchange')
    phone = fields.Char('Phone', track_visibility='onchange')
    fax = fields.Char('Fax', track_visibility='onchange')
    mobile = fields.Char('Mobile', track_visibility='onchange')
    district = fields.Char('District', size=256, track_visibility='onchange')
    owner_code = fields.Char('Owner Code', track_visibility='onchange')
    sanitex_type = fields.Selection([
        ('1', 'Local Company'),
        ('2', 'Foreign Company'),
        ('3', 'Individual'),
        ('4', 'Reserved'),
        ('5', 'Embassy'),
    ], 'Client Type', track_visibility='onchange')
    supplier_code = fields.Char("Supplier Code")
    local_partner = fields.Boolean('Local Partner')
    owner_lang_ids = fields.One2many(
        'partner.owner.language', 'partner_id', 'Owners'
    )
    
    inidividual_actv_nr = fields.Char("Invidual Activity No.")
    farmer_code = fields.Char("Farmer Code")
    bsn_lic_nr = fields.Char("Business License No.")
    route = fields.Char("Route")
    bank_name = fields.Char("Bank Name")
    bank_account = fields.Char("Bank Account")
    alcohol_license_type = fields.Char("Alcohol License Type")
    alcohol_license_sale_type = fields.Char("Alcohol License Sale Type")
    alcohol_license_no = fields.Char("Alcohol License No.")
    alcohol_license_date = fields.Date("Alcohol License Date")
    alcohol_license_consume = fields.Char("Alcohol License Consume")
    tobac_license_type = fields.Char("Tobac License Type")
    tobac_license_sale_type = fields.Char("Tobac License Sale Type")
    tobac_license_no = fields.Char("Tobac License No.")
    tobac_license_date = fields.Date("Tobac License Date")
    client_code = fields.Char("Client Code")
    parent_ref = fields.Char('Company Code', size=32, readonly=True)
    posid_name = fields.Char('POSID Name', size=128)
    supplier_code = fields.Char('Supplier Code', size=64)
    carrier = fields.Boolean("Carrier", default=False)
    id_version = fields.Char('POD Version', size=128, readonly=True)
    id_carrier = fields.Char('Carrier ID', size=32, help='Used in POD integration.')
    dos_location = fields.Boolean('DOS Location', readonly=True, default=False)
    
#     external_customer_id_int = fields.Integer(
#         'External ID', readonly=True, index=True
#     )
#     external_customer_address_id_int = fields.Integer(
#         'External Address ID', readonly=True, index=True
#     )

#     _sql_constraints = [
#         ('number_ref', 'unique(company_id, country_id, ref)', 'Registration Code Number must be unique per Company and Country!'),
#     ]

    
#    @api.model
#    def test_f(self):
#        print 'self', self
#        print self.env['product.product'].browse(69246), self.env['product.product'].browse([70116, 69436]), self.env['product.product'].browse(69246) + self.env['product.product'].browse(70116) 
#        return True

    @api.model
    def get_partner_by_carrier_id(self, carrier_id):
        carrier = self.search([
            ('ref','=',carrier_id),
            ('supplier','=',True),
            ('is_company','=',True),
            ('carrier','=',True)
        ], limit=1)
        if not carrier:
            carrier = self.search([
                ('ref', '=', carrier_id),
                ('supplier', '=', True),
                ('is_company','=',True),
            ], limit=1)
        return carrier

    @api.multi
    def get_client_dict_for_tare_report(self):
        return {
            'Name': self.parent_id and self.parent_id.name or '',
            'RegCode': self.parent_id and self.parent_id.ref or '',
            'VatCode': self.parent_id and self.parent_id.vat or '',
            'RegAddress': self.parent_id and self.parent_id.street or '',
            'InidividualActvNr': '',
            'FarmerCode': '',
            'POSAddress': self.street or '',
            'PosName': '',
            'InnerCode': self.possid_code or '',
            'BSNLicNr': '',
            'Phone': self.phone or self.mobile or '',
            'Fax': self.fax or '',
            'POSAddress2': '',
            'EUText': '',
            'PosCode': self.possid_code or '',
            'PersonName': '',
        }

    @api.model
    def get_empty_carrier_dict_from_carrier(self):
        return {
            'Name': '',
            'RegCode': '',
            'VATCode': '',
            'RegAddress': '',
            'Driver': '',
            'CarNumber': '',
            'TrailNumber': '',
            'AgreementText': '',
            'id_version': '',
        }


    @api.multi
    def get_carrier_dict_from_carrier(self):
        return {
            'Name': self and self.name or '',
            'RegCode': self and self.ref or '',
            'VATCode': self and self.vat or '',
            'RegAddress': self and self.street or '',
            'Driver': '',
            'CarNumber': '',
            'TrailNumber': '',
            'AgreementText': self and self.driving_contract_number or '',
            'id_version': self and self.id_version or '',
        }

    @api.model_cr
    def init(self):
        cr = self.env.cr
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('res_partner_external_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX res_partner_external_id_index ON res_partner (external_customer_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('res_partner_address_external_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX res_partner_address_external_id_index ON res_partner (external_customer_address_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('res_partner_intermediate_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX res_partner_intermediate_id_index ON res_partner (intermediate_id)')
    
    @api.multi
    def get_client_dict(self):
        d = {
             'posid': self.possid_code or '',
             'name': self.parent_id and self.parent_id.name or self.name or '',
             'registrationaddress': self.parent_id and self.parent_id.street or self.street or '',
             'posaddress': self.street or ''
        }
        return d


    @api.model
    def show_print_button(self, ids, context):
        return False


    @api.model
    def check_person_code_control_number(self, code):
        if not code:
            return False
        if not code.isdigit():
            return False
        if len(code) != 11:
            return False
        checksum = checksum2 = 0
        for i in range(10):
            d1 = i + 1 
            d2 = i + 3
            if d1 >= 10:
                d1 = d1 % 9
            if d2 >= 10:
                d2 = d2 % 9
            checksum += int(code[i]) * d1
            checksum2 += int(code[i]) * d2
        if checksum % 11 != 10:
            checkno = checksum % 11
        elif checksum2 % 11 != 10:
            checkno = checksum2 % 11
        else:
            checkno = 0
        return checkno == int(code[-1])

    @api.model
    def check_registration_code_control_number(self, code):
        if not code:
            return False
        if not code.isdigit():
            return False
        if len(code) != 9:
            return False
        checksum = 0
        for i in range(8):
            checksum += int(code[i]) * (i+1)
        if checksum % 11 == 10:
            return False
        else:
            return checksum % 11 != 10 and checksum % 11 == int(code[-1])

    @api.model
    def check_registration_code(self, code, country='LT'):
        if not code:
            raise UserError(_('Registration code cannot be empty'))
        if country in ['LT', 'LTU']:
            if not code.isdigit():
                raise UserError(_('Registration code should consist of digits (code: %s)') % code)
            if len(code) != 9:
                raise UserError(_('Registration code should consist of 9 digits (code: %s)') % code)
            if not self.check_registration_code_control_number(code):
                raise UserError(_('Wrong registration code (code: %s)') % code)
        return True

    @api.model
    def check_person_code(self, code, country='LT'):
        if not code:
            raise UserError(_('Person code cannot be empty'))
        if country in ['LT', 'LTU']:
            if not code.isdigit():
                raise UserError(_('Person code should consist of digits (code: %s)') % code)
            if len(code) != 11:
                raise UserError(_('Person code should consist of 11 digits (code: %s)') % code)
            if not self.check_person_code_control_number(code):
                raise UserError(_('Wrong Person code (code: %s)') % code)
        return True

    @api.model
    def check_vat_code(self, vat, country='LT'):
        if len(vat) < 10:
            raise UserError(_('VAT code should consist at least of 10 symbols (vat: %s)') % vat)
        if vat[:2] != country:
            raise UserError(_('VAT code(%s) should begin with %s') % (vat, country))
        if not vat[2:].isdigit():
            raise UserError(_('VAT code(%s) should consist of %s and digits') % (vat, country))
        return True

    @api.multi
    def check_partner(self):
        # Paprašė BLS padaryti klietų tikrinimą bet kai padarėm nesugebėjo normaliai klientų importuoti,
        # kurie tą tikrinimą praeitų. Tai išjungėm. galbūt laikinai.

        context = self.env.context or {}
        if context.get('skip_partner_check', False):
            return True
        for partner in self:
            if partner.sanitex_type == '1':#Local Company
                self.check_registration_code(partner.ref and partner.ref.strip() or '', partner.country_id and partner.country_id.code or 'LT')
            elif partner.sanitex_type == '2':#Foreign Company
                self.check_registration_code(partner.ref and partner.ref.strip() or '', 'EU')
            elif partner.ref and partner.sanitex_type == '3':#Invdividual
                self.check_person_code(partner.ref.strip())
            if partner.company_type == 'company' and not partner.name:
                raise UserError(_('Name field cannot be empty'))
            if partner.vat:
                self.check_vat_code(
                    partner.vat.strip(),
                    partner.country_id and partner.country_id.code[:2] or 'LT',
                )
        return True

    @api.multi
    def get_product_qty(self, product_id):
        #nebenaudojama
        part_stock_obj = self.env['sanitex.product.partner.stock']
        part_stocks = part_stock_obj.search([
            ('partner_id','=',self.id),
            ('product_id','=',product_id),
        ], limit=1)
        if part_stocks:
            return part_stocks.qty_available
        return 0.0
    
    @api.multi
    def get_product_qty_new(self, product_id):
        #nebenaudojama
        self.env.cr.execute("""
            SELECT
                qty_available            
            FROM
                sanitex_product_partner_stock 
            WHERE 
                partner_id = %s
                and product_id = %s
        """ % (str(self.id), str(product_id)))
        results = self.env.cr.fetchone()
        if results:
            return results[0]
        return 0.0

    @api.multi
    def get_products_with_debt(self):
        sql = '''
            SELECT product_id, sum(qty_available), product_code
            FROM
                sanitex_product_partner_stock
            WHERE
                partner_id = %s
            GROUP BY
                product_id, product_code
            HAVING
                sum(qty_available) > 0.0
        '''
        self.env.cr.execute(sql, (self.id,))
        return self.env.cr.fetchall()


    @api.multi
    def carrier_to_dict_for_rest_integration(self):
        return {
            "active": self.active,
            "allowVehicleSubstitution": True,
            "requireOdometerReadingEntry": True,
            # "tenant": False,
            # "createdAt": "",
            # "updatedAt": "",
            # "updateInc": 0,
            "deleted": False,
            "carrierId": self.external_customer_id or '',
            # "shortName": "",
            "companyId": self.ref or '',
            "companyName": self.name or '',
            "countryCode": self.country_id and self.country_id.code or ''
        }

    @api.multi
    def supplier_to_dict_for_rest_api(self):
        return {
            'supplierId': self.external_customer_id or '',
            # 'shortName': '',#Negaunam
            'companyId': self.ref or '',
            'companyName': self.name or '',
            'countryCode': self.country_id and self.country_id.code or '',
            'deleted': False,
        }

    @api.multi
    def posid_to_dict_for_rest_integration(self):
        return {
            'placeId': self.possid_code or '',
            'name': self.name or self.parent_id and self.parent_id.name or '',
            'postCode': self.zip or '',
            'streetAddress': self.street or '',
            'type': 'pos',#neaišku kaip nustatyt
            # 'description': '',
            # 'locality': '',
            # 'location': '',
            'email': self.email or '',
            'forkliftNeeded': '',#Negaunam
            'manualHandlingNeeded': '',#Negaunam
            'phone': self.phone or self.mobile or '',
            'vehicleMaxPallets': '',#Negaunam
            'vehicleMinPallets': '',#Negaunam
            'requireVerificationOnShipment': '',#Negaunam
            'requirePODDocumentScan': '',#Negaunam
            'companyId': self.parent_id and self.parent_id.ref or '',
            # 'shortName': '',#Negaunam
            'companyName': self.parent_id and self.parent_id.name or '',
            'deleted': False,
            'active': self.active,
            'countryCode': self.country_id and self.country_id.code or '',
        }

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

        res = super(ResPartner, self).search(
            args, offset=offset, limit=limit,
            order=order, count=count
        )
        return res

    @api.model
    def check_partner_vals(self, partner_vals):
        return True

    @api.model
    def create_partner(self, vals, address=False):
        interm_obj = self.env['stock.route.integration.intermediate']
        country_obj = self.env['res.country']
        state_obj = self.env['res.country.state']
        
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        
        ctx_active = context.copy()
        ctx_active['active_test'] = False
        
        partner_vals = {}
        partner_vals.update(vals.copy())
        if partner_vals.get('country', False):
            country = country_obj.search([('name','=',partner_vals['country'])], limit=1)
            if not country:
                country = country_obj.search([('code', '=', partner_vals['country'])], limit=1)
            if not country:
                country_vals = country_obj.default_get(country_obj._fields)
                country_vals['name'] = partner_vals['country']
                country_vals['code'] = partner_vals['country']
                country = country_obj.create(country_vals)
            partner_vals['country_id'] = country.id
        else:
            country = country_obj.search([('code','=','LTU')], limit=1)
            partner_vals['country_id'] = country.id
        if partner_vals.get('region', False):
            region = state_obj.search([
                ('code','=',partner_vals['region'][:3]),
                ('country_id','=',partner_vals['country_id'])
            ], limit=1)
            if region:
                partner_vals['state_id'] = region.id
            else:
                try:
                    partner_vals['state_id'] = state_obj.create({
                        'name': partner_vals['region'],
                        'code': partner_vals['region'][:3],
                        'country_id': country.id
                    }).id
                except:
                    pass
        if 'region' in partner_vals.keys():
            del partner_vals['region']
                    
        if 'country' in partner_vals:
            del partner_vals['country']
        if 'address' in partner_vals:
            partner_vals['street'] = partner_vals['address']
            del partner_vals['address']
        if partner_vals.get('sanitex_type', '1') not in ['1', '2', '3', '4', '5']:
             partner_vals['sanitex_type'] = '1'
             
                
        if not address:
            client = self.with_context(ctx_active).search([
                ('external_customer_id','=',vals['external_customer_id'])
            ], limit=1)
            # partner_vals['company_type'] = 'company'
            partner_vals['is_company'] = True
            partner_vals['supplier'] = True
            if 'vat' in partner_vals.keys():
                if len(partner_vals['vat']) > 1 and (partner_vals['vat'][0].isdigit()
                    or partner_vals['vat'][1].isdigit()) and 'country_id' in partner_vals.keys() \
                :
                    country = country_obj.browse(partner_vals['country_id'])
                    if country.code in ['LT','LTU']:
                        partner_vals['vat'] = 'LT' + partner_vals['vat']
            partner_vals['intermediate_id'] = context.get('intermediate_id', False)
            if client:
                interm_obj.remove_same_values(client, partner_vals)
                if partner_vals:
                    client.write(partner_vals)
                    if 'updated_partner_ids' in context:
                        context['updated_partner_ids'].append((vals['external_customer_id'], client.id))
            else:
                if not partner_vals.get('active', True) and not partner_vals.get('name', ''):
                    partner_vals['name'] = partner_vals['external_customer_id']
                vals2 = {}

                vals2.update(self.default_get(self._fields))
                vals2.update(partner_vals)
                vals2['display_name'] = vals['name']
                client = self.create(vals2)
                # self.invalidate_cache(['display_name'])
                # self.env.add_todo(self._fields['display_name'], client)
                # self.recompute()
                if 'created_partner_ids' in context:
                    context['created_partner_ids'].append((vals['external_customer_id'], client.id))
            if commit:
                self.env.cr.commit()
            return client
        else:
            address = self.with_context(ctx_active).search([
                ('external_customer_address_id','=',vals['external_customer_id'])
            ], limit=1)
            partner_vals['external_customer_address_id'] = vals['external_customer_id']
            del partner_vals['external_customer_id']
            partner_vals['company_type'] = 'person'
            partner_vals['is_company'] = False
            partner_vals['type'] = 'delivery'
            partner_vals['intermediate_id'] = context.get('intermediate_id', False)
            if address:
                interm_obj.remove_same_values(address, partner_vals)
                if partner_vals:
                    address.write(partner_vals)
                    if 'updated_partner_ids' in context:
                        context['updated_partner_ids'].append((vals['external_customer_id'], address.id))
            else:
                self.check_partner_vals(partner_vals)
                vals2 = {}
                vals2.update(self.default_get(self._fields))
                vals2.update(partner_vals)
                address = self.create(vals2)
                self.invalidate_cache(['display_name'])
                address.env.add_todo(self._fields['display_name'], address)
                address.recompute()
                if 'created_possid_ids' in context:
                    context['created_possid_ids'].append((vals['external_customer_id'], address.id))
            if commit:
                self.env.cr.commit()
            return address

    @api.model
    def get_vat_by_ref(self, partner_ref):
        vat_code = ''
        if partner_ref:
            for partner in self.search([('ref','=',partner_ref)]):
                if partner.vat:
                    vat_code = partner.vat
                    break
        return vat_code

    @api.multi
    def get_address(self):
        parts = []
#         if self.street:
#             parts.append(self.street)
        self._cr.execute('''
            SELECT
                street
            FROM
                res_partner
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        street, = self._cr.fetchone()
        if street:
            parts.append(street)
        
        return ', '.join(parts)

    @api.multi
    @api.depends('name', 'street')
    def name_get(self):
        context = self.env.context or {}
        res = []
        for partner in self:
            if partner.is_company:
                name = partner.name
            else:
                name = partner.get_address()
                if not name and self.env['res.users'].sudo().search([('partner_id','=',partner.id)]):
                    name = partner.name
                if context.get('include_posid_into_name', False) and partner.possid_code:
                    name = partner.possid_code + ' - ' + name
            if partner.supplier_code:
                name = "%s (%s)" % (partner.supplier_code, name)
                    
            res.append((partner.id, name))
        return res


    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            self.check_access_rights('read')
            where_query = self._where_calc(args)
            self._apply_ir_rules(where_query, 'read')
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            where_str = where_clause and (" WHERE %s AND " % where_clause) or ' WHERE '

            # search on the name of the contacts and of its company
            search_name = name
            if operator in ('ilike', 'like'):
                search_name = '%%%s%%' % name
            if operator in ('=ilike', '=like'):
                operator = operator[1:]

            unaccent = get_unaccent_wrapper(self.env.cr)

            query = """SELECT id
                         FROM res_partner
                      {where} ({email} {operator} {percent}
                           OR {display_name} {operator} {percent}
                           OR {reference} {operator} {percent}
                           OR {vat} {operator} {percent}
                           OR {possid_code} {operator} {percent})
                           -- don't panic, trust postgres bitmap
                     ORDER BY {display_name} {operator} {percent} desc,
                              {display_name}
                    """.format(where=where_str,
                               operator=operator,
                               email=unaccent('email'),
                               display_name=unaccent('display_name'),
                               reference=unaccent('ref'),
                               percent=unaccent('%s'),
                               vat=unaccent('vat'),
                               possid_code=unaccent('possid_code'),)

            where_clause_params += [search_name]*6
            if limit:
                query += ' limit %s'
                where_clause_params.append(limit)
            self.env.cr.execute(query, where_clause_params)
            partner_ids = [row[0] for row in self.env.cr.fetchall()]
            if partner_ids:
                return self.browse(partner_ids).name_get()
            else:
                return []
        return super(ResPartner, self).name_search(name, args, operator=operator, limit=limit)


    @api.model
    def CreateClient(self, list_of_client_vals):
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        inter_obj = self.env['stock.route.integration.intermediate']
        log_obj = self.env['delivery.integration.log']
        
        datetime = time.strftime('%Y-%m-%d %H:%M:%S')
        
        ctx_en = context.copy()
        ctx_en['lang'] = 'en_US'
        error = False#self.with_context(ctx_en).check_imported_client_values(list_of_client_vals)
        if error:
            log_vals = {
                'create_date': datetime,
                'function': 'CreateClient',
                'received_information': str(json.dumps(list_of_client_vals, indent=2)),
                'returned_information': str(json.dumps(error, indent=2))
            }
            log_obj.create(log_vals)
            return error
        
        itermediate = inter_obj.create({
            'datetime': datetime,
            'function': 'CreateClient',
            'received_values': str(json.dumps(list_of_client_vals, indent=2)),
            'processed': False
        })
        if commit:
            self.env.cr.commit()
        itermediate.process_intermediate_objects_threaded()
        return itermediate.id

    @api.model
    def CreatePOSID(self, list_of_posid_vals):
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        inter_obj = self.env['stock.route.integration.intermediate']
        log_obj = self.env['delivery.integration.log']
        
        create_datetime = time.strftime('%Y-%m-%d %H:%M:%S')
        
        ctx_en = context.copy()
        ctx_en['lang'] = 'en_US'
        error = self.with_context(ctx_en).check_imported_posid_values(list_of_posid_vals)
        if error:
            log_vals = {
                'create_date': create_datetime,
                'function': 'CreatePOSID',
                'received_information': str(json.dumps(list_of_posid_vals, indent=2)),
                'returned_information': str(json.dumps(error, indent=2))
            }
            log_obj.create(log_vals)
            return error
        
        itermediate = inter_obj.create({
            'datetime': create_datetime,
            'function': 'CreatePOSID',
            'received_values': str(json.dumps(list_of_posid_vals, indent=2)),
            'processed': False
        })
        if commit:
            self.env.cr.commit()
        itermediate.process_intermediate_objects_threaded()
        return itermediate.id
        
    @api.model
    def check_imported_client_values(self, list_of_client_vals):
        inter_obj = self.env['stock.route.integration.intermediate']
        result = {}
        inter_obj.check_import_values(list_of_client_vals,
            ['external_customer_id',], result
        )
                 
        i = 0
        for client_dict in list_of_client_vals:
            i = i + 1
            index = str(i)
            if client_dict.get('customer_active', 'N') == 'Y' and not client_dict.get('customer_name', ''):
                msg = _('\'Active\' is marked in Client.') + ' ' +  _('You have to fill in value: %s') % 'customer_name'
                if index in result.keys():
                    result[index].append(msg)
                else:
                    result[index] = [msg]
        return result

    @api.model
    def check_imported_posid_values(self, list_of_posid_vals):
        inter_obj = self.env['stock.route.integration.intermediate']
        result = {}
        inter_obj.check_import_values(
            list_of_posid_vals, [
                'external_buyer_address_id', 'external_customer_id', 
                'buyer_address_possid_code'
            ], result
        )
        return result
    
    @api.multi
    def check_existing_quantities(self):
        # Patikrina ar naujai sukurtam klientui jau yra registruotos skolos
        # Jei yra tai prie skolos objekto priskiria klientą (kliento posidą)

        quantities = self.env['sanitex.product.partner.stock'].search([
            ('external_posid_id','=',self.external_customer_address_id),
            ('partner_id','=',False)
        ])
        if quantities:
            quantities.write({'partner_id': self.id})
        return True
    
    @api.model
    def update_vals(self, vals):
        
        if vals.get('parent_id', False):
            parent = self.browse(vals['parent_id'])
            vals['parent_ref'] = parent.ref
        if 'country_id' in vals.keys():
            comp = self.env['res.users'].browse(self.env.uid).company_id
            vals['local_partner'] = comp.country_id and comp.country_id.id == vals['country_id'] or False

    @api.model
    def create(self, vals):
        self.update_vals(vals)
        vals['id_version'] = get_local_time_timestamp()
        partner = super(ResPartner, self).create(vals)
        if vals.get('external_customer_address_id', False):
            partner.check_existing_quantities()
#         if not (vals.get('external_customer_id_int', False) or vals.get('external_customer_address_id_int', False)):
#             partner.calc_int_identificators()
        return partner

    @api.multi
    def write(self, vals):
        self.update_vals(vals)
        
        fields_set = {'active', 'external_customer_id', 'ref', 'name', 'country_id'}
        recalc_id_version = set(vals.keys()) & fields_set
        
        if len(self) == 1 and vals.get('id_version', False):
            res = super(ResPartner, self).write(vals)
        elif recalc_id_version:
            for partner in self:
                vals['id_version'] = get_local_time_timestamp()
                res = super(ResPartner, self).write(vals)
        else:
            res = super(ResPartner, self).write(vals)
            
#         if vals.get('external_customer_address_id', False)\
#             or vals.get('external_customer_id', False)\
#         :
#             for partner in self:
#                 partner.calc_int_identificators()
#         if set(['name', 'vat', 'ref', 'country_id']) & set(vals.keys()):
#             self.check_partner(cr, uid, ids, context=context)
        return res

    @api.multi
    def unlink(self):
        context = self.env.context or {}
        if not context.get('allow_to_delete_clients', False):
            raise UserError(_('You cannot delete clients or posids'))
        return super(ResPartner, self).unlink()

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        res = super(ResPartner, self).onchange_parent_id()
        if self.vat:
            self.vat = False
        return res

    @api.model
    def _commercial_fields(self):
        res = super(ResPartner, self)._commercial_fields()
        if 'vat' in res:
            res.remove('vat')
        return res
        
    
    @api.multi
    def get_debt(self, product_id, price=None):
        return self.env['sanitex.product.partner.stock'].get_quantity(
            product_id, self.id, price=price
        )
#         debt = 0
#         partner_debt = self.env['sanitex.product.partner.stock'].search([
#             ('product_id','=',product_id),('partner_id','=',self.id)
#         ])
#         if partner_debt:
#             debt = partner_debt[0].qty_available
#         return debt

    @api.multi
    def get_quantities_by_price(self, product_id, qty=None):
        return self.env['sanitex.product.partner.stock'].get_quantities_by_price(
            product_id, self.id, qty=qty
        )
        
    @api.multi
    def open_route_templates(self):
        route_tempalte_env = self.env['stock.route.template']
        route_tempalte_action = self.env.ref('config_sanitex_delivery.route_template_action').read({})[0]
        route_tmpl_ids = route_tempalte_env.get_route_template_ids_by_posid(self.possid_code)
        if route_tempalte_action.get('context', False):
            ctx_str = route_tempalte_action['context']
            try:
                ctx = eval(ctx_str)
                if ctx.get('search_default_current', False):
                    ctx['search_default_current'] = False
                    route_tempalte_action['context'] = str(ctx)
            except:
                pass
        
        route_tempalte_action['domain'] = [('id','in',route_tmpl_ids)]

        return route_tempalte_action
    
    @api.model
    def recalc_carriers(self):
        carriers = self.env['res.partner']
        loc_env = self.env['stock.location']
        drivers = loc_env.search([('driver','=',True)])
        
        for driver in drivers:
            if driver.owner_id:
                carriers |= driver.owner_id
        carriers.write({'carrier': True})
        return True
    
    @api.model
    def get_pod_domain(self, obj):
        if obj == 'carrier':
            return [('carrier','=',True)]
        elif obj == 'supplier':
            return [('supplier','=',True)]
        return []
    
    @api.multi
    def set_version(self):
        for partner in self:
            self._cr.execute('''
                UPDATE
                    res_partner
                SET
                    id_version = %s
                WHERE id = %s
            ''', (get_local_time_timestamp(), partner.id))
        return True
        
        
    @api.multi
    def to_dict_for_pod_integration(self, obj):
        if obj == 'carrier':
            res = {
                "active": self.active,
                "allowVehicleSubstitution": True,
                "requireOdometerReadingEntry": True,
                "deleted": False,
                "carrierId": self.external_customer_id or '',
                "companyId": self.ref or '',
                "companyName": self.name or '',
                "countryCode": self.country_id and self.country_id.code or '',
                "id_version": self.id_version,
            }
        else: #supplier
            res = {
                "supplierId": self.external_customer_id or '',
                "shortName": self.supplier_code or "",
                "companyId": self.ref or '',
                "companyName": self.name or '',
                "countryCode": self.country_id and self.country_id.code or '',
                "active": self.active,
                "deleted": False,
                "id_version": self.id_version,
            }
        
        return res    
    
#     @api.multi
#     def calc_int_identificators(self):
#         self.ensure_one()
#         
#         self._cr.execute('''
#             SELECT
#                 external_customer_address_id, external_customer_id
#             FROM
#                 res_partner
#             WHERE id = %s
#             LIMIT 1
#         ''', (self.id,))
#         external_customer_address_id, external_customer_id = self._cr.fetchone()
#         
#         sql_values_to_set_list = []
#         
#         if external_customer_address_id and external_customer_address_id[0] != '0':
#             try:
#                 sql_values_to_set_list.append(
#                     "external_customer_address_id_int = %s" % (int(external_customer_address_id))
#                 )
#             except:
#                 pass
#             
#         if external_customer_id and external_customer_id[0] != '0':
#             try:
#                 sql_values_to_set_list.append(
#                     "external_customer_id_int = %s" % (int(external_customer_id))
#                 )
#             except:
#                 pass
#             
#         if sql_values_to_set_list:
#             self._cr.execute('''
#                 UPDATE
#                     res_partner
#                 SET %s
#                 WHERE id = %s
#             ''' % (', '.join(sql_values_to_set_list), self.id))
#             
#         return True