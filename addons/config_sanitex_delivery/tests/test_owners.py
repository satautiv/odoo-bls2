# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################
from odoo.addons.config_sanitex_delivery.tests.sanitex_tests import SanitexTesting

class TestOwners(SanitexTesting):

    def create_owner(self, owner_vals):
        a = self.product_owner_model.with_context({'no_commit': True}).CreateOwner([owner_vals])
        self.intermediate_model.with_context({'no_commit': True}).browse([a]).process_intermediate_objects()
        owners = self.product_owner_model.search([('intermediate_id','=',a)])
        if not owners:
            intermediate = self.intermediate_model.browse(a)
            self.assertEqual(1, 2, 'No Owner' + intermediate.traceback_string)
        else:
            owner = owners[0]

            self.assertEqual(
                owner.active, owner_vals['active']=='Y',
                'Owner Import (active)'
            )
            self.assertEqual(
                owner.waybill_declare, owner_vals['waybilldeclare']=='Y',
                'Owner Import (waybilldeclare)'
            )
            self.assertEqual(
                owner.vat, owner_vals['vat'],
                'Owner Import (vat)'
            )
            self.assertEqual(
                owner.waybill_declare_date_from, owner_vals['waybilldeclaredatefrom'],
                'Owner Import (waybilldeclaredatefrom)'
            )
            self.assertEqual(
                owner.product_owner_external_id, owner_vals['external_owner_id'],
                'Owner Import (product_owner_external_id)'
            )
            self.assertEqual(
                owner.owner_code, owner_vals['owner_code'],
                'Owner Import (owner_code)'
            )
            self.assertEqual(
                owner.name, owner_vals['name'],
                'Owner Import (name)'
            )
            self.assertEqual(
                owner.ref, owner_vals['ref'],
                'Owner Import (ref)'
            )
            self.assertEqual(
                owner.intermediate_id.id, a,
                'Owner Import (Intermediate ID)'
            )
            companies = self.company_model.search([('company_code','=',owner_vals['firm_id'])])
            if companies:
                self.assertEqual(
                    owner.company_id.id, companies[0].id,
                    'Owner Import (Company)'
                )
        return owner
    
    def test_1000_owner_import(self):
        if self.do_owner:
            print('test_1000_owner_import')
            owner_vals = {
                'external_owner_id': 'unit-test-' + self.id_ext,
                'owner_code': 'UTEST' + self.id_ext,
                'firm_id': 'BL',
                'name': 'Unit Test Pervezimas',
                'ref': '84561234',
                'vat': 'LT7896541236',
                'waybilldeclaredatefrom': '2016-12-10',
                'waybilldeclare': 'Y',
                'active': 'Y',
                "regaddress": "V. Krėvės pr. 97, Kaunas",
                "phone": "+37062042407",
            }
            owner = self.create_owner(owner_vals)
            self.owner = owner

            owner_vals = {
                'external_owner_id': 'unit-test-2-' + self.id_ext,
                'owner_code': 'UTEST2' + self.id_ext,
                'firm_id': 'BL',
                'name': 'Unit Test Savininkas',
                'ref': '7441855296',
                'vat': 'LT744874487',
                'waybilldeclaredatefrom': '2016-12-10',
                'waybilldeclare': 'Y',
                'active': 'Y',
                "regaddress": "V. Gasiūno pr. 97, Vilnius",
                "phone": "+37062096207",
            }
            owner = self.create_owner(owner_vals)
            self.owner = owner
                