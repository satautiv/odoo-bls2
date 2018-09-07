# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.api import Environment

# import time

DOCUMENT_TYPE_MAPPER = {
    'route_transfer_to_driver': 'config_sanitex_delivery.drivers_packing_transfer_act',
    'route_return_from_driver': 'config_sanitex_delivery.drivers_packing_transfer_act',
    'internal_transfer_to_driver': 'config_sanitex_delivery.tare_to_driver_act',
    'internal_return_from_driver': 'config_sanitex_delivery.driver_return_act',
    'route_transfer_to_client': 'config_sanitex_delivery.stock_packing_report',
    'internal_transfer_to_client': 'config_sanitex_delivery.stock_packing_report',
}


class DocumentType(models.Model):
    _name = 'document.type'
    _description = 'Document Type'

    name = fields.Char('Name', required=True, size=256, translate=True)
    code = fields.Char('Code', required=True, size=256)
    do_not_show = fields.Boolean('Do Not Show', default=False)

    _sql_constraints = [
        ('document_type_code_uniq', 'unique(code)', 'Document type with same code already exists !')
    ]

    @api.model
    def get_document_type(self, operation_type=None):
        if operation_type is None:
            return DOCUMENT_TYPE_MAPPER
        else:
            return DOCUMENT_TYPE_MAPPER.get(operation_type, operation_type)

    @api.model
    def generate_document_types(self):
        rep_env = self.env['ir.actions.report']
        lang_env = self.env['res.lang']
        reports = rep_env.search([
            ('keep_log','=',True)
        ])
        languages = lang_env.search([])
        for report in reports:
            report_no_lang = rep_env.with_context(lang=False).browse(report.id)
            if not self.search([
                ('code','=',report_no_lang.report_name)
            ]):
                document_type = self.create({
                    'name': report_no_lang.name,
                    'code': report_no_lang.report_name,
                    'do_not_show': False
                })
                for lang in languages:
                    report_lang = rep_env.with_context(lang=lang.code).browse(report.id)
                    document_type.with_context(lang=lang.code).write({'name': report_lang.name})

    @api.model
    def get_next_number_by_code(self, document_type_code, warehouse=None, owner=None):
        sql = '''
            SELECT
                id
            FROM
                document_type
            WHERE
                code = %s
            LIMIT 1
        '''
        where = (document_type_code,)
        self.env.cr.execute(sql,where)
        document_types = self.env.cr.fetchall()
        if not document_types:
            raise UserError(_('There are no document type with code %s') % document_type_code)
        document_type = self.browse(document_types[0][0])
        res = document_type.get_next_number(warehouse, owner)
        return res

    @api.multi
    def get_next_number(self, warehouse=None, owner=None):
        if not self.id:
            return
        settings_env = self.env['document.type.settings']
        sql = '''
            SELECT
                id
            FROM
                document_type_settings
            WHERE
                document_type_id = %s
            LIMIT 1
        '''
        where = (self.id,)
        self.env.cr.execute(sql,where)
        document_type_settings = self.env.cr.fetchall()
        if not document_type_settings:
            raise UserError(_('There are no document type with code %s') % self.code)
        settings = settings_env.browse(document_type_settings[0][0])
        return settings.get_next_number(warehouse, owner)

