# -*- coding: utf-8 -*-

import time
from odoo import api, models, _


class ReportStockCorrection(models.AbstractModel):
    _name = 'report.config_sanitex_delivery.report_stock_correction'


    @api.model
    def _get_info(self, ids, data):
        res = {}
        corr_env = self.env['stock.packing.correction']
        company = self.env['res.users'].browse(self.env.uid).company_id
        corrections = corr_env.browse(ids)
        reason = {
            'tare_return': _('Tare Return'),
            'transfer_to_driver': _('Transfer to Driver')
        }
        for correction in corrections:
            receiver = ''
            receiver += 'UAB "SANITEX"' + '\n'
            receiver += reason[correction.reason] + '\n'
            receiver += _('Comp. Code:') + ' ' + (
                company.company_registry  or '') + '\n'
            receiver += _('VAT Code:') + ' ' + (
                company.vat or '') + '\n'

            receiver += _('Tel.:') + ' ' + (company.phone or '') \
                + '  ' + _('Fax:') + ' ' + (company.fax or '') + '\n'

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

            info = {
                'receiver': receiver,
                'sender': sender,
                'number': 'ni'
            }
            res[correction.id] = info
        return res

    @api.model
    def get_report_values(self, docids, data=None):
        corr_env = self.env['stock.packing.correction']
        print_log_env = self.env['report.print.log']
        corrections_to_print = corr_env.browse([])
        corrections_to_print = []
        for doc_id in docids:
            correction = corr_env.browse(doc_id)
            owners = correction.get_document_owners()
            for owner in owners:
                new_correction_browse = corr_env.with_context(owner_to_print=owner.id).browse(correction.id)
                if new_correction_browse.line_ids:
                    corrections_to_print.append(new_correction_browse)

        duplicate = print_log_env.already_printed(
            'stock.packing.correction', 'config_sanitex_delivery.report_stock_correction', docids
        )

        return {
            'doc_ids': docids,
            'doc_model': corr_env,
            'docs': corrections_to_print,
            'time': time,
            'duplicate': duplicate,
            'data': data,
            # 'receiver': _get_receiver,
            'get_info': self._get_info(docids, data),
        }