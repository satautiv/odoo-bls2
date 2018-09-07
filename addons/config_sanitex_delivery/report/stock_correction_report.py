# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from openerp.report import report_sxw
from openerp.tools.translate import _

import time

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self._total = {}
        self.localcontext.update({
            'context': context,
            'get_objects': self._get_objects,
            'get_current_datetime': self._get_current_datetime,
            'duplicate': self._duplicate,
            'get_name': self._get_name,
            'get_record_no': self._get_record_no,
            'get_sender': self._get_sender,
            'get_receiver': self._get_receiver,
            'get_lines': self._get_lines,
            'get_total': self._get_total,
            'get_user': self._get_user,
        })
        
    def _get_objects(self):
        report_obj = self.env('ir.actions.report.xml')
#         log_obj = self.env('report.print.log')
        
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        x = 1
        
        report_ids = report_obj.search(cr, uid, [
            ('report_name','=','config_sanitex_delivery.stock_correction_report')
        ], context=context)
        if report_ids:
            report = report_obj.browse(cr, uid, report_ids[0], context=context)
            if report.copy_number > 1:
                x = report.copy_number
        objects = []
        for copy in range(x):
            for obj in self.localcontext['objects']:
                objects.append(obj)
                self._total[obj.id] = {
                    'price_wo_vat': 0.0,
                    'price_w_vat': 0.0,
                    'big': 0.0,
                    'small': 0.0,
                    'uom': 0,
                    'total': 0,
                    'sum_wo_vat': 0.0,
                    'vat': 0.0,
                    'products': 0.0,
                    'sum': 0.0,
                }
        return objects
    
    def _get_current_datetime(self):
        return time.strftime('%Y-%m-%d/%H:%M')
    
      
    def _duplicate(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        if rep_obj.check_if_dublicate(
            cr, uid, 'config_sanitex_delivery.stock_correction_report',
            'stock.packing.correction', route.id, context=context
        ):
            return _('(Duplicate)')
        return ''
    
    def _get_name(self, correction):
        return correction.number
    
    def _get_record_no(self, correction):
        return ''
    
    def _get_sender(self, correction, company, data, check=True):
#         if data['form'].get('type','') == 'shortage' and check:
#             return self._get_receiver(correction, company, data, check=False)
        sender = ''
        sender += 'UAB "SANITEX"' + '\n'
        sender += (correction.return_to_warehouse_id.code or '') + ', ' + (correction.return_to_warehouse_id.name or '') + '\n'
        sender += _('VAT Code:') + ' ' + (
            correction.return_to_warehouse_id.partner_id and \
            correction.return_to_warehouse_id.partner_id.vat or \
        '') + '\n'
        
        sender += _('Tel.:') + ' ' + (
            correction.return_to_warehouse_id.partner_id and \
            correction.return_to_warehouse_id.partner_id.phone or \
        '') + '  ' + _('Fax:') + ' ' + (
            correction.return_to_warehouse_id.partner_id and \
            correction.return_to_warehouse_id.partner_id.fax or \
        '') + '\n'
        sender += _('Unload place:')
        
        return sender
    
    def _get_receiver(self, correction, company, data, check=True):
#         if data['form'].get('type','') == 'shortage' and check:
#             return self._get_sender(correction, company, data, check=False)
        reason = {
            'operator_mistake': _('Operators Mistake'),
            'driver_shortage': _('Drivers Shortage')
        }
        receiver = ''
        receiver += 'UAB "SANITEX"' + '\n'
        receiver += reason[correction.reason] + '\n'
        receiver += _('Comp. Code:') + ' ' + (
            company.company_registry  or '') + '\n'
        receiver += _('VAT Code:') + ' ' + (
            company.vat or '') + '\n'
        
        receiver += _('Tel.:') + ' ' + (company.phone or '') \
            + '  ' + _('Fax:') + ' ' + (company.fax or '') + '\n'
        
        return receiver
    
    def _get_lines(self, correction, data):
        sign = 1.0
#         if data['form'].get('type','') == 'excess':
#             sign = -1.0
        lines = []
        no_total = False
        if sum(self._total[correction.id].values()) > 0:
            no_total = True
        
        for line in correction.line_ids:
            if line.correction_qty == 0.0:
                continue
            vals = {}
            vals['code'] = line.product_id.default_code or ''
            vals['name'] = line.product_id.name or ''
            vals['price_wo_vat'] = line.product_id.standard_price or 0.0
            vals['price_w_vat'] = round(vals['price_wo_vat'] * 1.21, 2)
            vals['big'] = 0.0
            vals['small'] = 0.0
            vals['uom'] = int(sign*(line.correction_qty or 0.0)) #line.product_id.uom_id and line.product_id.uom_id.name or ''
            vals['total'] = vals['uom']
            vals['sum_wo_vat'] = vals['total'] * vals['price_wo_vat']
            lines.append(vals)
            
            if not no_total:
                self._total[correction.id]['price_wo_vat'] += vals['price_wo_vat']
                self._total[correction.id]['price_w_vat'] += vals['price_w_vat']
                self._total[correction.id]['big'] += vals['big']
                self._total[correction.id]['small'] += vals['small']
                self._total[correction.id]['uom'] += int(sign*vals['uom'])
                self._total[correction.id]['total'] += int(sign*vals['total'])
                self._total[correction.id]['sum_wo_vat'] += vals['sum_wo_vat']
                self._total[correction.id]['vat'] = round(self._total[correction.id]['price_wo_vat'] * 0.21)
                self._total[correction.id]['sum'] = self._total[correction.id]['price_wo_vat'] + self._total[correction.id]['vat']
                
        for key in self._total[correction.id]:
            if self._total[correction.id][key] != 0.0:
                self._total[correction.id][key] = self._total[correction.id][key]*sign
        return lines
    
    
    def _get_total(self, correction):
        return self._total[correction.id]
    
    def _get_user(self, user):
        return user.name