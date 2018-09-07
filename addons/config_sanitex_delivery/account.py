# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

import datetime
import json
import logging
import requests
import threading
import time
import traceback
import re

from odoo import models, fields, _, api
from odoo import tools
import odoo.addons.decimal_precision as dp
from odoo.api import Environment
from odoo.exceptions import UserError

from .stock import str_date_to_timestamp, get_local_time_timestamp, utc_str_to_local_str


_logger = logging.getLogger(__name__)
hours_re = re.compile("[0-9]{2}:[0-9]{2}$")

INVOICE_LINE_VERSION_FIELD = {
    'product_id', 'external_invoice_line_id', 'id', 'quantity', 'invoice_id'
}

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    _order='date_invoice desc, id desc'

    @api.model
    def _get_invoice_states(self):
        return [
            ('draft',_('Active')),
            # ('proforma', 'Pro-forma'),
            # ('proforma2', 'Pro-forma'),
            # ('open', 'Open'),
            # ('paid', 'Paid'),
            ('cancel', _('Cancelled')),
        ]
    
    @api.model
    def _get_default_warehouse(self):
        user_obj = self.env['res.users']
        user = user_obj.browse(self.env.uid)
        return user.get_default_warehouse()

    @api.model
    def _get_default_category(self):
        context = self.env.context or {}
        return context.get('category', 'invoice')
  
#     @api.model
#     def _get_default_taxes(self):
#         context = self._context
#         res=[(5,)]
#         if context.get('receive_invoice', False):
#             AccountInvoiceTax = self.env['account.invoice.tax']
#             fields_list = AccountInvoiceTax._defaults.keys()
#             vals = AccountInvoiceTax.default_get(fields_list)
#             company = self.env['res.company'].search([], limit=1)
#             if company:
#                 for receive_tax_id in company.receive_tax_ids:
#                     vals['tax_id'] = receive_tax_id.id
#                     tpl_val = (0, 0, vals)
#                     res.append(tpl_val)    
#         return res
    
    def cron_delete_old_invoices(self):
        # Klausimai:
        # Pagal kuria data
        # Kokios busenos
        # ar galima trinti kai turi susijusiu uzduociu arba siuntu
        

        user = self.env['res.users'].browse(self.env.uid)
        company = user.company_id
        days_after = company.delete_invoices_after
        _logger.info('Removing old Invoices (%s days old)' % str(days_after))

        today = datetime.datetime.now()
        date_intil = today - datetime.timedelta(days=days_after)
        invoices = self.search([
            ('date','<',date_intil.strftime('%Y-%m-%d %H:%M:%S')),
            ('state','=','closed')
        ])
        _logger.info('Removing old Invoices: found %s records' % str(len(invoices)))
        for invoice in invoices:
            if not invoice.exists():
                continue
            if invoice.can_delete():
                invoice.unlink()
                self.env.cr.commit()

    @api.one
    @api.depends('invoice_line_ids.price_subtotal','doc_discount')
    def _compute_total_discount(self):
        total_discount = 0.0
        if self.doc_discount:
            for line in self.invoice_line_ids:
                total_discount += line.discount_amount
                
        self.discount_amount = total_discount
    
    @api.model
    def _get_invoice_categories(self):
        return self._get_document_operation_types()
#         [
#             ('invoice', _("Invoice")),
#             ('waybill', _("Waybill")),
# #             ('picking', _("Transportation")),
# #             ('package', _("Package")),
# #             ('packaging_sheet', _("Packaging Sheet")),
# #             ('additional_invoice', _("Additional Invoice")),
#         ]
##-------------------------- KAZKODEL BUVO UZKLOTA, BET NEBEISEINA ATSEKTI KODEL---------------------------        
#     @api.multi
#     def get_taxes_values(self):
#         tax_grouped = {}
#         for line in self.invoice_line_ids:
#             price_unit = line.price_unit * (1 - (line.discount + self.doc_discount) / 100.0)
#             taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['taxes']
#             for tax in taxes:
#                 val = {
#                     'invoice_id': self.id,
#                     'name': tax['name'],
#                     'tax_id': tax['id'],
#                     'amount': tax['amount'],
#                     'manual': False,
#                     'sequence': tax['sequence'],
#                     'account_analytic_id': tax['analytic'] and line.account_analytic_id.id or False,
#                     'account_id': self.type in ('out_invoice', 'in_invoice') and (tax['account_id'] or line.account_id.id) or (tax['refund_account_id'] or line.account_id.id),
#                 }
# 
#                 # If the taxes generate moves on the same financial account as the invoice line,
#                 # propagate the analytic account from the invoice line to the tax line.
#                 # This is necessary in situations were (part of) the taxes cannot be reclaimed,
#                 # to ensure the tax move is allocated to the proper analytic account.
#                 if not val.get('account_analytic_id') and line.account_analytic_id and val['account_id'] == line.account_id.id:
#                     val['account_analytic_id'] = line.account_analytic_id.id
# 
#                 key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)
# 
#                 if key not in tax_grouped:
#                     tax_grouped[key] = val
#                 else:
#                     tax_grouped[key]['amount'] += val['amount']
#         return tax_grouped

    @api.model
    def _get_default_account(self):
        return self.env['res.company'].get_default_account().id

    @api.multi
    def get_related_tasks(self):
        # Metodas grąžina susijusias užduotis

        tasks = self.env['sale.order']
        for invoice in self:
            tasks |= invoice.sale_order_line_ids.mapped('order_id')
        return tasks

    @api.multi
    def action_open_related_tasks(self):
        tasks = self.get_related_tasks()
        form_view = self.env.ref('config_sanitex_delivery.view_sale_order_route_bls_form', False)[0]
        tree_view = self.env.ref('config_sanitex_delivery.view_sale_order_no_create_button_tree', False)[0]
        context = self.env.context or {}
        ctx = context.copy()
        ctx['search_by_user_sale'] = False
        ctx['search_for_template_view'] = False
        res = {
                'name': _('Transportation Tasks'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'sale.order',
                'views': [(tree_view.id,'tree'),(form_view.id,'form')],
                'type': 'ir.actions.act_window',
                'context': ctx,
                'domain': [
                    ('id','in',list(tasks._ids)),
                ]
            }
        return res

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 'company_id')
    def _compute_amount(self):
        if self.invoice_line_ids:
            self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
            self.amount_tax = sum(line.amount for line in self.tax_line_ids)
            self.amount_total = self.amount_untaxed + self.amount_tax
            amount_total_company_signed = self.amount_total
            amount_untaxed_signed = self.amount_untaxed
            if self.currency_id and self.currency_id != self.company_id.currency_id:
                amount_total_company_signed = self.currency_id.compute(self.amount_total, self.company_id.currency_id)
                amount_untaxed_signed = self.currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
            sign = (self.type in ['in_refund', 'out_refund'] or self.annul_document) and -1 or 1
            self.amount_total_company_signed = amount_total_company_signed * sign
            self.amount_total_signed = self.amount_total * sign
            self.amount_untaxed_signed = amount_untaxed_signed * sign
        else:
            total_amount = self.move_ids.get_total_sum()
            self.amount_untaxed = total_amount
            self.amount_tax = 0.0
            self.amount_total = total_amount
            self.amount_total_company_signed = total_amount
            self.amount_total_signed = total_amount
            self.amount_untaxed_signed = total_amount


    @api.model
    def _get_document_operation_types(self):
        return [
            ('invoice',_('Invoice')),
            ('waybill',_('Waybill')),
            ('cmr',_('CMR')),
            ('wh2dr',_('Warehouse --> Driver')),
            ('dr2cl',_('Driver --> Client')),
            ('cl2dr',_('Client --> Driver')),
            ('dr2wh',_('Driver --> Warehouse')),
            ('dr2dr',_('Driver --> Driver')),
            ('wh2wh',_('Warehouse --> Warehouse')),
            ('cl2cl',_('Client --> Client')),
            ('wh2cl',_('Warehouse --> Client')),
            ('cl2wh',_('Client --> Warehouse')),
            ('adj2wh','Adjustment --> Warehouse'),
            ('wh2adj','Warehouse --> Adjustment'),
        ]
        
    @api.model
    def get_sending_type_selection(self):
        return [
            ('electronical', "EDI"),
            ('paper', _("Paper")),
            ('paper_edi', _("Paper & EDI")),
            ('none', _("None"))
        ]

    @api.model
    def _get_all_operation_types(self):
        return self.env['internal.operation']._get_all_operation_types()

    external_invoice_id = fields.Char('External ID', size=64, readonly=True)
    intermediate_id = fields.Many2one(
        'stock.route.integration.intermediate', 'Created by', readobly=True
    )
    sale_order_line_ids = fields.Many2many(
        'sale.order.line', 'invoice_so_line_rel', 'invoice_id',
        'order_line_id', 'Sale Order Lines'
    )
    partner_shipping_id = fields.Many2one('res.partner', 'Shipping Address')
    partner_invoice_id = fields.Many2one('res.partner', 'Invoice Address')
    primary_invoice_id = fields.Many2one('account.invoice',
        'Primary Invoice', readonly=True, index=True
    )
    cash_amount = fields.Float('Cash Amount', digts=(16, 2))
    picking_warehouse_id = fields.Many2one('stock.warehouse', 'Picking Warehouse', default=_get_default_warehouse)
    picking_location_id = fields.Many2one('stock.location', 'Picking Location')
    automatically_created_sale_id = fields.Many2one('sale.order', 'Automatically Created Sale')
    intermediate_for_ivaz_id = fields.Many2one(
        'stock.route.integration.intermediate', 'IVAZ export', readobly=True
    )
    owner_id = fields.Many2one('product.owner', 'Owner')
    state = fields.Selection(_get_invoice_states, string='Status', readonly=True, default='draft')
    
    container_ids = fields.Many2many(
        'account.invoice.container', 'container_invoice_rel',
        'invoice_id', 'container_id', "Containers"
    )
    can_be_deleted = fields.Boolean('Can be deleted', readonly=True, default=True)
    certificate_id = fields.Many2one('product.certificate', "Certificate")
    doc_discount = fields.Float("Document Discount %", digits=(3, 2))
    category = fields.Selection(_get_invoice_categories, "Category", default=_get_default_category)
    return_type = fields.Selection([
        ('credit', _("Credit")),
        ('debit', _("Debit"))
    ], "Return Type", default='credit')
    daa_no = fields.Char("Accompanying Administrative Document (DAA)", size=64)
    supplier_code = fields.Char("Supplier Code", readonly=True)
    source_location_id = fields.Many2one('stock.location', "Product Source Location")
    related_sale_id = fields.Many2one('sale.order', "Related Selection Sheet")
    discount_amount = fields.Float(
        "Total Discount Amount", store=True,
        compute='_compute_total_discount'
    )
    gate_id = fields.Many2one('stock.gate', string="Gate")
    refund_type = fields.Selection([
        ('credit', "Credit"),
        ('debit', "Debit"),
    ], string="Return Type")
    annul_document = fields.Boolean("Annul Document", default=False)
#     payment_term_days = fields.Integer("Payment Term Days")
    ivaz_declared_from_transportation = fields.Boolean("i.VAZ Declared From Transportation Order", default=False)
    total_weight = fields.Float('Total Weight', digits=dp.get_precision('Stock Weight'), readonly=True)
    account_id = fields.Many2one(default=_get_default_account)
    document_id_for_ivaz = fields.Char('ID For Sending To IVAZ', size=64, readonly=True)
    posid = fields.Char("POSID", size=64, readonly=True)
    order_number = fields.Char("Order No.", size=64, readonly=True)
    partner_order_number = fields.Char("Partner Order No.", size=64, readonly=True)
    id_version = fields.Char('POD Version', size=128, readonly=True)
    nkro_number = fields.Char('NKRO', readonly=True, size=64)
    nsad_number = fields.Char('NSAD', readonly=True, size=64)
    import_timestamp = fields.Integer('Import Timestamp', readonly=True, help='Taken from import values', default=0)
    
    payment_term = fields.Char('Payment Term')
    payment_term_date = fields.Date('Payment Term')
    time_invoice = fields.Char('Time', size=8, readonly=True)
    partner_ref = fields.Char('Client Comp. Code', size=32, readonly=True)
    partner_name = fields.Char('Client Name', size=64, readonly=True)
    partner_address = fields.Char('Client Adrress', size=128, readonly=True)
    driver_name = fields.Char('Driver Name', size=64, readonly=True, track_visibility='onchange')
    line_count = fields.Integer('Line Count', readonly=True)
    route_number = fields.Char('Route Number', size=64, readonly=True, track_visibility='onchange')
    route_template_number = fields.Char('Route Template Number', size=64, readonly=True)
    move_ids = fields.One2many('stock.move', 'invoice_id', 'Moves', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', change_default=True,
        required=False, readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='always')
    document_operation_type = fields.Selection(_get_document_operation_types, 'Document Type', readonly=True)
    all_document_numbers = fields.Char('All Numbers', size=64, readonly=True)
    warehouse_at_id = fields.Many2one('stock.warehouse', 'At Warehouse', readonly=True,
        help='Shows at whitch warehouse this document is at the moment.'
    )
    document_create_datetime = fields.Datetime('Create Date, Time', readonly=True)
    stock_package_id = fields.Many2one('stock.package', 'Related Package', readonly=True, index=True,
        help='If this field is filled in, that means this document was generated from this package.'
    )
    delivery_type = fields.Selection([
        ('delivery', 'Delivery'),
        ('collection', 'Collection')
    ], 'Delivery Type')
