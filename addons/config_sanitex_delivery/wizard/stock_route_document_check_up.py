# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError
# from ..stock import utc_str_to_local_str
#
# import time

class StockRouteDocumentCheckUp(models.TransientModel):
    _name = 'stock.route.document.check_up.osv'
    _description = 'Wizard tu check if all documents are in route'

    document_number = fields.Char('Document Number', size=128)
    route_id = fields.Many2one('stock.route', 'Parent Route', readonly=True)
    checked_invoice_ids = fields.Many2many(
        'account.invoice', 'invoice_check_osv_checked_rel',
        'osv_id', 'invoice_id', 'Checked Documents', readonly=True
    )
    collect_package_invoice_ids = fields.Many2many(
        'account.invoice', 'invoice_check_osv_colect_package_rel', 'osv_id',
        'invoice_id', 'Collect Package Documents', readonly=True
    )
    electronic_invoice_ids = fields.Many2many(
        'account.invoice', 'invoice_check_osv_electronic_rel', 'osv_id',
        'invoice_id', 'Electronic Documents', readonly=True
    )
    not_checked_invoice_ids = fields.Many2many(
        'account.invoice', 'invoice_check_osv_not_checked_rel', 'osv_id',
        'invoice_id', 'Not Checked Documents', readonly=True
    )
    checked_invoice_count = fields.Integer('Checked Invoice Count', readonly=True)
    not_checked_invoice_count = fields.Integer('Not Checked Invoice Count', readonly=True)
    electronic_invoice_count = fields.Integer('Electronic Invoice Count', readonly=True)
    collect_package_invoice_count = fields.Integer('Collection Invoice Count', readonly=True)
    all_document_count = fields.Integer('All Document Count', readonly=True)
    log = fields.Text('Log', readonly=True)

    @api.multi
    def reset(self):
        self.route_id.reset_document_scanning()
        return self.route_id.action_run_document_check_up()

    @api.multi
    def load(self):
        if self.route_id.fully_checked:
            inv_data = self.route_id.get_related_document_data_for_check_up()
            checked_invoice_ids = []
            electronic_invoice_ids = []
            collect_package_invoice_ids = []
            all_document_count = 0
            for inv in inv_data:
                for document_no in inv[1].split(','):
                    if inv[3] and inv[3] == 'collection':
                        collect_package_invoice_ids.append(inv[0])
                    elif inv[2] and inv[2] == 'electronical':
                        electronic_invoice_ids.append(inv[0])
                    else:
                        checked_invoice_ids.append(inv[0])
                    all_document_count += 1
            self.write({
                'checked_invoice_ids': [(6, 0, checked_invoice_ids)],
                'checked_invoice_count': len(checked_invoice_ids),
                'not_checked_invoice_count': 0,
                'electronic_invoice_ids': [(6, 0, electronic_invoice_ids)],
                'electronic_invoice_count': len(electronic_invoice_ids),
                'collect_package_invoice_ids': [(6, 0, collect_package_invoice_ids)],
                'collect_package_invoice_count': len(collect_package_invoice_ids),
                'all_document_count': all_document_count
            })

        else:
            select_info_sql = '''
                SELECT
                    invoice_id,
                    scanned,
                    invoice_type
                FROM
                    stock_route_document_scanning
                WHERE
                    route_id = %s
            '''
            select_info_where = (self.route_id.id,)
            self.env.cr.execute(select_info_sql, select_info_where)
            lines_info = self.env.cr.fetchall()
            checked_invoice_ids = []
            not_checked_invoice_ids = []
            electronic_invoice_ids = []
            collect_package_invoice_ids = []
            all_document_count = len(lines_info)
            for line_info in lines_info:
                if line_info[1]:
                    checked_invoice_ids.append(line_info[0])
                elif line_info[2] == 'collection_package':
                    collect_package_invoice_ids.append(line_info[0])
                elif line_info[2] == 'digital_doc':
                    electronic_invoice_ids.append(line_info[0])
                else:
                    not_checked_invoice_ids.append(line_info[0])
            self.write({
                'checked_invoice_ids': [(6, 0, checked_invoice_ids)],
                'checked_invoice_count': len(checked_invoice_ids),
                'not_checked_invoice_ids': [(6, 0, not_checked_invoice_ids)],
                'not_checked_invoice_count': len(not_checked_invoice_ids),
                'electronic_invoice_ids': [(6, 0, electronic_invoice_ids)],
                'electronic_invoice_count': len(electronic_invoice_ids),
                'collect_package_invoice_ids': [(6, 0, collect_package_invoice_ids)],
                'collect_package_invoice_count': len(collect_package_invoice_ids),
                'all_document_count': all_document_count
            })
            self.route_id.update_cheched_document_info(len(not_checked_invoice_ids))

    @api.multi
    def check(self):
        if self.document_number and not self.route_id.fully_checked:

            select_info_sql = '''
                SELECT
                    id
                FROM
                    stock_route_document_scanning
                WHERE
                    route_id = %s
                    AND name = %s
            '''
            select_info_where = (self.route_id.id, self.document_number)
            self.env.cr.execute(select_info_sql, select_info_where)
            lines_info = self.env.cr.fetchall()
            if not lines_info:
                select_info_sql = '''
                    SELECT
                        id
                    FROM
                        stock_route_document_scanning
                    WHERE
                        route_id = %s
                        AND name ILIKE %s
                '''
                select_info_where = (self.route_id.id, self.document_number)
                self.env.cr.execute(select_info_sql, select_info_where)
                lines_info = self.env.cr.fetchall()
            if not lines_info:
                raise UserError(_('No document \'%s\' in route \'%s\'') %(self.document_number, self.route_id.name))
            else:
                update_sql = '''
                    UPDATE
                        stock_route_document_scanning
                    SET
                        scanned = True
                    WHERE
                        id = %s
                '''
                update_where = (lines_info[0][0],)
                self.env.cr.execute(update_sql, update_where)
            self.write({'document_number': ''})
            self.load()
        else:
            self.write({'document_number': ''})

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.route.document.check_up.osv',
            'target': 'new',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'context': self.env.context or {},
            'nodestroy': True,
        }