class DocumentTypeSettings(models.Model):
    _name = 'document.type.settings'
    _description = 'Document Type Settings'

    _rec_name = 'document_type_id'

    @api.model
    def _get_document_sequence_types(self):
        return [
            ('wh',_('By Warehouse')),
            ('own',_('By Owner')),
        ]

    document_type_id = fields.Many2one('document.type', 'Documet', required=True)
    sequence_by = fields.Selection(_get_document_sequence_types, 'Sequence Managed', required=True)

    _sql_constraints = [
        ('document_seq_by_uniq', 'unique(document_type_id)', 'Duplicate line. Sequence type for document must be unique !')
    ]

    @api.multi
    def get_next_number(self, warehouse=None, owner=None):
        line_env = self.env['document.type.settings.line']
        sql = '''
            SELECT
                sequence_by
            FROM
                document_type_settings
            WHERE
                id = %s
            LIMIT 1
        '''
        where = (self.id,)
        self.env.cr.execute(sql,where)
        document_type_settings = self.env.cr.fetchall()
        sequence_by = document_type_settings[0][0]

        sql = '''
            SELECT
                l.id
            FROM
                document_type_settings_line l
                JOIN doc_setting_doc_setting_line_rel rel on (rel.line_id=l.id)
                JOIN document_type_settings set on (set.id=rel.setting_id)
            WHERE
                set.id = %s 
        '''
        if sequence_by == 'wh':
            if not warehouse:
                raise UserError(_('Warehouse is required to get next number for document %s (code: %s)') % (
                    self.document_type_id.name, self.document_type_id.code
                ))
            sql_where = ''' AND l.warehouse_id = %s '''
            where = (self.id, warehouse.id)
        elif sequence_by == 'own':
            if not owner:
                raise UserError(_('Owner is required to get next number for document %s (code: %s)') % (
                    self.document_type_id.name, self.document_type_id.code
                ))
            sql_where = ''' AND l.owner_id = %s '''
            where = (self.id, owner.id)
        sql += sql_where
        self.env.cr.execute(sql, where)
        line_results = self.env.cr.fetchall()
        line_ids = [line_result[0] for line_result in line_results]
        line = line_env.browse(line_ids)

        if not line:
            raise UserError(_('%s is missing numbering sequence for document: %s.') % (
                (self.sequence_by == 'wh' and (_('Warehouse') + ' ' + warehouse.name)) or (self.sequence_by == 'own' and (_('Product owner') + ' ' + owner.name)),
                self.document_type_id.name
            ))
        return line.get_next_number()

class DocumentTypeSettingsLine(models.Model):
    _name = 'document.type.settings.line'
    _description = 'Document Settings Line for Sequence'

    name = fields.Char('Name', size=256, translate=True)
    document_type_settings_ids = fields.Many2many(
        'document.type.settings', 'doc_setting_doc_setting_line_rel', 'line_id', 'setting_id', 'Documents'
    )
    owner_id = fields.Many2one('product.owner', 'Owner', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)
    sequences_ids = fields.One2many('ir.sequence', 'document_setting_line_id', 'Sequences')
    active_lines = fields.Integer('Active Lines', readonly=True)
    inactive_lines = fields.Integer('Inactive Lines', readonly=True)
    active = fields.Boolean('Active', default=True)

    @api.multi
    def check_document_value(self):
        # Patikrinama ar dokumentui nėra jau sukurtos kitos numeravimo
        # nustatymų eilutės tame sandėlyje arba savininke.
        for setting_line in self:
            if (setting_line.warehouse_id or setting_line.owner_id) and setting_line.document_type_settings_ids:
                domain = [('id','!=',setting_line.id)]
                object_name = ''
                if setting_line.warehouse_id:
                    domain.append(('warehouse_id','=',setting_line.warehouse_id.id))
                    object_name = _('for warehouse') + ' ' + setting_line.warehouse_id.name
                elif setting_line.owner_id:
                    domain.append(('owner_id','=',setting_line.owner_id.id))
                    object_name = _('for owner') + ' ' + setting_line.owner_id.name
                all_lines = self.search(domain)
                for document_type in setting_line.document_type_settings_ids:
                    for line in all_lines:
                        if document_type in line.document_type_settings_ids:
                            raise UserError(_('Document numbering line with document "%s" %s already exists. Line name: %s.') % (
                                document_type.document_type_id.name, object_name, line.name
                            ))

    @api.multi
    def get_next_number(self):
        with Environment.manage():
            new_cr = self.pool.cursor()
            try:
                new_self = self.with_env(self.env(cr=new_cr))

                seq_env = new_self.env['ir.sequence']
                sql = '''
                    SELECT
                        id
                    FROM
                        ir_sequence
                    WHERE
                        document_setting_line_id = %s
                        AND finished = False
                    LIMIT 1
                '''
                where = (new_self.id,)
                new_self.env.cr.execute(sql,where)
                ir_sequences = new_self.env.cr.fetchall()
                if not ir_sequences:
                    raise UserError(_('%s for document %s does not have any active sequences.') % (
                        ((new_self.owner_id and (_('Numbering line in product owner') + ' ' + new_self.owner_id.name)) or
                        (new_self.warehouse_id and (_('Numbering line in warehouse') + ' ' + new_self.warehouse_id.name))), new_self.name
                    ))
                sequence = seq_env.browse(ir_sequences[0][0])
                new_cr.commit()
            except:
                new_cr.close()
                raise
            number = sequence.next_by_id()
            new_cr.close()

        return number

    @api.multi
    def get_name(self):
        line_name = ''
        if self.document_type_settings_ids:
            line_name = ', '.join(self.document_type_settings_ids.mapped('document_type_id').mapped('name'))
        return line_name

    @api.multi
    def update_active_lines(self):
        for line in self:
            vals = {
                'inactive_lines': len(line.sequences_ids.filtered('finished'))
            }
            vals['active_lines'] = len(line.sequences_ids) - vals['inactive_lines']
            line.write(vals)

    @api.multi
    def update_name(self):
        lang_env = self.env['res.lang']
        languages = lang_env.search([])
        for line in self:
            line_no_lang = self.with_context(lang=False).browse(line.id)
            line_no_lang.with_context(lang=False).write({'name': line_no_lang.get_name()})
            for language in languages:
                line_lang = self.with_context(lang=language.code).browse(line.id)
                line_lang.with_context(lang=language.code).write({'name': line_lang.get_name()})

    @api.model
    def create(self, vals):
        if 'active' not in vals.keys():
            vals['active'] = True
        line = super(DocumentTypeSettingsLine, self).create(vals)
        line.check_document_value()
        line.update_name()
        return line

    @api.multi
    def write(self, vals):
        res = super(DocumentTypeSettingsLine, self).write(vals)
        if {'document_type_settings_ids', 'warehouse_id', 'owner_id'} & set(vals):
            self.check_document_value()
        if 'document_type_settings_ids' in vals.keys():
            self.update_name()
        return res

