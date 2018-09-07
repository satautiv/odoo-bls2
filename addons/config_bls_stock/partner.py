# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import api, models, fields
# import time

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    logo_link = fields.Char("Logo Link")
    external_customer_id = fields.Char(
        'External ID', size=64,
        track_visibility='onchange', readonly=True,
        index=True
    )
    external_customer_address_id = fields.Char(
        'External Address ID', size=64,
        track_visibility='onchange', readonly=True,
        index=True
    )
    
    @api.model
    def create_or_update_partner(self, json_data):
        partner_env = self.env['res.partner']
        res_partner_bank_env = self.env['res.partner.bank']
        res_bank_env = self.env['res.bank']
#         intermediate_env = self.env['stock.route.integration.intermediate']

        logo_link = json_data.get('LogoReferenceID', False)
#         if logo_link:
#             company = self.env.user.company_id
#             despatch_api_link = company.despatch_api_link
#             if not despatch_api_link.endswith('/'):
#                 despatch_api_link += "/"
#             if despatch_api_link.endswith('/api/')\
#                 and logo_link.startswith('/api/')\
#             :
#                 despatch_api_link = despatch_api_link[:-5]
#                 
#             logo_link = despatch_api_link + logo_link
        
        id_external = False
        if json_data.get('PartyIdentification', False):
            for party_ident_data in json_data['PartyIdentification']:
                id_attr = party_ident_data['_ext_attributes']['ID']
                if id_attr['schemeID'] == 'COMPANY_ID':
                    id_external = party_ident_data['ID']
                    break
#         
#         id_external = json_data.get('PartyIdentification', False)\
#             and json_data['PartyIdentification'][0]['ID'] or False
        
        partner_id = False
        
        if id_external:
            self._cr.execute('''
                SELECT
                    id
                FROM
                    res_partner
                WHERE external_customer_id = %s
                LIMIT 1
            ''', (id_external,))
            
            sql_res = self._cr.fetchone()
            if sql_res:
                partner_id = sql_res[0]
                
        address_dict = json_data.get('PhysicalLocation', False)\
            and json_data['PhysicalLocation']['Address'] or False
            
        country_code = address_dict and address_dict.get('Country', False)\
            and address_dict['Country'].get('IdentificationCode', False) or ''
        
        country_code = country_code.replace(' ', '') #Normaus kodai neturi tureti tarpu
        
        country_id = False
        if country_code:    
            self._cr.execute('''
                    SELECT
                        id
                    FROM
                        res_country
                    WHERE code = %s
                    LIMIT 1
                ''', (country_code,))
            sql_res = self._cr.fetchone()
            if sql_res:
                country_id = sql_res[0]
            else:    
                country_name = address_dict and address_dict.get('Country', False)\
                    and address_dict['Country'].get('Name', False) or ''
                
                country_id = self.env['res.country'].create({
                    'name': country_name,
                    'code': country_code,
                })
            
#             if not sql_res:
#                 country_name = address_dict and aaddress_dict.get('Country', False)\
#                     and address_dict['Country'].get('Name', False) or ''
#                 country_id = self.env['res.country'].create({
#                     'name': country_name,
#                     'code': country_code,
#                 }) 
#             else:
#                 country_id = sql_res[0]
        
        tax_dict = json_data.get('PartyTaxScheme', False)
        if tax_dict:
            tax_attr_dict = tax_dict.get('_ext_attributes', {})
            
            vat_code_ok = tax_attr_dict.get('CompanyID', False)\
                and tax_attr_dict['CompanyID']['schemeID'] == 'VAT_CODE' or False
        else:
            vat_code_ok = False
            
