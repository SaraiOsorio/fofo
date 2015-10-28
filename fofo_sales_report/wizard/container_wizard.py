# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015-Today Ecosoft Co., Ltd. (http://Ecosoft.co.th).
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

import time
from openerp import models, fields, api, _
from openerp.exceptions import Warning


class container_receiving_report(models.TransientModel):
    _name = 'container.receiving.report'
    
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env['res.company']._company_default_get('fofo.sale.report'))
    start_date = fields.Date('Arrival Start Date', required=True, default= fields.Date.today())
    end_date = fields.Date('Arrival End Date', required=True, default= fields.Date.today())
    
    @api.multi
    def print_report(self, data):
        if self.env.context is None:
            self.env.context = {}
        data['form'] = self.read(['end_date', 'start_date','company_id'])[0]
        return self.pool['report'].get_action(self._cr, self._uid, [], 'fofo_sales_report.container_receiving_report', data=data, context=self.env.context)#probuse


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
