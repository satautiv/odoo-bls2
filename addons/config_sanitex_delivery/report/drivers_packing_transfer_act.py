# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from openerp.report import report_sxw
from openerp.tools.translate import _

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self._total = {}
        self.localcontext.update({
            'context': context,
            'get_objects': self._get_objects,
            'get_current_time': self._get_current_time,
            'get_record_name': self._get_record_name,
            'get_receiver': self._get_receiver,
            'get_company_address': self._get_company_address,
            'get_lines': self._get_lines,
            'get_total': self._get_total,
            'get_lines_to_return': self._get_lines_to_return,
            'get_to_return': self._get_to_return,
            'duplicate': self._duplicate
        })
        
    def _duplicate(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        if rep_obj.check_if_dublicate(
            cr, uid, 'config_sanitex_delivery.drivers_packing_transfer_act',
            'stock.route', route.id, context=context
        ):
            return _('(Duplicate)')
        return ''
    
    def _get_to_return(self, route):
        if self._get_lines_to_return(route):
            return True
        return False
    
    def _get_objects(self):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        objects = self.localcontext['objects']
        return rep_obj.get_objects_for_driver_packing_transfer(
            cr, uid, objects, context=context
        )
    
    def _get_current_time(self):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_current_time_for_driver_packing_transfer(
            cr, uid, context=context
        )
    
    def _get_record_name(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_record_name_for_driver_packing_transfer(
            cr, uid, route, context=context
        )
    
    def _get_receiver(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_receiver_for_driver_packing_transfer(
            cr, uid, route, context=context
        )
    
    def _get_company_address(self, company):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_company_address_for_driver_packing_transfer(
            cr, uid, company, context=context
        )
    
    def _get_lines(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        totals = self._total
        res = rep_obj.get_lines_for_driver_packing_transfer(
            cr, uid, route, totals, context=context
        )
        self._total = totals
        return res
    
    def _get_total(self, route):
        return self._total
    
    def _get_lines_to_return(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_lines_to_return_for_driver_packing_transfer(
            cr, uid, route, context=context
        )