#         bank_name = ""
#         bank_acc = ""
#         id_bank = ""

        partner_vals = {
            'external_customer_id': id_external,
            'name': json_data.get('PartyName', False) and json_data['PartyName']['Name'],
            'street': address_dict and address_dict['AddressLine']\
                and address_dict['AddressLine'][0]\
                and address_dict['AddressLine'][0]['Line'] or "",
            'country_id': country_id,
#             'vat': vat_code_ok and tax_dict.get('CompanyID', "") or False,
            'ref': json_data.get('PartyLegalEntity', False)\
                and json_data['PartyLegalEntity'][0].get('CompanyID', ""),
            'logo_link': logo_link,
#             'bank_name': bank_name,
#             'bank_account': bank_acc,
#             'external_customer_id_int': id_external_int,
        }
        if vat_code_ok:
            partner_vals['vat'] = tax_dict.get('CompanyID', "")
        
        if not partner_id:
            partner_id = partner_env.create(partner_vals).id
        else:
            if logo_link:
            # --- UZPILDAU LOGO ---
                self._cr.execute('''
                    SELECT
                        id
                    FROM
                        res_partner
                    WHERE id = %s
                        AND logo_link is not null
                    LIMIT 1
                ''', (partner_id,))
                sql_res = self._cr.fetchone()
                if not sql_res:
                    self._cr.execute('''
                        UPDATE res_partner
                        SET logo_link = %s
                        WHERE id = %s
                    ''', (logo_link,partner_id))
                
            # --- UZPILDAU BANKO INFO ---
#             self._cr.execute('''
#                 SELECT
#                     id
#                 FROM
#                     res_partner
#                 WHERE id = %s
#                     AND bank_name is not null
#                     AND bank_account is not null
#                 LIMIT 1
#             ''', (partner_id,))
#             sql_res = self._cr.fetchone()
#             if not sql_res:
#                 self._cr.execute('''
#                     UPDATE res_partner
#                     SET bank_name = %s,
#                         bank_account = %s
#                     WHERE id = %s
#                 ''', (bank_name, bank_acc, partner_id))
                
                
                
#         else:
#             partner = partner_env.browse(partner_id)
#             intermediate_env.remove_same_values(partner, partner_vals)
#             partner.write(partner_vals)

        acc_data = json_data.get('FinancialAccount', False)
        if acc_data:
            bank_acc = acc_data.get("ID", "")
            if acc_data.get("FinancialInstitutionBranch", False)\
                and acc_data['FinancialInstitutionBranch'].get("FinancialInstitution", False)\
            :   
                financial_institution_data = acc_data['FinancialInstitutionBranch']["FinancialInstitution"]
                id_bank = financial_institution_data.get("ID", "")
                bank_name = financial_institution_data.get("Name", "")
                
                self._cr.execute('''
                    SELECT
                        id
                    FROM
                        res_partner_bank
                    WHERE acc_number = %s
                        AND partner_id = %s
                    LIMIT 1
                ''', (bank_acc,partner_id,))
                sql_res = self._cr.fetchone()
                if not sql_res:
                    self._cr.execute('''
                        SELECT
                            id
                        FROM
                            res_bank
                        WHERE id_bank = %s
                        LIMIT 1
                    ''', (id_bank,))
                    sql_res = self._cr.fetchone()
                    bank_id = sql_res and sql_res[0]
                    if not bank_id:
                        bank_id = res_bank_env.create({
                            'id_bank': id_bank,
                            'name': bank_name
                        }).id
                    res_partner_bank_env.create({
                        'acc_number': bank_acc,
                        'partner_id': partner_id,
                        'bank_id': bank_id,
                    })
                    
#         print ("             Creatinant ar surandant KONTRAHENTA uztrukau: %.5f" % (time.time() - t))
        return partner_id
    
    @api.model
    def create_or_update_address(self, json_data):
#         delivery_loc_data = json_data.get('DeliveryLocation', False)
#         if not delivery_loc_data:
#             return False
#         
#         intermediate_env = self.env['stock.route.integration.intermediate']
        addr_id = False
        
        identificator = json_data.get('ID', False)
        
#         id_external_int = False
        
        if identificator:
            attr_data = json_data['_ext_attributes']
            attr_id_data = attr_data['ID']
            id_id_schema = attr_id_data['schemeID']
            
            if id_id_schema == 'POS_ID':
                identificator_field = 'possid_code'
            elif id_id_schema == 'VAT_CODE':
                identificator_field = 'vat'
            elif id_id_schema == 'COMPANY_CODE':
                identificator_field = 'ref'
            
            if not addr_id and identificator_field:    
                sql_sentence = "SELECT id FROM res_partner WHERE %s = '%s' LIMIT 1" % (
                    identificator_field, identificator
                )
                self._cr.execute(sql_sentence)
                sql_res = self._cr.fetchone()
                
                addr_id = sql_res and sql_res[0] or False
        
        
