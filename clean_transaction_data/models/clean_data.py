# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Ecosoft Co., Ltd. (http://ecosoft.co.th).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import datetime

from openerp import fields, models, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning


class res_data_clean_line(models.Model):
    _name = 'res.data.clean.line'
    
    query = fields.Char('PSQL Query', required=True)
    
class res_data_clean(models.Model):
    _name = 'res.data.clean'
    _inherit = ['mail.thread']
    
    name = fields.Char('Name', required=True)
    date = fields.Date('Date', default=fields.Date.today() )
    resp_user_id = fields.Many2one('res.users', string='Responsible User', default=lambda self:self.env.uid, readonly=True)
    processed_user_id = fields.Many2one('res.users', string='Run By', readonly=True)
    process_date = fields.Date('Run Date', readonly=True)
    state = fields.Selection([('draft', 'Darft'),
                              ('confirm', 'Confirmed'),
                              ('process', 'Processed')], string='State', default = 'draft', track_visibility='onchange')
    query_line_ids = fields.Many2many('res.data.clean.line', 'res_data_clean_line_rel', 'line_id1', 'line_id2', string='Lines')
    
    @api.multi
    def confirm(self):
        if not self.query_line_ids:
            raise Warning(_('Can not confirm record without queries.'))
        self.state = 'confirm'
    
    @api.multi
    def run_query(self):
        self.state = 'process'
        self.processed_user_id = self.env.uid
        self.process_date = datetime.today()
        for line in self.query_line_ids:
            sql_query = line.query
            try:
                self._cr.execute(sql_query)
            except:
                raise Warning(_('Please Check the query: %s' %(sql_query)))
        
    @api.multi
    def reset_to_draft(self):
        self.state = 'draft'
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
    
