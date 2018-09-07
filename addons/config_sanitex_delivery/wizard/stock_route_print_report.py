# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockRoutePrintReport(models.TransientModel):
    _name = 'stock.route.print_report.osv'
    _description = 'Print Packing Report for Route' 

    @api.model
    def _get_route(self):
        context = self.env.context or {}
        return context.get('active_ids', [False])[0]

    @api.model
    def _get_report(self):
        context = self.env.context or {}
        return context.get('report_to_print', False)

    @api.model
    def _get_printer(self):
        usr_obj = self.env['res.users']
        return usr_obj.browse(self.env.uid).get_default_printer()

    @api.model
    def _get_reprint(self):
        rep_log = self.env['report.print.log']
        context = self.env.context or {}
        report_name = self._get_report()
        model = 'stock.route'
        ids = context.get('active_ids', [])
        routes = self.env['stock.route'].browse(ids)
        if report_name == 'config_sanitex_delivery.packing_return_act':
            model = 'stock.picking'
            ids = routes.mapped('returned_picking_ids').mapped('id')
        if report_name == 'config_sanitex_delivery.drivers_packing_transfer_act':
            model = 'stock.picking'
            ids = routes.mapped('picking_ids').mapped('id')
        already = rep_log.already_printed(model, report_name, ids)
        # if not already and self._get_report() == 'config_sanitex_delivery.product_packing':
        #     already = rep_log.already_printed('stock.route',
        #         'config_sanitex_delivery.drivers_packing_transfer_act', context.get('active_ids', [])
        #     )
        return already

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
    parent_route_id = fields.Many2one(
        'stock.route', 'Route', readonly=True, default=_get_route
    )
    reprint = fields.Boolean('Reprinting', default=_get_reprint)
    printer_id = fields.Many2one('printer', 'Printer', default=_get_printer)
    reprint_reason = fields.Char('Reason for Reprinting', size=512)
    file = fields.Binary('File')
    number_of_copies = fields.Integer("Number of Copies", required=True, default=_get_number_of_copies)

    @api.multi
    def print_report(self):
        if self.report == 'config_sanitex_delivery.packing_return_act'\
         and not self.parent_route_id.returned_picking_ids:
            raise UserError(_('There is nothing to print. There are not any returns from driver.'))
        elif self.report == 'config_sanitex_delivery.drivers_packing_transfer_act'\
         and not self.parent_route_id.picking_ids:
            raise UserError(_('Route does not have any tare assigned.'))
        self.parent_route_id.with_context(show_printing_error=True).print_report(
            self.report, printer=self.printer_id, reprint_reason=self.reprint_reason,
            copies=self.number_of_copies
        )
        # if self.report == 'config_sanitex_delivery.product_packing':
        #     # akto spausdinimas kai spausdinamas draivas
        #     self.parent_route_id.with_context(show_printing_error=False).print_report(
        #         'config_sanitex_delivery.drivers_packing_transfer_act', printer=self.printer_id,
        #         reprint_reason=self.reprint_reason, copies=self.number_of_copies
        #     )

        return {'type': 'ir.actions.act_window_close'}