#         if addr_id:
#             addr = self.browse(addr_id)
#             intermediate_env.remove_same_values(addr, vals)
#             try:
#                 addr.write(vals)
#             except:
#                 pass
#         else:
#             if identificator:
#                 vals[identificator_field] = identificator
#                 if identificator_field == 'possid_code':
#                     vals['external_customer_address_id'] = identificator
#             vals['name'] = name
#             addr_id = self.create(vals).id

        if not addr_id:
            addr_data = json_data['Address']
        
            street = ""
            if addr_data.get('StreetName', False) or addr_data.get('BuildingNumber', ''):
                street = "%s %s" % (addr_data.get('StreetName', False), addr_data.get('BuildingNumber', ''))
    
            if addr_data.get('AddressLine', False):
                name = addr_data['AddressLine'][0]['Line']
                if not street:
                    street = name 
            else:
                if addr_data.get('CityName', False):
                    street += ", %s" % (addr_data['CityName'])
                else:
                    name = street
                    
            country_code = addr_data and addr_data.get('Country', False)\
                and addr_data['Country'].get('IdentificationCode', False) or ''
                
            country_code = country_code.replace(' ', '') #Normaus kodai neturi tureti tarpu
      
            if country_code:
                self._cr.execute('''
                        SELECT
                            id
                        FROM
                            res_country
                        WHERE code = %s
                        LIMIT 1
                    ''', (country_code,))
                sql_res = self._cr.fetchone()
                if not sql_res:
                    country_name = addr_data and addr_data.get('Country', False)\
                        and addr_data['Country'].get('Name', False) or ''
                    country_id = self.env['res.country'].create({
                        'name': country_name,
                        'code': country_code,
                    }).id
                else:
                    country_id = sql_res[0]
            else:
                country_id = False
                    
            vals = {
                'street': street,
                'city': addr_data.get('StreetName', ''),
                'country_id': country_id,
#                 'external_customer_address_id_int': id_external_int,
            }
            
            if identificator:
                vals[identificator_field] = identificator
                if identificator_field == 'possid_code':
                    vals['external_customer_address_id'] = identificator
            vals['name'] = name
            addr_id = self.create(vals).id
        