class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    document_setting_line_id = fields.Many2one('document.type.settings.line', 'Document Setting Line', readonly=True)
    priority = fields.Integer('Priority')
    last_number = fields.Integer('Last Number')
    left_qty = fields.Integer('Numbers Left')
    name = fields.Char(required=False)
    finished = fields.Boolean('Finished', readonly=True)

    @api.multi
    def check_priority(self):
        for sequence in self:
            if sequence.document_setting_line_id:
                if self.search([
                    ('document_setting_line_id','=',sequence.document_setting_line_id.id),
                    ('priority','=',sequence.priority)
                ], count=True) > 1:
                    raise UserError(_('Sequence with priority %s already exists for document type %s') % (
                        str(sequence.priority), sequence.document_setting_line_id.name
                    ))

    @api.multi
    def check_number_validity(self):
        # Patikrinimas ar numeracija su kažkokiu priešdeliu nėra jau
        # sukurta kitam to sandėlio arba savininko dokumentui
        for sequence in self:
            if sequence.prefix and sequence.document_setting_line_id:
                domain = [
                    ('prefix','=',sequence.prefix),
                    ('document_setting_line_id','!=',sequence.document_setting_line_id.id)
                ]
                object_name = ''
                if sequence.document_setting_line_id.warehouse_id:
                    domain.append(('document_setting_line_id.warehouse_id','=',sequence.document_setting_line_id.warehouse_id.id))
                    object_name = _('for warehouse') + ' ' + sequence.document_setting_line_id.warehouse_id.name
                elif sequence.document_setting_line_id.owner_id:
                    domain.append(('document_setting_line_id.owner_id','=',sequence.document_setting_line_id.owner_id.id))
                    object_name = _('for owner') + ' ' + sequence.document_setting_line_id.owner_id.name
                duplicates = self.search(domain)
                if duplicates:
                    raise UserError(_('Sequence with prefix "%s" already exists %s for document "%s".') % (
                        sequence.prefix, object_name, duplicates[0].document_setting_line_id.name
                    ))

    @api.model
    def create(self, vals):
        number_next_actual = False
        if vals.get('number_next_actual', False):
            number_next_actual= vals['number_next_actual']
        sequence = super(IrSequence, self).create(vals)
        sequence.check_priority()
        sequence.check_number_validity()
        self.env.cr.commit()
        if number_next_actual:
            sequence.write({'number_next_actual': number_next_actual})
        sequence.update_sequence()
        sequence.document_setting_line_id.update_active_lines()
        return sequence

    @api.multi
    def write(self, vals):
        for sequence in self:
            if 'prefix' in vals.keys():
                if vals['prefix'] != sequence.prefix:
                    raise UserError(_('You can\'t change series for sequence(%s). (%s --> %s)') % (
                        sequence.document_setting_line_id.name, sequence.prefix, vals['prefix']
                    ))
            if 'number_next_actual' in vals.keys():
                if vals['number_next_actual'] < sequence.number_next_actual:
                    raise UserError(_('Next number can\'t be lower than before(sequence: %s). (%s < %s)') % (
                        sequence.document_setting_line_id.name, str(vals['number_next_actual']), str(sequence.number_next_actual)
                    ))

        res = super(IrSequence, self).write(vals)
        if {'prefix', 'document_setting_line_id'} & set(vals):
            self.check_number_validity()
        if {'priority', 'document_setting_line_id'} & set(vals):
            self.check_priority()
        if {'last_number', 'number_next_actual'} & set(vals):
            self.env.cr.commit()
            self.update_sequence()
        if {'finished', 'document_setting_line_id'} & set(vals):
            self.mapped('document_setting_line_id').update_active_lines()
        return res

    @api.onchange('last_number','number_next_actual')
    def on_change_last_number(self):
        if self.last_number:
            self.padding = len(str(self.last_number))
            self.left_qty = (self.last_number - self.number_next_actual + 1 > 0) and \
                (self.last_number - self.number_next_actual + 1) or 0

    @api.multi
    def update_sequence(self, next_number=None):
        if next_number is None:
            with Environment.manage():
                new_cr = self.pool.cursor()
                sequences = self.with_env(self.env(cr=new_cr))
                sequences.invalidate_cache(fnames=['last_number', 'number_next_actual'], ids=list(sequences._ids))

                for sequence in sequences:
                    vals = {
                        'left_qty': (sequence.last_number - sequence.number_next_actual + 1 > 0) and
                            (sequence.last_number - sequence.number_next_actual + 1) or 0,
                        'finished': sequence.number_next_actual > sequence.last_number
                    }
                    if sequence.last_number and sequence.last_number > 0:
                        vals['padding'] = len(str(sequence.last_number))
                    try:
                        sequence.write(vals)
                        if vals['finished']:
                            sequence.document_setting_line_id.update_active_lines()
                        new_cr.commit()
                    except:
                        pass
                new_cr.close()
        else:
            with Environment.manage():
                try:
                    if self._ids:
                        new_cr = self.pool.cursor()
                        number = int(next_number)
                        sql = '''
                            UPDATE
                                ir_sequence
                            SET
                                left_qty = (
                                    CASE
                                        WHEN last_number - %s > 0 THEN last_number - %s
                                        WHEN last_number - %s <= 0 THEN 0
                                    END
                                ),
                                finished = %s >= last_number
                            WHERE
                                id in %s
                            RETURNING
                                finished
                        '''
                        sql_where = (number, number, number, number, tuple(self._ids))
                        new_cr.execute(sql, sql_where)
                        results = new_cr.fetchall()
                        for result in results:
                            if result[0]:
                                sequences = self.with_env(self.env(cr=new_cr))
                                sequences.mapped('document_setting_line_id').update_active_lines()
                                break
                        new_cr.commit()
                except:
                    pass
                new_cr.close()



    @api.multi
    def next_by_id(self):
        number = super(IrSequence, self).next_by_id()
        self.update_sequence(next_number=number[-self.padding:])
        return number
