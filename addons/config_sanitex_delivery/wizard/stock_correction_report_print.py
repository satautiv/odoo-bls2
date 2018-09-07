# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api

class StockCorrectionPrintReport(models.TransientModel):
    _name = 'stock.correction.print_report.osv'
    _description = 'Print Correction Report for Route' 

    @api.model
    def _get_correction(self):
        context = self.env.context or {}
        return context.get('active_ids', [False])[0]

    @api.model
    def _get_report(self):
        # context = self.env.context or {}
        correction_env = self.env['stock.packing.correction']
        correction = correction_env.browse(self._get_correction())
        if correction.reason == 'tare_return':
            return 'config_sanitex_delivery.driver_return_act'
        else:
            return 'config_sanitex_delivery.tare_to_driver_act'
        # return context.get('report_to_print', False)

    @api.model
    def _get_printer(self):
        usr_obj = self.env['res.users']
        return usr_obj.browse(self.env.uid).get_default_printer()

    @api.model
    def _get_reprint(self):
        context = self.env.context or {}
        rep_log = self.env['report.print.log']
        corrections = self.env['stock.packing.correction'].browse(context.get('active_ids', []))
        printed_ids = corrections.mapped('picking_to_warehouse_ids').mapped('id') \
            + corrections.mapped('picking_to_driver_ids').mapped('id')
        return rep_log.already_printed('stock.picking', self._get_report(), printed_ids)

    @api.model
    def _get_all_reports(self):
        rep_obj = self.env['ir.actions.report']
        reports = rep_obj.search([
            ('keep_log','=',True)
        ])
        res = []
        for report in reports:
            rep = report.read(['name', 'report_name'])[0]
            res.append((rep['report_name'], rep['name']))
        return res
    
    @api.model
    def _get_number_of_copies(self):
        report_name = self._get_report()
        if not report_name:
            return 1
        user_env = self.env['res.users']
        number_of_copies_env = self.env['number.of.copies']
        
        user = user_env.browse(self._uid)
        if user.default_warehouse_id:
            current_warehouse = user.default_warehouse_id
        elif user.default_region_id and user.default_region_id.location_id:
            current_location = user.default_region_id.location_id
            current_warehouse = current_location.get_location_warehouse_id()
        else:
            current_warehouse = False
        
        domain_part = [('report_id.report_name','=',report_name)]
        if current_warehouse:
            number_of_copies_rec = number_of_copies_env.search(
                domain_part+[('warehouse_ids','in',current_warehouse.id)],
                limit=1
            )
            if number_of_copies_rec:
                return number_of_copies_rec.number_of_copies
        
        number_of_copies_rec = number_of_copies_env.search(
            domain_part+[('warehouse_ids','=',False)], limit=1
        )
        if number_of_copies_rec:
            return number_of_copies_rec.number_of_copies
        return 1
        

    report = fields.Selection(_get_all_reports, 'Report', required=True, default=_get_report)
    parent_correction_id = fields.Many2one(
        'stock.packing.correction', 'Correction', readonly=True, default=_get_correction
    )
    reprint = fields.Boolean('Reprinting', default=_get_reprint)
    printer_id = fields.Many2one('printer', 'Printer', required=True, default=_get_printer, ondelete='cascade')
    reprint_reason = fields.Char('Reason for Reprinting', size=512)
    number_of_copies = fields.Integer("Number of Copies", required=True, default=_get_number_of_copies)
    confirmation = fields.Boolean('Confirmation', default=lambda self: (self.env.context or {}).get('for_confirmation', False))

    @api.multi
    def print_report(self):
        context = self.env.context or {}
        corr_env = self.env['stock.packing.correction']
        rep_obj = self.env['ir.actions.report']
        report = rep_obj.search([
            ('report_name','=',self.report)
        ])
        corrections = corr_env.browse(context['active_ids'])
        records = corrections.mapped('picking_to_driver_ids') + corrections.mapped('picking_to_warehouse_ids')
        report.print_report(records, printer=self.printer_id, reprint_reason=self.reprint_reason, copies=self.number_of_copies)
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def confirm(self):
        context = self.env.context or {}
        if self.parent_correction_id:
            self.parent_correction_id.action_done()
            if not context.get('will_be_printed', False):
                self.parent_correction_id.do_not_print_reports(self.report)

    @api.multi
    def print_report_and_confirm(self):
        self.with_context(will_be_printed=True).confirm()
        self.print_report()