#         print ("             Creatinant ar surandant ADRESA uztrukau: %.5f" % (time.time() - t))
        return addr_id

    @api.model
    def get_partner_vals(self, partner_id, owner_code=False, for_owner=False):
        self._cr.execute('''
            SELECT
                logo_link, external_customer_id,
                possid_code, vat, ref, name, street,
                country_id, parent_id
            FROM
                res_partner
            WHERE id = %s
            LIMIT 1
        ''', (partner_id,))
        logo_link, id_external_customer,\
        possid_code, vat, ref, name,\
        addr_line, country_id, parent_id = self._cr.fetchone()

        if for_owner and not owner_code and ref:
            self._cr.execute('''
                SELECT
                    owner_code
                FROM
                    product_owner
                WHERE ref = %s
                LIMIT 1
            ''', (ref,))
            owner_code, = self._cr.fetchone() or (False,)


        if not addr_line:
            addr_line = '-'
        
        if parent_id:
            self._cr.execute('''
                SELECT
                    name
                FROM
                    res_partner
                WHERE id = %s
                LIMIT 1
            ''', (parent_id,))
            comp_name, = self._cr.fetchone()
        else:
            comp_name = name
        
        
        ident_vals_list = []
        
        if id_external_customer:
            ident_vals_list.append({
              "scheme_id": "COMPANY_ID",
              "scheme_name": "Company ID",
              "scheme_agency_id": "BLS",
              "id": id_external_customer
            })
            
        if possid_code:
            ident_vals_list.append({
              "scheme_id": "POS_ID",
              "scheme_name": "Location ID",
              "scheme_agency_id": "BLS",
              "id": possid_code
            })
            
        if vat:
            ident_vals_list.append({
                "scheme_id": "VAT_CODE",
                "id": vat
            })
            
        if ref:
            ident_vals_list.append({
                "scheme_id": "COMPANY_CODE",
                "id": ref
            })
        if owner_code:
            ident_vals_list.append({
              "scheme_id": "SHORT_NAME",
              "scheme_name": "Short name",
              "id": owner_code
            })
            
        physical_loc_addr_vals = {
            "address": {
                "address_line": [
                    {
                        "line": addr_line
                    }
                ],
            }
        }
        
        currency_name = "EUR"
        
        if country_id:
            self._cr.execute('''
                SELECT
                    name, code, currency_id
                FROM
                    res_country
                WHERE id = %s
                LIMIT 1
            ''', (country_id,))
            country_name, country_code, currency_id = self._cr.fetchone()
            physical_loc_addr_vals['address']['country'] = {
                "name": country_name,
                "identification_code": country_code,
            }
            if currency_id:
                self._cr.execute('''
                    SELECT
                        name
                    FROM
                        res_currency
                    WHERE id = %s
                    LIMIT 1
                ''', (currency_id,))
                currency_name, = self._cr.fetchone()
        
        res = {
            "party_name": {
                "name": name
            },
            "physical_location": physical_loc_addr_vals
        }
        if logo_link:
            res['logo_reference_id'] = logo_link
        if ident_vals_list:
            res['party_identification'] = ident_vals_list
            
        if vat:
            res['party_tax_scheme'] = {
                "scheme_id": "VAT_CODE",
                "company_id": vat,
                "registration_name": comp_name,
                "tax_scheme": {
                    "currency_code": currency_name,
                    "tax_type_code": "VAT"
                  
                }
            }
        if ref:
            res['party_legal_entity'] = {
                "scheme_id": "COMPANY_CODE",
                "company_id": ref,
                "registration_name": comp_name,
            }
            
        self._cr.execute('''
            SELECT
                acc_number, bank_id
            FROM
                res_partner_bank
            WHERE partner_id = %s
            ORDER BY create_date DESC
            LIMIT 1
        ''', (partner_id,))
        sql_res = self._cr.fetchone()
        if sql_res:
            acc_number, bank_id = sql_res
            
            res['financial_account'] = {
                "id": acc_number,
            }
            if bank_id:
                self._cr.execute('''
                    SELECT
                        name, id_bank
                    FROM
                        res_bank
                    WHERE id = %s
                    LIMIT 1
                ''', (bank_id,))
                bank_name, id_bank = self._cr.fetchone()
                if id_bank:
                    res['financial_account']['financial_institution_branch'] = {
                        "financial_institution": {
                            "id": id_bank,
                        }
                    }
                    if bank_name:
                        res['financial_account']['financial_institution_branch']['financial_institution']['name'] = bank_name
                    
        return res
    
    @api.model
    def get_partner_location_vals(self, partner_id):
        self._cr.execute('''
            SELECT
                possid_code, name, street,
                country_id
            FROM
                res_partner
            WHERE id = %s
            LIMIT 1
        ''', (partner_id,))
        possid_code, name, addr_line, country_id = self._cr.fetchone()
        
        if possid_code:
            res = {
              "scheme_id": "POS_ID",
              "scheme_name": "Location ID",
              "scheme_agency_id": "BLS",
              "id": possid_code
            }
        else:
            res = {}

        if name:
            res['name'] = name   

        res["address"] = {
            "address_line": [
                {
                    "line": addr_line
                }
            ],
        }

        if country_id:
            self._cr.execute('''
                SELECT
                    name, code
                FROM
                    res_country
                WHERE id = %s
                LIMIT 1
            ''', (country_id,))
            country_name, country_code= self._cr.fetchone()
            res['address']['country'] = {
                "name": country_name,
                "identification_code": country_code,
            }  
        return res

class ResPartnerCoordinate(models.Model):
    _name = 'res.partner.coordinate'
    _description = 'Coordinates'
    
    code = fields.Char("Coordinate System Code")
    unit_code = fields.Char("Unit Code")
    latitude_dagrees = fields.Char("Latitude Dagrees")
    latitude_minutes = fields.Char("Latitude Minutes")
    longitude = fields.Char("Longitude Dagrees")
    longitude_minutes = fields.Char("Latitude Minutes")
    
class ResBank(models.Model):
    _inherit = 'res.bank'
    
    id_bank = fields.Char("Bank ID")
    