#     sending_type = fields.Char('Sending Type', size=32)
    sending_type = fields.Selection(get_sending_type_selection, "Sending Type", default='paper')
    destination_location_id = fields.Many2one('stock.location', 'Destination Status', readonly=True)
    operation_type = fields.Selection(_get_all_operation_types, 'Operation Type', readonly=True)

    # commercial_partner_id = fields.Integer('Commercial Entity')
    commercial_partner_id = fields.Many2one('res.partner', string='Commercial Entity',
        related=False, store=True, readonly=True,
        help="The commercial entity that will be used on Journal Entries for this invoice")


    _sql_constraints = [
        ('external_invoice_id', 'unique (external_invoice_id)', 'External ID of invoice has to be unique')
    ]


    @api.multi
    def action_scan(self):
        # Skenuojant dokumentus, kurie bus išvežti maršrutu arba sugrįžo iš maršruto
        # yra galimybė ne skenuoti kodą, bet paspaudus mygtuką dokumente,
        # jį pažymėti kaip nuskenuotą. Veikia tik tada kai
        # per kontekstą paduodamas wizardo id

        check_up_env = self.env['stock.route.document.check_up.osv']
        context = self.env.context or {}
        if context.get('check_up_osv_id', False):
            check_up_wizard = check_up_env.with_context(no_closed_edit=False).browse(context['check_up_osv_id'])
            for invoice in self:
                for document_name in invoice.all_document_numbers.split(','):
                    check_up_wizard.write({'document_number': document_name.strip()})
                    rezult = check_up_wizard.check()
            return rezult

    @api.multi
    def to_dict_for_rest_integration(self):
        context = self.env.context or {}
        invoice_dict = {
            'linenum': 1,
            'invoiceuniqueid': ''.join(self.external_invoice_id.split('-')[:-1]),
            'documentnum': self.name,
            'cashsum': self.cash_amount,
            'updated': str_date_to_timestamp(self.write_date, '%Y-%m-%d %H:%M:%S'),
            'weight': self.total_weight,
        }
        if context.get('rest_version', 1) > 1:
            invoice_dict.update({
                'orderExternalNo': self.name or '',
                'orderId': ''.join(self.external_invoice_id.split('-')[:-1]),
                'orderSum': self.cash_amount or 0,
                'cargoInfo': []
            })
            for line in self.invoice_line_ids:
                line_dict = line.invoice_line_to_dict_for_rest_integration()
                line_dict['carrierId'] = ''
                invoice_dict['cargoInfo'].append(line_dict)
        return invoice_dict

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.supplier_code = self.partner_id.supplier_code
        else:
            self.supplier_code = False
        super(AccountInvoice, self)._onchange_partner_id()
        
    @api.onchange('picking_location_id')
    def _onchange_location_id(self):
        if self.picking_location_id:
            self.gate_id = self.picking_location_id.gate_id\
             and self.picking_location_id.gate_id.id or False

    @api.multi
    def get_formview_id(self, access_uid=None):
        return False

    @api.multi
    def get_lines(self):
        if self:
            lines_sql = '''
                SELECT
                    id
                FROM
                    account_invoice_line
                WHERE
                    invoice_id in %s
            '''
            lines_where = (tuple(self.ids),)
            self.env.cr.execute(lines_sql, lines_where)
            return self.env['account.invoice.line'].browse([line_id[0] for line_id in self.env.cr.fetchall()])
        return self.env['account.invoice.line']

    @api.multi
    def print_document_from_invoice(self):
        picking_env = self.env['stock.picking']
        picking = picking_env.search([('invoice_id','=',self[0].id)])
        if not picking:
            raise UserError(_('There are no report to print for document %s.' % self[0].name))
        return picking.print_picking_from_route()

    @api.multi
    def _export_rows(self, fields):
        if self.env.user.company_id.user_faster_export:
            res = self.env['ir.model'].export_rows_with_psql(fields, self)
            if ['state'] in fields:
                res2 = []
                ind = fields.index(['state'])
                for line in res:
                    line_list = list(line)
                    if line_list[ind] == 'draft':
                        line_list[ind] = 'active'
                    res2.append(line_list)
                res = res2
        else:
            res = super(AccountInvoice, self)._export_rows(fields)
        return res

    @api.model_cr
    def init(self):
        cr = self.env.cr
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('account_invoice_related_sale_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX account_invoice_related_sale_id_index ON account_invoice (related_sale_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('account_invoice_automatically_created_sale_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX account_invoice_automatically_created_sale_id_index ON account_invoice (automatically_created_sale_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('account_invoice_external_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX account_invoice_external_id_index ON account_invoice (external_invoice_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('account_invoice_intermediate_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX account_invoice_intermediate_id_index ON account_invoice (intermediate_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('account_invoice_intermediate_for_ivaz_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX account_invoice_intermediate_for_ivaz_id_index ON account_invoice (intermediate_for_ivaz_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('account_invoice_refund_invoice_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX account_invoice_refund_invoice_id_index ON account_invoice (refund_invoice_id)')
        cr.execute("""
            SELECT 
                count(*) 
            FROM 
                information_schema.constraint_table_usage 
            WHERE 
                table_name = 'account_invoice'
                and constraint_name = 'account_invoice_number_uniq'
        """)
        res = cr.fetchone()
        if res[0] > 0:
            cr.execute("""
                ALTER TABLE 
                    account_invoice
                DROP CONSTRAINT 
                    account_invoice_number_uniq
            """)

    @api.model
    def get_search_domain(self, args):
        context = self._context or {}
        if context.get('search_invoices_by_warehouse', False):
            user = self.env.user
            available_wh_ids = user.get_current_warehouses().mapped('id')
            if ('picking_warehouse_id', 'in', available_wh_ids) not in args:
                args.append('|')
                args.append(('picking_warehouse_id', 'in', available_wh_ids))
                args.append(('warehouse_at_id', 'in', available_wh_ids))


    @api.model
    def _search(
            self, args, offset=0, limit=None,
            order=None, count=False,
            access_rights_uid=None
    ):
        self.get_search_domain(args)
        return super(AccountInvoice, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )

    @api.multi
    def action_cancel_bls(self):
        self.write({'state': 'cancel'})

    @api.model
    def create_invoice(self, vals):
        interm_obj = self.env['stock.route.integration.intermediate']
        context = self.env.context or {}

        commit = not context.get('no_commit', False)
        invoice = self.search([
            ('external_invoice_id','=',vals['external_invoice_id'])
        ], limit=1)
        if invoice:
            import_timestamp = invoice.read(['import_timestamp'])[0]['import_timestamp']
            if import_timestamp > vals['import_timestamp']:
                return invoice
        if invoice:
            invoice_vals = {}
            invoice_vals.update(vals)
            interm_obj.remove_same_values(invoice, invoice_vals)
            if invoice_vals:
                invoice_vals['intermediate_id'] = context.get('intermediate_id', False)
                invoice.write(invoice_vals)
                if 'updated_invoice_ids' in context:
                    context['updated_invoice_ids'].append((vals['external_invoice_id'], invoice.id))
                context['invoice_message'].append(_('Invoice was successfully updated'))
        else:
            invoice_vals = self.default_get(self._fields)
            invoice_vals['document_operation_type'] = 'invoice'
            invoice_vals.update(vals)
            if 'origin' not in invoice_vals.keys():
                vals['origin'] = 'import - ' + vals['external_invoice_id']
            invoice_vals['intermediate_id'] = context.get('intermediate_id', False)
            self.check_invoice_vals(invoice_vals)
            invoice = self.with_context(recompute=False).create(invoice_vals)
            if 'created_invoice_ids' in context:
                context['created_invoice_ids'].append((vals['external_invoice_id'], invoice.id))
            context['invoice_message'].append(_('Invoice was successfully created'))
        if commit:
            self.env.cr.commit()
        return invoice

    @api.model
    def get_avail_dates(self, domains=None, action_domain=False, action_context=False):
        # Funkcija gaunanti datas datos filtrui. Iškviečiama iš JavaScript'o

        context = action_context or {}
        normalized_domain = []
        self.with_context(context).get_search_domain(normalized_domain)

        if domains is None or domains == False:
            domains = []

        for domain_ele in domains:
            if isinstance(domain_ele, dict):
                if domain_ele.get('__domains', False):
                    for cmplx_domain_ele in domain_ele['__domains']:
                        if len(cmplx_domain_ele) == 1:
                            normalized_domain.append(cmplx_domain_ele[0])
                        elif len(cmplx_domain_ele) == 3:
                            normalized_domain.append(cmplx_domain_ele)
                        else:
                            continue
            elif isinstance(domain_ele, list):
#                 normalized_domain.append(domain_ele[0])
                normalized_domain += domain_ele
            else:
                continue

        if action_domain:
            for domain_ele in action_domain:
                if isinstance(domain_ele, dict):
                    if domain_ele.get('__domains', False):
                        for cmplx_domain_ele in domain_ele['__domains']:
                            if len(cmplx_domain_ele) == 1:
                                normalized_domain.append(cmplx_domain_ele[0])
                            elif len(cmplx_domain_ele) == 3:
                                normalized_domain.append(cmplx_domain_ele)
                            else:
                                continue
                elif isinstance(domain_ele, list):
                    #                 normalized_domain.append(domain_ele[0])
                    normalized_domain += domain_ele
                else:
                    continue
            # normalized_domain += action_domain

        query = self._where_calc(normalized_domain)
        from_clause, where_clause, where_clause_params = query.get_sql()
        where_str = where_clause and (" WHERE %s" % where_clause) or ''
        query_str = 'SELECT DISTINCT(date_invoice) FROM account_invoice %s ORDER BY date_invoice DESC' % where_str

        self.env.cr.execute(query_str, where_clause_params)
        res = self.env.cr.fetchall()
        dates = [tpl[0] for tpl in res]
        return dates

    @api.model
    def CreateInvoice(self, list_of_invoice_vals):
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        inter_obj = self.env['stock.route.integration.intermediate']
        log_obj = self.env['delivery.integration.log']
        
        datetimes = time.strftime('%Y-%m-%d %H:%M:%S')
        
        ctx_en = context.copy()
        ctx_en['lang'] = 'en_US'
        error = self.with_context(ctx_en).check_imported_invoice_values(list_of_invoice_vals)
        if error:
            log_vals = {
                'create_date': datetimes,
                'function': 'CreateInvoice',
                'returned_information': str(json.dumps(error, indent=2)),
                'received_information': str(json.dumps(list_of_invoice_vals, indent=2))
            }
            
            log_obj.create(log_vals)
            return error
        
        itermediate = inter_obj.create({
            'datetime': datetimes,
            'function': 'CreateInvoice',
            'received_values': str(json.dumps(list_of_invoice_vals, indent=2)),
            'processed': False
        })
        if commit:
            self.env.cr.commit()
        itermediate.process_intermediate_objects_threaded()
        return itermediate.id
    
    @api.model
    def CreateSupplierInvoice(self, list_of_invoice_vals):
        # Iš išorės(iš mazgo) kviečiama funkcija, kuri sukuria tiekėjo sąskaitos faktūros 
        # tarpinį objektą iš kurio vėliau kursis tiekėjo sąskaitos faktūros 
        
        context = self.env.context or {}
        
        commit = not context.get('no_commit', False)
        inter_obj = self.env['stock.route.integration.intermediate']
        log_obj = self.env['delivery.integration.log']
        
        datetime = time.strftime('%Y-%m-%d %H:%M:%S')
        
        ctx_en = context.copy()
        ctx_en['lang'] = 'en_US'
        error = self.with_context(ctx_en).check_imported_supplier_invoice_values(list_of_invoice_vals)
        if error:
            log_vals = {
                'create_date': datetime,
                'function': 'CreateSupplierInvoice',
                'returned_information': str(json.dumps(error, indent=2)),
                'received_information': str(json.dumps(list_of_invoice_vals, indent=2))
            }
            
            log_obj.create(log_vals)
            return error
        
        itermediate = inter_obj.create( {
            'datetime': datetime,
            'function': 'CreateSupplierInvoice',
            'received_values': str(json.dumps(list_of_invoice_vals, indent=2)),
            'processed': False
        })
        
        if commit:
            self.env.cr.commit()
        itermediate.process_intermediate_objects_threaded()
        
        return itermediate.id
    
    @api.model
    def check_imported_supplier_invoice_values(self, list_of_invoice_vals):
        # Patikrina gautas reikšmes iš mazgo ar jos atitinka visas taisykles
        # UŽBAIGTI
        return {}

    @api.multi
    def get_related_invoices(self):
        # Grąžina susijusius dokumentus. Susijęs dokumentas tai kai dokumentas yra
        # atšaukiamas būna atsiųsta anuliuojamasis dokumentas ir tada naujas, geras dokumentas.
        # Šiuos dokumentus ir grąžina.

        related_invoices = self.env['account.invoice']
        for invoice in self:
            related_invoices |= invoice
            primary_invoice = invoice.primary_invoice_id
            while primary_invoice:
                related_invoices |= primary_invoice
                primary_invoice = primary_invoice.primary_invoice_id

            new_invoice = self.search([('primary_invoice_id','=',invoice.id)])
            while new_invoice:
                related_invoices |= new_invoice
                new_invoice = self.search([('primary_invoice_id', '=', new_invoice.id)])
        return related_invoices

    @api.multi
    def action_open_related_invoices(self):
        # Atidaro susijusius dokumentus
        related_invoices = self.get_related_invoices()
        if not related_invoices or len(related_invoices) == len(self):
            raise UserError(_('Documents (%s) does not have any related documents.') % ', '.join(self.mapped('all_document_numbers')))
        form_view = self.env['ir.model.data'].xmlid_to_object('config_sanitex_delivery.view_account_invoice_bls_documents_form')[0]
        tree_view = self.env['ir.model.data'].xmlid_to_object('config_sanitex_delivery.view_account_invoice_bls_documents_tree')[0]
        return {
            'name': _('Related Invoices: %s') % ', '.join([invoice.all_document_numbers for invoice in self]),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id,'tree'),(form_view.id,'form')],
            'domain': [
                ('id','in',[related_invoice.id for related_invoice in related_invoices])
            ]
        }


    @api.model
    def check_imported_invoice_values(self, list_of_invoice_vals):
        inter_obj = self.env['stock.route.integration.intermediate']
        result = {}
        required_values = [
            'external_customer_id', 'external_invoice_id',
            'invoice_no', 'invoice_date', 'invoice_currency', 
            'invoice_lines','external_buyer_address_id'
        ]
        inter_obj.check_import_values(list_of_invoice_vals, required_values, result)
        if result:
            return result
        required_line_values = [
            'external_invoice_line_id', 'external_product_id', 'product_name',
            'product_code', 'invoice_line_qty', 'invoice_line_uom'
        ]
        i = 0
        for inv_dict in list_of_invoice_vals:
            i = i + 1
            index = str(i)
            line_results = {}
            inter_obj.check_import_values(
                inv_dict.get('invoice_lines', []),
                required_line_values, line_results, prefix=_('Invoice Line')
            )
            if line_results:
                if index in result.keys():
                    result[index].append(line_results)
                else:
                    result[index] = [line_results]
        return result
    
    @api.multi
    def get_ivaz_dictionary(self, route_id):
        usr_obj = self.env['res.users']
        route_obj = self.env['stock.route']
        
        def format_date(str_date):
            date_date = datetime.datetime.strptime(str_date, '%Y-%m-%d %H:%M:%S')
            return date_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            
        def get_address(partner, only_address=False):
            address = {}
            address['address'] = partner.street
            if not only_address:
                address['registration_code'] = partner.parent_id and partner.parent_id.ref or partner.ref or None
                address['name'] = partner.parent_id and partner.parent_id.name or partner.name or None
                
            return address
        comp = usr_obj.browse(self.env.uid).company_id
        vals = {}

        route = route_obj.browse(route_id)
        
        vals['cancelled'] = self.state == 'cancel' and True or False
        vals['id'] = self.document_id_for_ivaz or '-'
        vals['waybillid'] = self.name or ''
        vals['sender'] = get_address(comp.partner_id)
        vals['receiver'] = get_address(self.partner_shipping_id)
        vals['transporter'] = get_address(route.driver_company_id)
        vals['shipfrom'] = get_address(comp.partner_id, True)
        vals['shipto'] = get_address(self.partner_shipping_id, True)
        vals['placeofissue'] = route.source_location_id.load_address and {'address': route.source_location_id.load_address} \
            or get_address(comp.partner_id, True)
        vals['timeofdispatch'] = format_date(route.departure_time)
        vals['created'] = format_date(self.create_date)
        vals['cars'] = []
        vals['cars'].append({'carnumber': route.license_plate, 'carmodel': None})
        vals['source'] = comp.ivaz_source or 'Odoo'
        if route.trailer:
            vals['cars'].append({'carnumber': route.trailer, 'carmodel': 'Priekaba'})
        vals['products'] = []
        for line in self.invoice_line_ids:
            if line.quantity <=0:
                continue
            vals['products'].append({
                'lineid': str(line.id),
                'description': line.name,
                'quantity': line.quantity,
                'unitofmeasure': line.uom_id and line.uom_id.name,
            })
        if not vals['products']:
            raise UserError(_('Invoice (%s, ID: %s) does not have any lines with higher than zero quantity') % (
                self.name, str(self.id)
            ))
        return vals
    
    @api.multi
    def get_intermediate_ids_from_record(self, record):
        """
            Is esmes, metodas uzkojimui, taciau privalo grazinti intermediate ids,
            todel parasytas paprastas sukurimas
        """
        intem_env = self.env['stock.route.integration.intermediate']
        
        intermediate_ids = []
        
        for inv in self:
            intermediate_id = intem_env.create({
                'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
                'processed': False,
                'function': 'IVAZexport',
                'invoice_id': inv.id,
            })
            self._cr.commit()
            intermediate_ids.append(intermediate_id)
        
        return intermediate_ids
    
    @api.model
    def get_record_model(self, record):
        return record._name
    
    @api.model
    def get_record_table_name(self, record):
        model_env = self.env['ir.model']
        model = model_env.search([('model','=',record._name)], limit=1)
        
        return model and model.name or _('Unknown Table')
    
    @api.multi
    def get_ivaz_dictionary_from_rec(self, record):
        self.ensure_one()
        return []

    @api.multi
    def export_invoice_to_ivaz(self, rec):
        context = self.env.context or {}
        if context.get('do_not_export_to_ivaz', False):
            return False
        usr_obj = self.env['res.users']
        intem_obj = self.env['stock.route.integration.intermediate']
        
        
        company = usr_obj.browse(self.env.uid).company_id
        server = company.ivaz_export_server
        token = company.ivaz_export_token
        
        record_model = self.get_record_model(rec)
        
        from_stock_route = record_model == 'stock.route'
        
        if from_stock_route:
            intermediates = intem_obj.search([
                ('route_to_ivaz_id','=',rec.id)
            ])
            
            if not intermediates:
                intermediates = intem_obj.create({
                    'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'processed': False,
                    'function': 'IVAZexport',
                    'route_to_ivaz_id': rec.id
                })
                self.env.cr.commit()
        else:
            intermediates = self.get_intermediate_ids_from_record(rec)
        
        headers = {
            'Content-type': 'application/json',
            'Accept': 'text/plain',
            'waybill2vmi-token': token
        }
        for intermediate_record in intermediates:
            msg = ''
            trb = ''
            processed = True
            invoce_dict_list = []
            invoice_ids = []
            if not from_stock_route:
                invoice_ids = []
                intermediate = intermediate_record.read(['invoice_id'])[0]
                if intermediate['invoice_id'] and intermediate['invoice_id'][0]:
                    invoice_ids = [intermediate['invoice_id'][0]]
            try:
                if from_stock_route:
                    for invoice in self.filtered('invoice_line_ids'):
                        invoce_dict_list.append(invoice.get_ivaz_dictionary(rec.id))
                else:
                    for id in invoice_ids:
                        invoce_dict_list += self.browse(id).get_ivaz_dictionary_from_rec(rec)
                 
                record_table_name = self.get_record_table_name(rec)
                intermediate_record.write({
                    'received_values': record_table_name + ': ' + str(rec.id) + '\n\n' + json.dumps(invoce_dict_list, indent=2),
                })
                self.env.cr.commit()
                if not server:
                    raise UserError(_('To export invoice to IVAZ you need to fill in export server in company\'s %s settings') %company.name)
                if not token:
                    raise UserError(_('To export invoice to IVAZ you need to fill in export server\'s token in company\'s %s settings') %company.name)
                response = requests.post(server, data=json.dumps(invoce_dict_list), headers=headers)
                intermediate_record.write({
                    'return_results': str(response),
                    'processed': processed
                })
            
            except UserError as e:
                err_note = _('Failed to send to IVAZ: %s') % (tools.ustr(e),)
                msg += err_note
                trb = traceback.format_exc() + '\n\n'
                processed = False
                self.env.cr.rollback()
            except Exception as e:
                err_note = _('Failed to send to IVAZ: %s') % (tools.ustr(e),)
                msg += err_note
                trb = traceback.format_exc() + '\n\n'
                processed = False
                self.env.cr.rollback()
            if msg:
                intermediate_record.write({
                    'return_results': msg,
                    'traceback': trb,
                    'processed': processed
                })
            if processed:
                self.env.cr.commit()
        
        return True

    @api.multi
    def export_invoices_to_ivaz(self, rec):
        usr_obj = self.env['res.users']
        company = usr_obj.browse(self.env.uid).company_id
        if not company.export_ivaz or not self:
            return False
        self.export_invoice_to_ivaz(rec)
        return True

    @api.multi
    def export_invoices_to_ivaz_threaded(self, rec):
        usr_obj = self.env['res.users']
        company = usr_obj.browse(self.env.uid).company_id
        if not company.export_ivaz or not self:
            return False
        t = threading.Thread(target=self.thread_export_invoices_to_ivaz, args=(rec))
        t.start()

    @api.multi
    def thread_export_invoices_to_ivaz(self, rec):
        with Environment.manage():
            new_cr = self.pool.cursor()
            new_self = self.with_env(self.env(cr=new_cr))
            try:
                new_self.export_invoices_to_ivaz(rec)
                new_cr.commit()
            finally:
                new_cr.close()
    
    @api.model
    def check_invoice_vals(self, invoice_vals):
        if not invoice_vals.get('partner_id', False):
            raise UserError(
                _('Invoice has to have \'%s\' filled') % _('Client')
            )
        return True
    
    @api.multi
    def get_total_weight(self):
        weight = 0.0
        for invoice in self:
            for line in invoice.invoice_line_ids:
                weight += line.get_total_weight()
        return weight

    @api.multi
    def update_total_weight(self):
        context = self.env.context or {}
        if context.get('skip_weight_calculation', False):
            return
        for invoice in self:
            total_task_weight = invoice.get_total_weight()
            if invoice.total_weight != total_task_weight:
                invoice.write({'total_weight': total_task_weight})

    @api.multi
    def update_weight_with_sql(self):
        if self:
            upd_weight_sql = '''
                UPDATE
                    account_invoice ai
                SET
                    total_weight = (select SUM(total_weight) from account_invoice_line where invoice_id = ai.id)
                WHERE 
                    ai.id in %s
            '''
            upd_weight_where = (self._ids,)
            self.env.cr.execute(upd_weight_sql, upd_weight_where)
            self.invalidate_cache(fnames=['total_weight'], ids=list(self._ids))

    @api.multi
    def get_sale_vals_from_invoice(self):
        so_obj = self.env['sale.order']
        vals = so_obj.default_get(so_obj._fields)
        vals['warehouse_id'] = self.picking_warehouse_id and self.picking_warehouse_id.id or False
        vals['picking_location_id'] = self.picking_location_id and self.picking_location_id.id or False
        vals['partner_id'] = self.partner_id and self.partner_id.id or False
        temp_so = so_obj.new(vals)
        temp_so.onchange_partner_id()
        vals.update(temp_so._convert_to_write(temp_so._cache))
        vals['partner_invoice_id'] = self.partner_shipping_id and self.partner_shipping_id.id or False
        vals['partner_shipping_id'] = self.partner_shipping_id and self.partner_shipping_id.id or False
        vals['delivery_type'] = 'delivery'
        vals['shipping_date'] = self.date_invoice
        vals['date_order'] = time.strftime('%Y-%m-%d %H:%M:%S')
        vals['name'] = self.number or self.name or self.external_invoice_id or ''
        vals['owner_id'] = self.owner_id and self.owner_id.id or False
        vals['previous_task_received'] = True
        vals['replanned'] = False
        vals['external_sale_order_id'] = 'FROM_INVOICE_' + self.external_invoice_id
        if self.operation_type == 'atlas_movement':
            vals['external_sale_order_id'] = 'FROM_MOVEMENT_' + (self.external_invoice_id or str(self.id))
        if self.operation_type == 'atlas_movement' and self.destination_location_id:
            vals['shipping_warehouse_id'] = self.destination_location_id.get_location_warehouse_id().id

        vals['order_package_type'] = 'order'
        return vals

    @api.model
    def show_print_button(self, ids, context):
        return False

    @api.multi
    def create_sale(self):
        context = self.env.context or {}
        ctx = context.copy()
        ctx['skip_task_line_recount'] = True
        ctx['skip_missing_links'] = True

        so_obj = self.env['sale.order']
        sol_obj = self.env['sale.order.line']
        sales = so_obj.browse([])
        for invoice in self:
            if invoice.automatically_created_sale_id:
                sale = invoice.automatically_created_sale_id
            else:
                sale_vals = invoice.get_sale_vals_from_invoice()
                sale = so_obj.create(sale_vals)
                invoice.write({'automatically_created_sale_id': sale.id})
            for line in invoice.invoice_line_ids:
                if line.automatically_created_sale_line_id:
                    continue
                line_vals = line.get_sale_line_vals_from_invoice_line()
                line_vals['order_id'] = sale.id
                sol = sol_obj.with_context(ctx).create(line_vals)
                sol.with_context(skip_weight_calculation=True).update_pallet_quantity()
                # line.write({'automatically_created_sale_line_id': sol.id})
                write_sql = '''
                    UPDATE
                        account_invoice_line
                    SET
                       automatically_created_sale_line_id = %s
                    WHERE
                        id = %s
                '''
                write_where = (sol.id, line.id)
                self.env.cr.execute(write_sql, write_where)
            # for move in invoice.move_ids:
            #     if move.automatically_created_sale_line_id:
            #         continue
            #     line_vals = move.get_sale_line_vals_from_move()
            #     line_vals['order_id'] = sale.id
            #
            #     sol = sol_obj.with_context(ctx).create(line_vals)
            #     sol.with_context(skip_weight_calculation=True).update_pallet_quantity()
            #     move.write({'automatically_created_sale_line_id': sol.id})
            sales += sale
        self.update_sale_orders()
        sales.create_container_for_sale()
        sales.create_transportation_order_for_sale()
        sales.recount_lines_numbers()
        sales.update_weight_and_pallete_with_sql()
        return sales

    @api.multi
    def copy(self, default=None):
        context = self.env.context or {}
        if not context.get('allow_inv_copy', False):
            raise UserError(_('You cannot duplicate an invoice.'))
        
        return super(AccountInvoice, self).copy(default=default)


    @api.multi
    def get_related_tasks_sql(self):
        so_env = self.env['sale.order']
        if self:
            get_ord_sql = '''
                SELECT
                    so.id
                FROM
                    sale_order so
                    JOIN sale_order_line sol on (sol.order_id = so.id)
                    JOIN invoice_line_so_line_rel rel on (rel.order_line_id = sol.id)
                    JOIN account_invoice_line ail on (ail.id = rel.invoice_line_id)
                    JOIN account_invoice ai on (ail.invoice_id=ai.id)
                WHERE
                    ai.id in %s
            '''
            get_ord_where = (self._ids,)
            self.env.cr.execute(get_ord_sql, get_ord_where)
            so_ids = [so_id[0] for so_id in self.env.cr.fetchall()]
            return so_env.browse(so_ids)
        return so_env



    @api.multi
    def update_sale_orders_sql(self):
        if self:
            get_inv_lines_sql = '''
                INSERT INTO 
                    invoice_so_line_rel 
                SELECT 
                    ai.id, rel.order_line_id 
                FROM 
                    invoice_line_so_line_rel rel 
                    join account_invoice_line ail on (ail.id = rel.invoice_line_id)
                    join account_invoice ai on (ai.id = ail.invoice_id)
                    left join invoice_so_line_rel rel2 on (rel2.invoice_id = ai.id and rel2.order_line_id = rel.order_line_id)
                WHERE
                    (rel2.invoice_id is null or rel2.order_line_id is null)
                    AND ai.id in %s
                GROUP BY
                    ai.id, rel.order_line_id
            '''
            get_inv_lines_where = (self._ids,)
            self.env.cr.execute(get_inv_lines_sql, get_inv_lines_where)

            upd_ord_lines_sql = '''
                UPDATE
                    sale_order_line
                SET
                    has_related_document = True
                WHERE
                    id in (
                        SELECT
                            rel.order_line_id
                        FROM
                            invoice_line_so_line_rel rel
                            join account_invoice_line ail on (ail.id=rel.invoice_line_id)
                        WHERE
                            ail.invoice_id in %s
                    )
            '''
            upd_ord_lines_where = (self._ids,)
            self.env.cr.execute(upd_ord_lines_sql, upd_ord_lines_where)
            tasks = self.get_related_tasks_sql()
            tasks.compute_invoice_number_sql()
            tasks.update_document_template_info()

    @api.multi
    def update_sale_orders(self):
        res =  self.update_sale_orders_sql()
        return res
        # sol_obj = self.env['sale.order.line']
        # so_obj = self.env['sale.order']
        # sale_ids = []
        # line_ids = []
        # for invoice in self:
        #     invoice_sale_order_line_ids = invoice.sale_order_line_ids.mapped('id')
        #     inv_lines_sale_order_line_ids = []
        #     for line in invoice.invoice_line_ids:
        #         inv_lines_sale_order_line_ids += line.sale_order_line_ids.mapped('id')
        #         line_ids += line.sale_order_line_ids.mapped('id')
        #     set_invoice_sale_order_line_ids = set(invoice_sale_order_line_ids)
        #     set_inv_lines_sale_order_line_ids = set(inv_lines_sale_order_line_ids)
        #     missing_sol_ids = set_inv_lines_sale_order_line_ids - set_invoice_sale_order_line_ids
        #     non_existed_sol_ids = set_invoice_sale_order_line_ids - set_inv_lines_sale_order_line_ids
        #     # all_sale_order_line_ids = set(missing_sol_ids) | set(non_existed_sol_ids)
        #     sale_order_line_ids = []
        #     for missing_sol_id in missing_sol_ids:
        #         sale_order_line_ids.append((4, missing_sol_id))
        #     for non_existed_sol_id in non_existed_sol_ids:
        #         sale_order_line_ids.append((3, non_existed_sol_id))
        #     invoice.write({'sale_order_line_ids': sale_order_line_ids})
        #     for sol_id in set_inv_lines_sale_order_line_ids:
        #         sol = sol_obj.browse(sol_id)
        #         if sol.order_id.id not in sale_ids:
        #             sale_ids.append(sol.order_id.id)
        # sol_obj.search([('id','in',line_ids),('has_related_document','=',False)]).write({'has_related_document': True})
        # so_obj.browse(sale_ids).compute_invoice_number()
        # so_obj.browse(sale_ids).update_document_template_info()
        # return True
    
    @api.model
    def get_readonly_fields_vals(self, vals):
        res = {}
        context = self.env.context or {}
        partner_env = self.env['res.partner']
        if vals.get('partner_id', False) and not context.get('skip_invoice_create_readonly_update', False):
            partner = partner_env.search([('id','=',vals['partner_id'])], limit=1)
            res['supplier_code'] = partner.supplier_code
            res['partner_ref'] = partner.ref or ''
            res['partner_name'] = partner.name or ''

        if vals.get('partner_shipping_id', False) and not context.get('skip_invoice_create_readonly_update', False):
            partner = partner_env.search([('id','=',vals['partner_shipping_id'])], limit=1)
            res['partner_address'] = partner.street or ''
        return res

    @api.multi
    def update_line_count(self):
        if self:
            count_sql = '''
                UPDATE
                    account_invoice ai
                SET
                    line_count = (
                            SELECT 
                                count(id) 
                            FROM 
                                account_invoice_line 
                            WHERE 
                                invoice_id = ai.id
                        )
                WHERE
                    id in %s
            '''
            count_where = (self._ids,)
            self.env.cr.execute(count_sql, count_where)

    @api.multi
    def update_full_name(self):
        context = self.env.context or {}
        if context.get('skip_full_name_update', False) or not self:
            return
        full_name_sql = '''
            UPDATE
                account_invoice
            SET
                all_document_numbers = (
                    CASE
                        WHEN nkro_number is not null
                            AND nkro_number != ''
                            AND nsad_number is not null
                            AND nsad_number != ''
                        THEN nkro_number || ', ' || nsad_number
                        WHEN nkro_number is not null
                            AND nkro_number != ''
                            AND (nsad_number is null
                            OR nsad_number = '')
                        THEN nkro_number
                        WHEN nsad_number is not null
                            AND nsad_number != ''
                            AND (nkro_number is null
                            OR nkro_number = '')
                        THEN nsad_number
                        WHEN (nsad_number is null
                            OR nsad_number = '')
                            AND (nkro_number is null
                            OR nkro_number = '')
                        THEN name
                    END
                )
            WHERE
                id in %s    
        '''
        full_name_where = (self._ids,)
        self.env.cr.execute(full_name_sql, full_name_where)

    @api.model
    def check_if_replanned_by_id(self, invoice_id, route_id):
        if type(invoice_id) == int and type(route_id) == int:
            replanned_sql = '''
                SELECT
                    ai.id
                FROM
                    account_invoice ai
                    JOIN account_invoice_line ail on (ail.invoice_id = ai.id)
                    JOIN invoice_line_so_line_rel ilslr on (ilslr.invoice_line_id = ail.id)
                    JOIN sale_order_line sol on (sol.id = ilslr.order_line_id)
                    JOIN sale_order so on (so.id = sol.order_id)
                    JOIN stock_route_invoice_rel srir on (srir.invoice_id = ai.id and so.route_id = srir.route_id)
                WHERE
                    ai.id = %s
                    AND so.route_id = %s
                    AND (so.replanned = True or so.after_replan = True)
            '''
            replanned_where = (invoice_id, route_id)
            self.env.cr.execute(replanned_sql, replanned_where)
            if self.env.cr.fetchall():
                return True
        return False

    @api.model
    def create(self, vals):
        if 'time_invoice' not in vals.keys():
            vals['time_invoice'] = utc_str_to_local_str(date_format='%H:%M')
        if 'document_create_datetime' not in vals.keys():
            vals['document_create_datetime'] = time.strftime('%Y-%m-%d %H:%M:%S')
        vals.update(self.get_readonly_fields_vals(vals))
        res = super(AccountInvoice, self).create(vals)
        res.set_version()
        if {'name', 'nkro_number', 'nsad_number'} & set(vals.keys()):
            res.update_full_name()
        return res


    @api.multi
    def read(self, fields=None, load='_classic_read'):

        res = super(AccountInvoice, self).read(fields=fields, load=load)
        context = self.env.context or {}
        if context.get('check_for_replanned_tasks', False):
            if 'name' in fields and 'id' not in fields:
                fields.append('id')
        if context.get('check_for_replanned_tasks', False):
            for invoice in res:
                if self.check_if_replanned_by_id(invoice['id'], context['check_for_replanned_tasks']):
                    invoice['name'] = _('(R)') + '' + invoice['name']
        return res

    @api.multi
    def write(self, vals):
        if 'partner_id' in vals:
            vals.update(self.get_readonly_fields_vals(vals))
        if set(vals.keys()) & {
            'external_invoice_id', 'name', 'cash_amount', 'date_invoice',
            'owner_id', 'posid', 'sale_order_line_ids'
        }:
            self.set_version()
        res = super(AccountInvoice, self).write(vals)
        if {'name', 'nkro_number', 'nsad_number'} & set(vals.keys()):
            self.update_full_name()
        return res

    @api.multi
    def remove_from_system(self):
        self.with_context(recompute=False).sudo().unlink()
    
#     def can_delete_invoice(self, date_until=None):
#         if date_until is None:
#             user = self.env['res.users'].browse(self.env.uid)
#             company = user.company_id
#             days_after = company.delete_invoices_after
#             today = datetime.datetime.now()
#             date_until = (today - datetime.timedelta(days=days_after)).strftime('%Y-%m-%d %H:%M:%S')        
#         if not self.date_invoice < date_until:
#             return False
#         return True

    @api.multi
    def update_line_subtotals(self):
        if self:
            update_sql = '''
                SELECT
                    id
                FROM
                    account_invoice_line
                WHERE
                    invoice_id in %s
            '''
            update_where = (self._ids,)
            self.env.cr.execute(update_sql, update_where)
            line_ids_results = self.env.cr.fetchall()
            self.env['account.invoice.line'].browse([line_id[0] for line_id in line_ids_results]).update_subtotals()

    @api.multi
    def update_amounts(self):
        self.update_line_subtotals()
        self.invalidate_cache(fnames=[
            'amount_untaxed', 'amount_untaxed_signed', 'amount_tax',
            'amount_total', 'amount_total_signed', 'amount_total_company_signed',
        ], ids=list(self._ids))
        self.env.add_todo(self._fields['amount_untaxed'], self)
        self.env.add_todo(self._fields['amount_untaxed_signed'], self)
        self.env.add_todo(self._fields['amount_tax'], self)
        self.env.add_todo(self._fields['amount_total'], self)
        self.env.add_todo(self._fields['amount_total_signed'], self)
        self.env.add_todo(self._fields['amount_total_company_signed'], self)
        self.with_context(recompute=True).recompute()
        
    @api.model
    def cron_delete_old_account_invoices(self):
        # Krono paleidžiama funkcija, kuri trina senas sąskaitas faktūras        
        
        user = self.env['res.users'].browse(self.env.uid)
        company = user.company_id
        log = company.log_delete_progress or False
        days_after = company.delete_invoices_after
        date_field = company.get_date_field_for_removing_object(self._name)

        _logger.info('Removing old Invoices (%s days old) using date field \'%s\'' % (str(days_after), date_field))

        today = datetime.datetime.now()
        date_until = today - datetime.timedelta(days=days_after)

        invoices = self.search([
            (date_field,'<',date_until.strftime('%Y-%m-%d %H:%M:%S')),
        ])
        _logger.info('Removing old Invoices: found %s records' % str(len(invoices)))
        if log:
            all_invoice_count = float(len(invoices))
            i = 0
            last_log = 0
        ids_to_unlink = invoices.mapped('id')
        # for invoice in invoices:
        for invoice_ids in [ids_to_unlink[ii:ii+50] for ii in range(0, len(ids_to_unlink), 50)]:
            # if not invoice.exists():
            #     continue
            try:
                # invoice.remove_from_system()
                # self.env.cr.commit()
                self.browse(invoice_ids).remove_from_system()
                self.env.cr.commit()
                if log:
                    i += 1
                    if last_log < int((i / all_invoice_count)*100):
                        last_log = int((i / all_invoice_count)*100)
                        _logger.info('Invoice delete progress: %s / %s' % (str(i), str(int(all_invoice_count))))
            except Exception as e:
                err_note = 'Failed to delete  Invoice(ID: %s): %s \n\n' % (str(invoice_ids), tools.ustr(e),)
                trb = traceback.format_exc() + '\n\n'
                _logger.info(err_note + trb)
    
    @api.model
    def get_pod_domain(self, obj):
        context = self.env.context or {}
        if context.get('for_raml', False):
            self.env.cr.execute('''
                SELECT
                    invoice_id
                FROM
                    stock_route_invoice_rel
                WHERE
                    route_id in (SELECT id FROM stock_route)
            ''')
            ids_res = self.env.cr.fetchall()
            ids = [id_res[0] for id_res in ids_res]
            return [('id','in', ids)]
        return []
    
    @api.multi
    def set_version(self):
        for inv in self:
            self._cr.execute('''
                UPDATE
                    account_invoice
                SET
                    id_version = %s
                WHERE id = %s
            ''', (get_local_time_timestamp(), inv.id))
        return True

    @api.multi
    def to_dict_for_pod_integration(self, obj):
        route_env = self.env['stock.route']
        
        order_numbers = set([])
#         route_str_ids = set([])

        position_in_route = None
        business_hours = None
        for order_line in self.invoice_line_ids.mapped('sale_order_line_ids'):
            order = order_line.order_id
            if order and order.name:
                order_numbers.add(order.name)
            if order.delivered_goods_time:
                business_hours = order.delivered_goods_time
            if order.order_number_by_route:
                try:
                    int(order.order_number_by_route)
                    position_in_route = order.order_number_by_route
                except:
                    position_in_route = None
        if (position_in_route is None or business_hours is None) and self.stock_package_id:
            task = self.env['sale.order'].search([
                ('delivery_type','=',self.delivery_type),
                ('related_package_id','=',self.stock_package_id.id),
                ('replanned','=',False)
            ], order='id desc', limit=1)
            if task.order_number_by_route:
                try:
                    int(task.order_number_by_route)
                    position_in_route = task.order_number_by_route
                except:
                    position_in_route = None
            if task.delivered_goods_time:
                business_hours = task.delivered_goods_time
            order_numbers.add(task.name)

        order_numbers = list(order_numbers)
        
#         carrier_ids_external = set([])
        routes = route_env.search([
            ('invoice_ids','in',self.id)
        ])
        route_dicts = []
        for route in routes:
            if route.state == 'draft':
                continue
            route_dicts.append(route.to_dict_for_pod_integration('route'))
#             route_str_ids.add(str(route.id))
#             if route.location_id and route.location_id.owner_id\
#              and route.location_id.owner_id.external_customer_id:
#                 carrier_ids_external.add(route.location_id.owner_id.external_customer_id)
#         carrier_ids_external = list(carrier_ids_external)
#         route_str_ids = list(route_str_ids)
        if business_hours and isinstance(business_hours, str) and len(business_hours.split(' - ')) == 2:
            business_hours_from = business_hours.split(' - ')[0]
            business_hours_to = business_hours.split(' - ')[1]
            if not hours_re.match(business_hours_from):
                business_hours_from = None
            if not hours_re.match(business_hours_to):
                business_hours_to = None
        else:
            business_hours_from = None
            business_hours_to = None

        cash = False
        if self.cash_amount and self.cash_amount > 0.0:
            cash = True

        return {
            'documentId': self.external_invoice_id or str(self.id) or "",
#             'routeIds': route_str_ids,
#             'carrierIds': carrier_ids_external, 
            'routes': route_dicts,
            'orderNumbers': order_numbers,
            'orderExternalNo': self.name or "",
            'noteForDriver': "", #tuscia, nes po to gausim patys is POD
            'orderSum': self.cash_amount or 0.0,
            'orderDate': self.date_invoice or "",
            'owner_id': self.owner_id and self.owner_id.product_owner_external_id or "",
            'destinationPlaceId': self.posid or "",            
            'deleted': False,
            "id_version": self.id_version,
            'documentPositionInRoute': position_in_route,
            'businessHoursFrom': business_hours_from,
            'businessHoursTo': business_hours_to,
            'cash': cash,
            'package': self.stock_package_id and True or False,
        }
        
    @api.multi
    def action_invoice_paid(self):
        return False
    
    @api.multi
    def action_invoice_re_open(self):
        return False
                    
class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

#     @api.depends(
#         'product_id','product_id.small_package_size',
#         'product_id.big_package_size'
#     )
#     def _get_packages_sizes(self):
#         for inv_line in self:
#             
#             sps = 0.0
#             bps = 0.0
#             if self.product:
#                 sps = self.product.small_package_size or 0.0
#                 bps = self.product.big_package_size or 0.0
#                 
#             inv_line.update({
#                 'small_package_size': sps,
#                 'big_package_size': bps,
#             })
               
    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
        'product_id', 'invoice_id.currency_id', 'invoice_id.company_id',
        'invoice_id.doc_discount', 
    )
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.price_unit * (1 - ((self.discount + self.invoice_id.doc_discount)or 0.0) / 100.0)
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
        if self.invoice_id.currency_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            price_subtotal_signed = self.invoice_id.currency_id.compute(price_subtotal_signed, self.invoice_id.company_id.currency_id)
        sign = (self.invoice_id.type in ['in_refund', 'out_refund'] or self.invoice_id.annul_document) and -1 or 1
        self.price_subtotal = price_subtotal
        self.price_subtotal_signed = price_subtotal_signed * sign
        self.discount_amount = round(self.price_unit * self.quantity, 2)\
            * ((self.discount + self.invoice_id.doc_discount) / 100.0)
        self.price_after_disc = self.price_unit - (self.price_unit * self.discount / 100)

    @api.model
    def _get_default_account(self):
        return self.env['account.invoice']._get_default_account()

    external_invoice_line_id = fields.Char('External ID', size=64, readonly=True)
    sale_order_line_ids = fields.Many2many(
        'sale.order.line', 'invoice_line_so_line_rel', 'invoice_line_id',
        'order_line_id', 'Sale Order Lines'
    )
    uom = fields.Char('UOM', size=64)
    product_code = fields.Char('Product Code', readonly=True, size=128)
    temp_quantity = fields.Integer('Quantity', readonly=True)
    automatically_created_sale_line_id = fields.Many2one('sale.order.line', 'Automatically Created Sale Line')
    lot_id = fields.Many2one('stock.production.lot', 'Lot')
    packing_needed = fields.Boolean('Packing Needed')
    account_id = fields.Many2one('account.account', 'Account', default=_get_default_account, required=False)
    certificate_id = fields.Many2one('product.certificate', "Certificate")
    small_package_qty = fields.Float("Small Package Quantity")
    big_package_qty = fields.Float("Big Package Quantity")
    small_package_size = fields.Float("Small Package Size", readonly=True)
    big_package_size = fields.Float("Big Package Size", readonly=True)
    price_subtotal_editable = fields.Float("Amount")
    product_qty = fields.Float(
        "Product Quantity", digits=(12, 3), help="Product quantity not in package"
    )
    location_id = fields.Many2one('stock.location', "Location",
        help="If it is empty, then it means that this lines location matches invoice's location."
    )
    package = fields.Boolean("Package", default=False)
    discount_amount = fields.Float(string='Discount Amount',
        store=True, readonly=True, compute='_compute_price'
    )
    container_line_ids = fields.One2many(
        'account.invoice.container.line', 'invoice_line_id',
        string="Primary Container Lines" 
    )
    related_container_line_ids = fields.Many2many(
        'account.invoice.container.line', 'invoice_line_container_line_rel',
        'invoice_line_id', 'container_line_id',
        string="Related Container Lines" 
    )
    total_weight = fields.Float('Total Weight', digits=dp.get_precision('Stock Weight'), readonly=True)
    id_version = fields.Char('POD Version', size=128, readonly=True)


    partner_id = fields.Many2one('res.partner', string='Partner',
        related=False, store=True, readonly=True)

    _sql_constraints = [
        ('external_invoice_line_id', 'unique (external_invoice_line_id)', 'External ID of invoice line has to be unique')
    ]

    @api.model_cr
    def init(self):
        cr = self.env.cr
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('account_invoice_line_automatically_created_sale_line_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX account_invoice_line_automatically_created_sale_line_id_index ON account_invoice_line (automatically_created_sale_line_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('account_invoice_line_external_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX account_invoice_line_external_id_index ON account_invoice_line (external_invoice_line_id)')

    @api.multi
    def get_container(self):
        containers = self.env['account.invoice.container'].browse([])
        if self.sale_order_line_ids:
            orders = self.sale_order_line_ids.mapped('order_id')
            containers = orders.mapped('container_ids')
            # and self.sale_order_line_ids.order_id.container_ids \
            # container =
            # container = self.sale_order_line_ids.order_id.container_ids
        return containers

    @api.multi
    def update_subtotals(self):
        self.invalidate_cache(fnames=['price_subtotal'], ids=list(self._ids))
        self.env.add_todo(self._fields['price_subtotal'], self)
        self.with_context(recompute=True).recompute()

    @api.multi
    def invoice_line_to_dict_for_rest_integration(self):
        return {
            'cargoId': self.external_invoice_line_id or '',
            # 'type': '', #negaunam
            'itemCode': self.product_id and self.product_id.default_code or '',
            'itemEanCode': '',#self.product_id and self.product_id.default_code or '',
            'boxEanCode': '', #ar tinka barkodas, jei taip tai kokio tipo barkodo reikia
            'itemName': self.product_id and self.product_id.name or self.name or '',
            'unitOfMeasure': self.uom_id and self.uom_id.name or self.product_id and self.product_id.uom_id \
                and self.product_id.uom_id.name or '',
            'unitGrossWeight': self.product_id and self.product_id.weight or 0.0,
            'expectedQuantity': self.quantity or 0.0,
            'acceptedQuantity': self.quantity or 0.0,
            # 'carrierId': '',
            'deleted': False,
            'orderId': self.invoice_id and self.invoice_id.external_invoice_id \
                and ''.join(self.invoice_id.external_invoice_id.split('-')[:-1]) or '',
            'containerId': self.get_container() and (
                self.get_container().container_no or self.get_container().id_external or str(self.get_container().id)
            ) or '',
        }


    @api.model
    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        context = self.env.context or {}
        ctx = context.copy()
        view_ref_key = view_type + '_view_ref'
        if view_ref_key in ctx.keys():
            view = self.env.ref(ctx[view_ref_key])
            if view.model != self._name:
                del ctx[view_ref_key]
        return super(AccountInvoiceLine, self.with_context(ctx))._fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )

    @api.model
    def check_invoice_line_vals(self, invoice_line_vals):
        if not invoice_line_vals.get('product_id', False):
            raise UserError(
                _('Invoice line has to have \'%s\' filled') % _('Product')
            )
        if not invoice_line_vals.get('quantity', False):
            invoice_line_vals['quantity'] = 0.0
            # raise UserError(
            #     _('Invoice line has to have \'%s\' filled') % _('Quantity')
            # )
        if not invoice_line_vals.get('price_unit', False):
            invoice_line_vals['price_unit'] = 0.0
        return True

    @api.model
    def create_invoice_line(self, vals):
        interm_obj = self.env['stock.route.integration.intermediate']
        context = self.env.context or {}
        commit = not context.get('no_commit', False)

        line = self.search([
            ('external_invoice_line_id','=',vals['external_invoice_line_id'])
        ], limit=1)
        if line and interm_obj.do_not_update_vals('account.invoice.line'):
            return line
        invoice_line_vals = self.default_get(self._fields)
        invoice_line_vals.update(vals)
        if line:
            interm_obj.remove_same_values(line, invoice_line_vals)
            if invoice_line_vals:
                line.write(invoice_line_vals)
        else:
            self.check_invoice_line_vals(invoice_line_vals)
            line = self.with_context(recompute=False, skip_sale_order_check=True).create(invoice_line_vals)
        if commit:
            self.env.cr.commit()
        return line
    
                   
#     def __init__(self, pool, cr):
#         cr.execute("""
#             SELECT 
#                 count(*)
#             FROM 
#                 INFORMATION_SCHEMA.COLUMNS 
#             WHERE 
#                 table_name = 'account_invoice_line' 
#                 AND column_name = 'temp_quantity'
#         """)
#         res = cr.fetchone()
#         if res and res[0] > 0:
#             cr.execute("""
#                 UPDATE 
#                     account_invoice_line 
#                 SET 
#                     quantity = temp_quantity
#                 WHERE 
#                     quantity = 0
#                     AND temp_quantity <> 0
#             """)
#         
#         cr.execute("""
#             SELECT 
#                 column_name
#             FROM 
#                 INFORMATION_SCHEMA.COLUMNS 
#             WHERE 
#                 table_name = 'account_invoice_line' 
#                 AND column_name like 'quantity_moved%'
#             ORDER BY
#                 ordinal_position
#         """)
#         res = cr.fetchall()
#         if res:
#             for column in res:
#                 if column:
#                     try:
#                         cr.execute("""
#                             ALTER TABLE 
#                                 account_invoice_line
#                             DROP COLUMN 
#                                 %s
#                         """ %column[0])
#                         cr.commit()
#                     except:
#                         cr.rollback()
#                         pass
#         return super(account_invoice_line, self).__init__(pool, cr)
    
    @api.onchange('small_package_qty', 'big_package_qty', 'product_qty')
    def _onchange_package_or_product_qty(self):
        self.quantity = ((self.small_package_qty or 0.0) * (self.small_package_size or 0.0)) +\
        ((self.big_package_qty or 0.0) * (self.big_package_size or 0.0)) + (self.product_qty or 0.0)
        
        self._onchange_price_unit()  
#         return

#     @api.onchange('quantity')
#     def _onchange_total_qty(self):
#         total_qty = self.quantity
#         if self.big_package_size:
#             bpq = int(total_qty/self.big_package_size)
#             self.big_package_qty = bpq
#             total_qty -= bpq * self.big_package_size
#         if self.small_package_size:
#             spq = int(total_qty/self.small_package_size)
#             self.small_package_qty = spq
#             total_qty -= spq * self.small_package_size
#         self.product_qty = total_qty
#         
#         self._onchange_price_unit() 

    @api.onchange('price_unit','discount')
    def _onchange_price_unit(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        self.price_subtotal_editable = taxes['total_excluded'] if taxes else self.quantity * price
#         self.price_subtotal = (self.price_unit or 0.0) * (self.quantity or 0.0)  
#         return
    
    @api.onchange('price_subtotal_editable')
    def _onchange_price_subtotal(self):
        if self.quantity == 0.0:
            self.price_unit = 0.0
        else:
            self.price_unit = ((self.price_subtotal_editable or 0.0) / ((100.0-self.discount)/100.0)) / self.quantity 
#         return
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.small_package_size = self.product_id.small_package_size or 0.0
            self.big_package_size = self.product_id.big_package_size or 0.0
            self.product_code = self.product_id.default_code or False
        else:    
            self.small_package_size = 0.0
            self.big_package_size = 0.0
        self._onchange_package_or_product_qty()
            
        res = super(AccountInvoiceLine, self)._onchange_product_id()
        
        if not self.name and self.product_id:
            self.name = self.product_id.name
        
        return  res
          
    @api.multi
    def get_total_weight(self):
        weight = 0.0
        for line in self:
            if line.product_id:
                weight += line.product_id.get_weight(qty=line.quantity)
                # if line.product_id.product_type == 'fixed':
                #     weight += line.quantity
                # else:
                #     weight += line.product_id.weight * line.quantity
        return weight

    @api.multi
    def get_sale_line_vals_from_invoice_line(self):
        sol_obj = self.env['sale.order.line']
        vals = sol_obj.default_get(sol_obj._fields)
        vals['product_id'] = self.product_id and self.product_id.id or False
               
        temp_sol = sol_obj.new(vals)
        temp_sol.product_id_change()
        vals.update(temp_sol._convert_to_write(temp_sol._cache))
        vals['product_uom_qty'] = self.quantity
        vals['price_unit'] = self.price_unit
        vals['discount'] = self.discount
        vals['invoice_line_ids'] = [(6, 0, [self.id])]
        vals['total_weight']  = self.total_weight
        vals['picked_qty']  = self.quantity
        return vals

    @api.multi
    def check_sale_orders(self):
        context = self.env.context or {}
        if context.get('skip_sale_order_check', False):
            return
        ai_obj = self.env['account.invoice']
        invoice_ids = []
        for line in self:
            if line.invoice_id.id not in invoice_ids:
                invoice_ids.append(line.invoice_id.id)
        ai_obj.browse(invoice_ids).update_sale_orders()
        return True
    
    @api.model
    def get_readonly_fields_vals(self, vals):
        res = {}
        if vals.get('product_id', False):
            prod_env = self.env['product.product']
            product = prod_env.search([('id','=',vals['product_id'])], limit=1)
            res['product_code'] = product.default_code or False
            res['small_package_size'] = product.small_package_size or 0.0
            res['big_package_size'] = product.big_package_size or 0.0
        return res

    @api.model
    def _search(
            self, args, offset=0, limit=None,
            order=None, count=False,
            access_rights_uid=None
    ):
        context = self.env.context or {}
        if context == {'active_test': False} and self.env.uid == 1:
            for arg in args:
                if arg[0] == 'invoice_id.partner_id' and arg[1] == 'in':
                    return []

        return super(AccountInvoiceLine, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )

    @api.model
    def create(self, vals):
        # context = self.env.context or {}
        prod_obj = self.env['product.product']
        # certificate_obj = self.env['product.certificate']

        vals.update(self.get_readonly_fields_vals(vals))

        if vals.get('product_id', False):
            product = prod_obj.browse(vals['product_id'])
            vals['product_code'] = product.get_product_code()
            vals.update(product.get_product_packages_qty())
        if 'quantity' in vals.keys():
            vals['temp_quantity'] = vals['quantity']
        line = super(AccountInvoiceLine, self).create(vals)
        if vals.get('sale_order_line_ids', []):
            line.check_sale_orders()
        # if not context.get('stop_certificate_linking', False):
        #     if vals.get('certificate_id', False):
        #         ctx = context.copy()
        #         ctx['stop_certificate_linking'] = True
        #         certificate_obj.browse(vals['certificate_id']).with_context(ctx).write({
        #             'invoice_line_ids': [(4,line.id)]
        #         })
        if {'product_id', 'quantity'} & set(vals.keys()):
            line.update_total_weight()
        line.set_version()
        return line

    @api.multi
    def update_total_weight(self):
        context = self.env.context or {}
        if context.get('skip_weight_calculation', False):
            return
        invoices = self.env['account.invoice'].browse([])
        for line in self:
            line_total_weight = line.get_total_weight()
            if line.total_weight != line_total_weight:
                line.write({'total_weight': line_total_weight})
                invoices |= line.invoice_id
        invoices.update_total_weight()


    @api.multi
    def update_total_weight_with_sql(self):
        if self:
            weight_sql = '''
                UPDATE
                    account_invoice_line ail
                SET
                    total_weight = (
                        CASE
                            WHEN pp.product_type in ('fixed', 'variable') THEN ail.quantity
                            WHEN pp.product_type in ('unit') THEN ail.quantity * pp.weight
                        END
                    )
                FROM
                    product_product pp
                WHERE
                    pp.id = ail.product_id
                    AND ail.id in %s
                RETURNING 
                   invoice_id
            '''
            weight_where = (self._ids,)
            self.env.cr.execute(weight_sql, weight_where)
            invoice_ids = [inv_id[0] for inv_id in self.env.cr.fetchall()]
            self.env['account.invoice'].browse(list(set(invoice_ids))).update_weight_with_sql()
            self.invalidate_cache(fnames=['total_weight'], ids=list(self._ids))



    @api.multi
    def write(self, vals):
        context = self.env.context or {}
        prod_obj = self.env['product.product']
        certificate_obj = self.env['product.certificate']
        
        vals.update(self.get_readonly_fields_vals(vals))
        
        if vals.get('product_id', False):
            product = prod_obj.browse(vals['product_id'])
            vals['product_code'] = product.get_product_code()
            vals.update(product.get_product_packages_qty())
        if 'quantity' in vals.keys():
            vals['temp_quantity'] = vals['quantity']
        if not context.get('stop_certificate_linking', False):
            ctx = context.copy()
            ctx['stop_certificate_linking'] = True    
            for line in self:
                if vals.get('certificate_id', False):
                    inv_line = line.read(['certificate_id'])[0]
                    if inv_line['certificate_id'] and inv_line['certificate_id'][0]:
                        certificate_obj.browse(inv_line['certificate_id'][0]).with_context(ctx).write({
                            'invoice_line_ids': [(3,line.id)]
                        })
                    certificate_obj.browse(vals['certificate_id']).with_context(ctx).write({
                        'invoice_line_ids': [(4,line.id)]
                    })
            
        res  = super(AccountInvoiceLine, self).write(vals)
        
        if 'sale_order_line_ids' in vals.keys():
            self.check_sale_orders()
        if {'product_id', 'quantity'} & set(vals.keys()):
            self.update_total_weight()
#         if 'total_weight' in vals.keys():
#             self.mapped('invoice_id').update_total_weight()
        if 'sale_order_line_ids' in vals.keys():
            self.mapped('sale_order_line_ids').mapped('order_id').update_cash_amount()
        if INVOICE_LINE_VERSION_FIELD & set(vals.keys()):
            self.set_version()
        else:
            print('no timestamp', self, vals)
        return res    
    
    @api.model
    def get_pod_domain(self, obj):
        context = self.env.context or {}
        if context.get('for_raml', False):
            self.env.cr.execute('''
                SELECT
                    invoice_id
                FROM
                    stock_route_invoice_rel
                WHERE
                    route_id in (SELECT id FROM stock_route)
            ''')
            ids_res = self.env.cr.fetchall()
            ids = [id_res[0] for id_res in ids_res]
            return [('invoice_id','in', ids)]
        return []
    
    @api.multi
    def set_version(self):
        for inv_line in self:
            self._cr.execute('''
                UPDATE
                    account_invoice_line
                SET
                    id_version = %s
                WHERE id = %s
            ''', (get_local_time_timestamp(), inv_line.id))
        return True
    
    
    @api.multi
    def to_dict_for_pod_integration(self, obj):
        barcode_env = self.env['product.barcode']
#         route_env = self.env['stock.route']
        unit_barcode = ""
        box_barcode = ""
        if self.product_id:
            prod_id = self.product_id.id
            unit_barcode_obj = barcode_env.search([
                ('product_id','=',prod_id),
                ('type','=','unit'),
                ('barcode','!=',False)
            ], limit=1)
            if unit_barcode_obj:
                unit_barcode = unit_barcode_obj.barcode
            box_barcode_obj = barcode_env.search([
                ('product_id','=',prod_id),
                ('type','=','primary_packaging'),
                ('barcode','!=',False)
            ], limit=1)
            if box_barcode_obj:
                box_barcode = box_barcode_obj.barcode
                
#         route = self.invoice_id.
        
        container = self.get_container()
        
#         carrier_ids_external = set([])
#         if self.invoice_id:
#             routes = route_env.search([
#                 ('invoice_ids','in',self.invoice_id.id)
#             ])
#             for route in routes:
#                 if route.location_id and route.location_id.owner_id\
#                  and route.location_id.owner_id.external_customer_id:
#                     carrier_ids_external.add(route.location_id.owner_id.external_customer_id)
#         carrier_ids_external = list(carrier_ids_external)

        return {
            'documentLineId': self.external_invoice_line_id or str(self.id) or '',
            'itemCode': self.product_id and self.product_id.default_code or "",
            'itemEanCode': unit_barcode,
            'boxEanCode': box_barcode,
            'itemName': self.product_id and self.product_id.name or "",
            'unitOfMeasure': self.product_id and self.product_id.uom_id and\
                self.product_id.uom_id.name or "",
            'unitGrossWeight': self.product_id and self.product_id.weight or 0.0,
            'expectedQuantity': self.quantity or 0.0,
#             'carrierIds': carrier_ids_external,
            'deleted': False,
    #             'documentId': self.invoice_id and self.invoice_id.external_invoice_id or "",
            'document': self.invoice_id and self.invoice_id.to_dict_for_pod_integration('document') or {},
            'containerId': container and (container.id_external or str(container.id)) or '',
            'containerNo': container and (container.container_no or str(container.id)) or '',
            "id_version": self.id_version,
            'package': self.invoice_id and self.invoice_id.stock_package_id and True or False
        }
    


class AccountInvoiceContainer(models.Model):
    _name = 'account.invoice.container'
    _rec_name = 'id_external'
    _order = 'delivery_date desc'
    
    @api.model
    def get_child_container_invoices(self, container):
        invoice_ids = []
        if container.child_container_ids:
            for child_container in container.child_container_ids:
                invoice_ids += self.get_child_container_invoices(child_container)
        elif container.invoice_id and isinstance(container.invoice_id.id, ( int, long )):
            invoice_ids.append(container.invoice_id.id)
        return invoice_ids
    
    id_external = fields.Char('External ID', size=32, readonly=True)
    code = fields.Char('Code', size=64)
    line_ids = fields.One2many('account.invoice.container.line', 'container_id', "Container Lines")
    invoice_id = fields.Many2one('account.invoice', "Invoice", index=True)
    valid_until = fields.Date("Valid Until")
    container_no = fields.Char("Container No.", size=32)
    sscc = fields.Char("SSCC", size=32)
    parent_container_id = fields.Many2one('account.invoice.container', "Parent Container", index=True)
    child_container_ids = fields.One2many('account.invoice.container', 'parent_container_id', "Child Containers")
    invoice_ids = fields.Many2many(
        'account.invoice', 'container_invoice_rel', 'container_id', 'invoice_id', "Invoices",
#         compute='_get_invoice_ids', store=True
    )
#     it_is_parent_container = new_api_fields.Boolean("It's a Parent Container", default=False)
    height = fields.Float('Height', digits=(12, 3))
    weight = fields.Float('Weight', digits=dp.get_precision('Stock Weight'))
    factual_weight = fields.Float('Factual Weight', digits=dp.get_precision('Stock Weight'))
    type = fields.Many2one('stock.package.type', 'Type')
    package_id = fields.Many2one('stock.package', 'Package', readonly=True, index=True)
    state = fields.Selection([
        ('not_received', 'Not Received From Client'),
        ('canceled', 'Canceled'),
        ('registered', 'Registered'),
        ('in_terminal', 'In Terminal'),
        ('transported', 'Being Transported'),
        ('delivered', 'Delivered'),
        ('returned_to_supplier', 'Returned to Supplier'),
        ('lost', 'Lost'),
    ], 'State')
    planned_export = fields.Boolean('Planned Export', default=False)
    
    sender_id = fields.Many2one('res.partner', 'Owner', readonly=True)
    delivery_date = fields.Date('Delivery Date', readonly=True)
    buyer_id = fields.Many2one('res.partner', 'Delivery Client', readonly=True)
    buyer_address_id = fields.Many2one('res.partner', 'Delivery Address', readonly=True)
    internal_order_number = fields.Char("Package No", size=62, readonly=True)
    planned_collection = fields.Boolean('Planned Collection', readonly=True)
    returnend = fields.Boolean('Returned', default=False)
#     sale_id = new_api_fields.Many2one('sale.order', 'Sale', readonly=True)

    sale_ids = fields.Many2many(
        'sale.order', 'sale_order_container_rel', 'cont_id', 
        'sale_id', 'Sales'
    )
    buyer_name = fields.Char('Buyer Name', size=128, readonly=True)
    buyer_posid = fields.Char('Buyer POSID', size=128, readonly=True)
    sender_name = fields.Char('Sender Name', size=128, readonly=True)
    sender_posid = fields.Char('Sender POSID', size=128, readonly=True)
    delivery_route_ids = fields.Many2many('stock.route',
        'delivery_container_route_rel', 'container_id', 'route_delivery_id',  
        'Delivery Routes'
                                          )
    packet_type_id = fields.Many2one(
        'stock.package.type', 'Container Type',
    )
    owner_id = fields.Many2one('product.owner', 'Owner', readonly=True)
    route_received = fields.Boolean('Received', default=False)
    route_not_received = fields.Boolean('Not Received', default=False)
    not_received_filter = fields.Char('Feld to Filter Not Received Containers', readonly=True)
    picking_warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)
    destination_warehouse_id = fields.Many2one('stock.warehouse', 'Destination Warehouse', readonly=True)
    id_version = fields.Char('POD Version', size=128, readonly=True)
    volume = fields.Float("Volume", digits=(12, 4), readonly=True)
    length = fields.Float("Volume", digits=(12, 3))
    width = fields.Float("Width", digits=(12, 3))
    

    @api.multi
    def container_to_dict_for_res_integration(self):
        return {
            'containerId': self.id_external or str(self.id),
            # 'carrierId': ,
            'deleted': False,
            'containerNo': self.container_no or '',
            'shippingStatus': self.state == 'delivered' and 'shipped' or 'enroute',
            'blackBox': False,#negaunam tokių duomenų
            'requireScanOnPickUp': False,#negaunam tokių duomenų
            'deliveryDate': self.delivery_date or '',
            'parcelId': self.package_id and self.package_id.external_package_id or '',
            'parentContainerId': self.parent_container_id and (
                self.parent_container_id.id_external or str(self.parent_container_id.id)) or '',
            # 'routeId': '',#užpildyti išorėje
            # 'originWaypointId': '',#negaunam tokių duomenų
            # 'destinationWaypointId': '',#negaunam tokių duomenų
            # 'podId': '',#negaunam tokių duomenų
            'originWaypointInfo': {
                'waypointId': '',
                'carrierId': '',
                'position': '',
                'status': '',
                'estimatedArrivalTime': '',
                'estimatedVisitTime': '',
                'arrivalWindowFrom': '',
                'arrivalWindowTo': '',
                'deleted': '',
                'routeId': '',
                'placeId': '',
            },
            'destinationWaypointInfo':{
                'waypointId': '',
                'carrierId': '',
                'position': '',
                'status': '',
                'estimatedArrivalTime': '',
                'estimatedVisitTime': '',
                'arrivalWindowFrom': '',
                'arrivalWindowTo': '',
                'deleted': '',
                'routeId': '',
                'placeId': '',
            },
            'originPlaceId': self.sender_posid or '',
            'destinationPlaceId': self.buyer_posid or '',
        }

    @api.model
    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        context = self.env.context or {}
        ctx = context.copy()
        view_ref_key = view_type + '_view_ref'
        if view_ref_key in ctx.keys():
            view = self.env.ref(ctx[view_ref_key])
            if view.model != self._name:
                del ctx[view_ref_key]
        return super(AccountInvoiceContainer, self.with_context(ctx))._fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )


    @api.multi
    def _export_rows(self, fields):
        if self.env.user.company_id.user_faster_export:
            res = self.env['ir.model'].export_rows_with_psql(fields, self)
        else:
            res = super(AccountInvoiceContainer, self)._export_rows(fields)
        return res

    @api.multi
    def get_active_container_line(self, domain=[]):
        # Tas pats konteineris gali būti priskirtas prie kelių 
        # maršruto konteinerio eilučių(objektas sujungiantis maršrutą su konteineriu).
        # Ši funkcija grąžina einamąją maršruto konteinerio eilutę.
        
        src_env = self.env['stock.route.container']
        return src_env.search([('container_id','=',self.id),('current','=',True)] + domain)
    
    @api.multi
    def action_receive_not_received_container(self):
        # Po to, kai per maršruto gavimo wizardą pažymima, kad konteineris nėra gautas, 
        # galima iš konteinerio iškviesti šią funkciją. Iškviesti gali arba konteinerio gavėjas
        # arba siuntėjas.
        
        context = self.env.context or {}
        
        ctx_not_received = context.copy()
        ctx_not_received['not_received_containers'] = True
        ctx_allow_copy = context.copy()
        ctx_allow_copy['allow_to_copy_sale'] = True
        
        user_warehouse = self.env['res.users'].browse(self.env.uid).default_warehouse_id
        for container in self:
            if not container.route_not_received:
                continue
            if not self.with_context(ctx_not_received).search([('id','=',container.id)]):
                raise UserError(_('You can not get container(s%, ID: %s)') % (container.id_external, str(container.id)))
            route_container_line = container.get_active_container_line()
            route_transportation_task = route_container_line.get_transportation_task()
            if user_warehouse == route_transportation_task.warehouse_id:
                # konteineris grąžinamas į išsiuntimo sandėlį
                container.receive()
#                 
#                 default = {
#                     'route_id': False,
#                     'container_ids': [(6, 0, [container.id])],
#                     'shipping_warehouse_route_released': False,
#                     'route_state_received': False,
#                     'not_received': False,
#                     'intermediate_id': False,
#                     'show': True,
#                 }
#                 new_transportation_task = route_transportation_task.with_context(ctx_allow_copy).copy()
#                 route_transportation_task.write({
#                     'show': False,
#                     'received_by': user_warehouse.code,
#                     'sequence': 0
#                 })
            elif user_warehouse == route_transportation_task.shipping_warehouse_id:
                # konteineris grąžinamas tam sandėliui, kuris ir turėjo gauti
                container.receive()
            else:
                raise(_('TESTAVIMUI'))
        return True
            
    
    @api.multi
    def update_not_received_filter(self):
        # Konteinerio objekte atnaujinamas char laukelis, 
        # kuriame įrašomį sandėlių, kuriems reikia rodyti šį konteinerį, ID.
        # Šis laukelis bus naudojamas paieškoje, kad pagreitinti ją.
#         src_env = self.env['stock.route.container']
        for container in self:
            container_line = container.get_active_container_line()
            if container_line:
                if container_line.state == 'not_received':
                    warehouse_ids = [
                        container_line.warehouse_id.id, container_line.route_id.warehouse_id.id,
                        container_line.get_transportation_task().warehouse_id.id
                    ]
                    filter_str = 'id'.join([str(id) for id in warehouse_ids])
                    container.write({
                        'not_received_filter': 'id' + filter_str + 'id'
                    })
                else:
                    container.write({
                        'not_received_filter': ''
                    })
                    
    @api.onchange('route_not_received')
    def onchange_route_not_received(self):
        if self.route_not_received and self.route_received:
            self.route_received = False
     
    @api.onchange('route_received')
    def onchange_route_received(self):
        if self.route_not_received and self.route_received:
            self.route_not_received = False
    
    @api.multi
    def action_wizard_receive(self):
        # Funkcija kviečiama iš maršrute esančio wizardo, kuriame pažymima,
        # kurie konteineriai gauti. Funkcija perkrauna wizardą.
        
        self.write({'route_received': True, 'route_not_received': False})
        return {
            "type": "ir.actions.dialog_reload",
        }
        
    @api.multi
    def action_wizard_not_receive(self):
        # Funkcija kviečiama iš maršrute esančio wizardo, kuriame pažymima,
        # kurie konteineriai nebuvo gauti. Funkcija perkrauna wizardą.
        for container in self:
            container.write({
                'route_received': False,
                'route_not_received': True,
                'destination_warehouse_id': container.get_active_container_line().get_transportation_task().shipping_warehouse_id.id
            })
        return {
            "type": "ir.actions.dialog_reload",
        }
        
    @api.model
    def get_total_weight(self):
        weight = 0.0
        for container in self:
            weight += container.weight
        return weight

    @api.model
    def search_placeholder_container(self, vals):
        if vals.get('package_id', False):
            search_sql = '''
                SELECT
                    cont.id
                FROM
                    account_invoice_container cont
                    JOIN sale_order_container_rel rel on (rel.cont_id = cont.id)
                    JOIN sale_order so on (so.id=rel.sale_id)
                    JOIN stock_package sp on (sp.internal_order_number=so.name)
                WHERE
                    so.delivery_type = 'collection'
                    AND so.placeholder_for_route_template = True
                    AND sp.id = %s
                LIMIT 1
            '''
            search_where = (vals['package_id'],)
            self.env.cr.execute(search_sql, search_where)
            cont_id, = self.env.cr.fetchone() or (False,)
            if cont_id:
                return self.env['account.invoice.container'].browse(cont_id)
            return self.env['account.invoice.container']


    @api.model
    def create_container(self, vals):
        interm_obj = self.env['stock.route.integration.intermediate']

        containers = self.search([('id_external','=',vals['id_external'])])
        if not containers:
            containers = self.search_placeholder_container(vals)
        if containers:
            cont_vals = {}
        else:
            cont_vals = self.default_get(self._fields)
        
        cont_vals.update(vals)
        
        if containers:
            container = containers[0]
            interm_obj.remove_same_values(containers[0], cont_vals)
            if cont_vals:
                containers.write(cont_vals)
            
        else:
            cont_vals['state'] = 'in_terminal'
            container = self.create(cont_vals)
        self.env.cr.commit()       
        return container.id
    
    @api.multi
    def update_containers(self):
        return self.mapped('package_id').update_containers(self)


    @api.multi
    def _get_invoice_ids(self):
        for container in self:
            invoice_ids = self.get_child_container_invoices(container)
            invoice_ids += container.invoice_ids.ids
            invoice_ids = list(set(invoice_ids))
            
            super(AccountInvoiceContainer, container).write({
                'invoice_ids': [(6,0,invoice_ids)]
            })
            
        return True
    
    @api.multi
    def get_routes(self):
        container_line_env = self.env['stock.route.container']
        container_lines = container_line_env.search([
            ('container_id','in',self.mapped('id'))
        ])
        return container_lines.mapped('route_id')
    
    @api.multi
    def calc_volume(self):
        for container in self:
            length = self.length or 1.0
            heigth = self.heigth or 1.0
            width = self.width or 1.0
            
            self._cr.execute('''
                UPDATE
                    account_invoice_container
                SET
                    volume = %s
                WHERE id = %s
            ''', (length*heigth*width, container.id))
        return True      
        
    @api.multi
    def write(self, vals):
        res = super(AccountInvoiceContainer, self).write(vals)
        if 'package_id' in vals.keys():
            self.update_containers()
            if 'state' not in vals.keys():
                self.mapped('package_id').update_state()
        if 'state' in vals.keys():
            self.mapped('package_id').update_state()
        if 'weight' in vals.keys():
            self.mapped('package_id').update_weight()
            self.mapped('delivery_route_ids').update_weight()
        if 'invoice_id' in vals.keys()\
            or 'children_container_ids' in vals.keys() \
        :
            self._get_invoice_ids() 
#         for container in self:
#             container.set_version()
        if 'heigth' in vals.keys() or 'length' in vals.keys()\
         or 'width' in vals.keys():
            self.calc_volume()
        
        self.set_version()
        
        return res
    
    @api.model
    def create(self, vals):
        if 'state' not in vals.keys():
            vals['state'] = 'in_terminal'
        vals['id_version'] = get_local_time_timestamp()
        new_container = super(AccountInvoiceContainer, self).create(vals)
        new_container._get_invoice_ids()
        if 'package_id' in vals.keys():
            new_container.update_containers()
        if 'package_id' in vals.keys():
            new_container.package_id.update_state()
        self.calc_volume()
        return new_container
        
    @api.multi
    def receive(self, route_id=False):
        # Funkcija iškviečiama, kai naudotojas pažymi, kad konteineris yra gautas.
         
        cont_line_env = self.env['stock.route.container']
        user_env = self.env['res.users']
        user = user_env.browse(self.env.uid)
        if route_id:
            cont_lines = cont_line_env.search([
                ('route_id','=',route_id),
                ('container_id','in',self.mapped('id'))
            ])
        else:
            cont_lines = cont_line_env.browse()
            for container in self:
                cont_lines += container.get_active_container_line()
        cont_lines.write({'state': 'received', 'warehouse_id': user.default_warehouse_id.id})
    
    @api.multi
    def not_receive(self, route_id=False):
        # Funkcija iškviečiama, kai naudotojas pažymi, kad konteineris nėra gautas.
        cont_line_env = self.env['stock.route.container']
        user_env = self.env['res.users']
        user = user_env.browse(self.env.uid)
        
        if route_id:
            cont_lines = cont_line_env.search([
                ('route_id','=',route_id),
                ('container_id','in',self.mapped('id'))
            ])
        else:
            cont_lines = self.browse()
            for container in self:
                cont_lines += container.get_active_container_line()
        cont_lines.write({'state': 'not_received', 'warehouse_id': user.default_warehouse_id.id})

    @api.model
    def get_search_domain(self, args):
        context = self._context or {}
        if context.get('search_containers_by_warehouse', False):
            user = self.env['res.users'].browse(self.env.uid)
            available_wh_ids = user.get_current_warehouses().mapped('id')
            if ('picking_warehouse_id','in',available_wh_ids) not in args:
                args.append(('picking_warehouse_id','in',available_wh_ids))


    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context or {}
        
        # atfiltruojami konteineriai kurie buvo negauti naudotojo sandėlio
        if context.get('not_received_containers'):
            user = self.env['res.users'].browse(self.env.uid)
            if not user.default_warehouse_id:
                raise UserError(_('To open not received containers you need to select warehouse.'))
            wh_id = user.default_warehouse_id.id
            args.append(('not_received_filter','like','%id'+str(wh_id)+'id%'))
 
        return super(AccountInvoiceContainer, self).search(args, offset, limit, order, count=count)

    @api.model
    def _search(
        self, args, offset=0, limit=None,
        order=None, count=False,
        access_rights_uid=None
    ):
        self.get_search_domain(args)
        return super(AccountInvoiceContainer, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )

    @api.multi
    def remove_from_system(self):
        self.sudo().unlink()
    
#     def can_delete_invoice(self, date_until=None):
#         if date_until is None:
#             user = self.env['res.users'].browse(self.env.uid)
#             company = user.company_id
#             days_after = company.delete_containers_after
#             today = datetime.datetime.now()
#             date_until = (today - datetime.timedelta(days=days_after)).strftime('%Y-%m-%d %H:%M:%S')        
#         if not (self.delivery_date and self.delivery_date < date_until or not self.delivery_date) and not self.delete_containers_after < date_until:
#             return False
#         return True
            
    
    @api.model
    def cron_delete_old_containers(self):
        # Krono paleidžiama funkcija, kuri trina senas sąskaitas faktūras        
        
        user = self.env['res.users'].browse(self.env.uid)
        company = user.company_id
        log = company.log_delete_progress or False
        days_after = company.delete_containers_after
        date_field = company.get_date_field_for_removing_object(self._name)
        _logger.info('Removing old Containers (%s days old) using date field \'%s\'' % (str(days_after), date_field))

        today = datetime.datetime.now()
        date_until = today - datetime.timedelta(days=days_after)

        containers = self.search([
            (date_field,'<',date_until.strftime('%Y-%m-%d %H:%M:%S')),
        ])
        _logger.info('Removing old Containers: found %s records' % str(len(containers)))
        ids_to_unlink = containers.mapped('id')
        if log:
            all_containers_count = float(len(containers))
            i = 0
            last_log = 0
        # for container in containers:
        for container_ids in [ids_to_unlink[ii:ii+50] for ii in range(0, len(ids_to_unlink), 50)]:
            try:
                # container.remove_from_system()
                # self.env.cr.commit()
                self.browse(container_ids).remove_from_system()
                self.env.cr.commit()
                if log:
                    i += 1
                    if last_log < int((i / all_containers_count)*100):
                        last_log = int((i / all_containers_count)*100)
                        _logger.info('Container delete progress: %s / %s' % (str(i), str(int(all_containers_count))))
            except Exception as e:
                err_note = 'Failed to delete container(ID: %s): %s \n\n' % (str(container_ids), tools.ustr(e),)
                trb = traceback.format_exc() + '\n\n'
                _logger.info(err_note + trb)
                
    @api.multi
    def name_get(self):
        res = []
        for container in self:
            name_parts = []
            if container.id_external:
                name_parts.append(container.id_external)
            if container.code:
                name_parts.append(container.code)
            if name_parts:
                name = "_".join(name_parts)
            else:
                name = "-"
            res.append((container.id, name))
        return res 
    
    #Metodas kvieciamas is JS, paduodant netvarkingus domainus, o grazinami skirtingi galimi savininkai
    def get_avail_owners(self, domains, action_domain=False, action_context=False):
        context = action_context or {}
        normalized_domain = []
        for domain_ele in domains:
            if isinstance(domain_ele, dict):
                if domain_ele.get('__domains', False):
                    for cmplx_domain_ele in domain_ele['__domains']:
                        if len(cmplx_domain_ele) == 1:
                            normalized_domain.append(cmplx_domain_ele[0])
                        elif len(cmplx_domain_ele) == 3:
                            normalized_domain.append(cmplx_domain_ele)
                        else:
                            continue
            elif isinstance(domain_ele, list):
                normalized_domain.append(domain_ele[0])
            else:
                continue

        if action_domain:
            normalized_domain += action_domain
            
        additional_domain = []
        self.with_context(context).get_search_domain(additional_domain)
        
        normalized_domain += additional_domain
        
        query = self._where_calc(normalized_domain)
        from_clause, where_clause, where_clause_params = query.get_sql()
        where_str = where_clause and (" WHERE %s" % where_clause) or ''
        query_str = 'SELECT DISTINCT(owner_id) FROM account_invoice_container %s ORDER BY owner_id' % where_str

        self.env.cr.execute(query_str, where_clause_params)
        res = self.env.cr.fetchall()
        owners = []
        
        for owner_id_tuple in res:
            if owner_id_tuple[0]:
                owner_id = owner_id_tuple[0]
                self.env.cr.execute('SELECT owner_code,name FROM product_owner WHERE id = %s' % owner_id)
                owner_code_sql_res = self.env.cr.fetchone()
                
                owner_code, owner_name = owner_code_sql_res
                if owner_name:
                    owner_str = "%s - %s" % (owner_code, owner_name)
                else:
                    owner_str = owner_code
                
                if (owner_code, owner_str) not in owners:
                    owners.append((owner_code, owner_str))
        
        owners = sorted(owners, key=lambda tup: tup[1])
        return owners
    
    @api.model
    def get_pod_domain(self, obj):
        return []
    
    @api.multi
    def set_version(self):
        for container in self:
            self._cr.execute('''
                UPDATE
                    account_invoice_container
                SET
                    id_version = %s
                WHERE id = %s
            ''', (get_local_time_timestamp(), container.id))
        return True
    
    @api.multi
    def to_dict_for_pod_integration(self, obj):
        stock_container_env = self.env['stock.route.container']
        stock_containers = stock_container_env.search([
            ('container_id','=',self.id),
        ])
        route_ids = []
        
        carrier_ids_external = set([])
        if stock_containers:
            for stock_container in stock_containers:
                route = stock_container.route_id
                if route.state == 'draft':
                    continue
                if route:
                    route_ids.append(route.id)
                    if route.location_id and route.location_id.owner_id\
                     and route.location_id.owner_id.external_customer_id:
                        carrier_ids_external.add(route.location_id.owner_id.external_customer_id)
        carrier_ids_external = list(carrier_ids_external)
        
        delivery_date = self.delivery_date
                
        if self.package_id:
            parcel = self.package_id.external_package_id or False
            blackbox = True
        else:
            parcel = False
            blackbox = False
            
        parent_container = self.parent_container_id and (
            self.parent_container_id.id_external or str(self.parent_container_id.id)
        ) or False
        
        res = {
            'containerId': self.id_external or str(self.id),
            'carrierIds': carrier_ids_external,
            'deleted': False,
            'containerNo': self.container_no or '',
            'shippingStatus': self.state == 'delivered' and 'shipped' or 'enroute',
            'blackBox': blackbox,
            'routeIds': list(set(route_ids)),
            'originPlaceId': self.sender_posid or "",
            'destinationPlaceId': self.buyer_posid or "",
            "id_version": self.id_version,
        }
        if delivery_date:
            res['deliveryDate'] = delivery_date
        if parcel:
            res['parcelId'] = parcel
        if parent_container:
            res['parentContainerId'] = parent_container    
            
        
        return res
    
class AccountInvoiceContainerLine(models.Model):
    _name = 'account.invoice.container.line'
    _rec_name = 'invoice_line_id'
    
#     @api.depends('invoice_line_id')
#     def _get_invoice_line_product(self):
#         for container_line in self:
#             container_line.update({
#                 'product_id': container_line.invoice_line_id.product_id or False
#             })

    @api.onchange('invoice_line_id')
    def onchange_invoice_line(self):
        if self.invoice_line_id and self.invoce_line_id.product_id:
            self.product_id = self.invoice_line_id.product_id.id
            self.product_code = self.invoice_line_id.product_id.default_code
            self.invoice_line_ids = self.invoice_line_ids.ids + [self.invoice_line_id.id]
    
    invoice_line_id = fields.Many2one('account.invoice.line', "Invoice Line", index=True)
    product_id = fields.Many2one(
        'product.product', 'Product'
#         , compute='_get_invoice_line_product', store=True
    )
    product_code = fields.Char("Product Code")
    qty = fields.Float('Quantity', digits=dp.get_precision('Product Unit of Measure'))
#     lot_id = fields.Many2one('stock.production.lot', 'Lot')
    container_id = fields.Many2one('account.invoice.container', "Container")
    uom_id = fields.Many2one('product.uom', 'UoM')
    related_product_id = fields.Many2one(
        'product.product', 'Related Product', readonly=True
    )
    location_id = fields.Many2one('stock.location', 'Location')
    
    serial_ids = fields.One2many('product.stock.serial', 'container_line_id', "Serial Numbers")
    
#------ FIELDAI CLAIMSU KURIMUI

    min_expiry_date = fields.Date("Min. Expiry Date")
    expiry_date = fields.Date("Expiry Date")
    ordered = fields.Selection([
        ('yes', _('YES')),
        ('no', _('NO')),
    ], "Ordered", default='no')
    got_from_wms = fields.Selection([
        ('yes', _('YES')),
        ('no', _('NO')),
    ], "Got From WMS", default='no')
    invoice_line_ids = fields.Many2many(
        'account.invoice.line', 'invoice_line_container_line_rel',
        'container_line_id', 'invoice_line_id', "Invoice Lines"
    )




# TAROS EILUTES
# class AccountInvoicePackageLine(models.Model):
#     _name = 'account.invoice.package_line'
#     _rec_name = 'product_id'
#       
#     @api.depends('qty', 'price_unit')
#     def _compute_total(self):
#         for line in self:
#             line.update({
#                 'price_total': (line.qty or 0.0) * (line.price_unit or 0.0)
#             })
#       
#     product_id = new_api_fields.Many2one(
#         'product.product', 'Package', domain=[('type_of_product','=', 'package')]
#     )
#     qty = new_api_fields.Float('Quantity', digits=dp.get_precision('Product Unit of Measure'))
#     price_unit = new_api_fields.Float(string='Unit Price', digits=dp.get_precision('Product Price'))
#     price_total = new_api_fields.Monetary(compute='_compute_total', string='Total', store=True)
#     invoice_id = new_api_fields.Many2one('account.invoice', "Invoice")
#     currency_id = new_api_fields.Many2one(related='invoice_id.currency_id', store=True, string='Currency', readonly=True)

# class AccountInvoiceTax(models.Model):
#     _inherit = 'account.invoice.tax'
#     
#     amount_wt_vat_discount = new_api_fields.Float("Amount Without VAT & Discount") 
#     amount_wt_vat = new_api_fields.Float("Amount Without VAT")    


class AccountTax(models.Model):
    _inherit = 'account.tax'
    
    @api.model
    def get_taxes(self, amount):
        sale_taxes = self.search([
            ('amount','=',amount),
            ('type_tax_use','=','sale')
        ])
        if not sale_taxes:
            sale_tax_vals = self.default_get(self._fields)
            sale_tax_vals['amount'] = amount
            sale_tax_vals['type_tax_use'] = 'sale'
            sale_tax_vals['name'] = str(amount) + ' %'
            sale_tax = self.create(sale_tax_vals)
        else:
            sale_tax = sale_taxes[0]
            
        purchase_taxes = self.search([
            ('amount','=',amount),
            ('type_tax_use','=','purchase')
        ])
        if not purchase_taxes:
            purchase_tax_vals = self.default_get(self._fields)
            purchase_tax_vals['amount'] = amount
            purchase_tax_vals['type_tax_use'] = 'purchase'
            purchase_tax_vals['name'] = str(amount) + ' %'
            purchase_tax = self.create(purchase_tax_vals)
        else:
            purchase_tax = purchase_taxes[0]
        
        return sale_tax, purchase_tax