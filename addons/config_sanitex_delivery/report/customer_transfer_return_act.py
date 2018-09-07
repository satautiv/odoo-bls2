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
        self.localcontext.update({
            'get_objects': self._get_objects,
            'get_loading_place': self._get_loading_place,
            'get_unloading_place': self._get_unloading_place,
            'get_lines': self._get_lines,
            'duplicate': self._duplicate,
            'get_number': self._get_name,
            'context': context
        })
    
    def _get_name(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_name_for_customer_transfer_return(
            cr, uid, packing, context=context
        )
    
    def _duplicate(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        if rep_obj.check_if_dublicate(
            cr, uid, 'config_sanitex_delivery.customer_transfer_return_act',
            'stock.packing', packing.id, context=context
        ):
            return _('(Duplicate)')
        return ''
    
    def _get_objects(self, data=None):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        objects = self.localcontext['objects']
        return rep_obj.get_objects_for_customer_transfer_return(
            cr, uid, objects, data, context=context
        )
    
    def _get_loading_place(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_loading_place_for_customer_transfer_return(
            cr, uid, packing, context=context
        )
        
    def _get_unloading_place(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_unloading_place_for_customer_transfer_return(
            cr, uid, packing, context=context
        )
        
    def _get_lines(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_lines_for_customer_transfer_return(
            cr, uid, packing, context=context
        )